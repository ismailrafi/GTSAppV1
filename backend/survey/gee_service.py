"""
Google Earth Engine Service
Handles:
  - Sentinel-1 & Sentinel-2 imagery (cloud < 30%, last 3 months)
  - Spectral Indices: NDVI, NDWI, EVI, SAVI
  - Masking: built-up, forest, water bodies
  - Unsupervised classification (KMeans, min 10 classes)
  - Supervised classification (RandomForest)
  - Returns base64-encoded thumbnail images
"""
import os
import io
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False
    logger.warning("earthengine-api not installed. GEE features disabled.")


def _init_gee():
    """Initialize GEE with service account or interactive auth."""
    if not GEE_AVAILABLE:
        raise RuntimeError("earthengine-api package not installed.")
    try:
        key_file = os.getenv('GEE_KEY_FILE', 'gee_key.json')
        service_account = os.getenv('GEE_SERVICE_ACCOUNT', '')
        if service_account and os.path.exists(key_file):
            credentials = ee.ServiceAccountCredentials(service_account, key_file)
            ee.Initialize(credentials)
        else:
            ee.Initialize()  # Uses ~/.config/earthengine/credentials (ee.Authenticate())
    except Exception as e:
        raise RuntimeError(f"GEE initialization failed: {e}")


def _get_aoi(lat: float, lon: float, buffer_m: int) -> "ee.Geometry":
    """Return a square buffer AOI around the given point."""
    point = ee.Geometry.Point([lon, lat])
    return point.buffer(buffer_m).bounds()


def _get_sentinel2(aoi: "ee.Geometry", start_date: str, end_date: str) -> "ee.ImageCollection":
    """Get cloud-filtered Sentinel-2 SR image collection."""
    return (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12'])
    )


def _get_sentinel1(aoi: "ee.Geometry", start_date: str, end_date: str) -> "ee.Image":
    """Get Sentinel-1 SAR median composite."""
    return (
        ee.ImageCollection('COPERNICUS/S1_GRD')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.eq('instrumentMode', 'IW'))
        .select(['VV', 'VH'])
        .median()
    )


def _mask_non_cropland(image: "ee.Image") -> "ee.Image":
    """
    Mask out built-up areas, water bodies, and dense forest using
    ESA WorldCover (10m global land cover, 2021).
    Classes to KEEP: Cropland (40), Shrubland (20), Grassland (30), Bare/sparse (60)
    """
    worldcover = ee.ImageCollection('ESA/WorldCover/v200').first()
    # 10 = Tree cover (forest), 80 = Permanent water, 50 = Built-up
    forest  = worldcover.eq(10)
    water   = worldcover.eq(80)
    buildup = worldcover.eq(50)
    mask    = forest.Or(water).Or(buildup).Not()
    return image.updateMask(mask)


def _compute_indices_image(s2: "ee.Image") -> "ee.Image":
    """Compute NDVI, NDWI, EVI, SAVI from a Sentinel-2 image."""
    # Scale reflectance
    s2 = s2.divide(10000)
    nir  = s2.select('B8')
    red  = s2.select('B4')
    green= s2.select('B3')
    swir = s2.select('B11')

    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
    evi  = (nir.subtract(red)
               .divide(nir.add(red.multiply(6)).subtract(swir.multiply(7.5)).add(1))
               .multiply(2.5)).rename('EVI')
    savi = (nir.subtract(red)
               .divide(nir.add(red).add(0.5))
               .multiply(1.5)).rename('SAVI')
    return ee.Image([ndvi, ndwi, evi, savi])


def _image_to_b64(image: "ee.Image", aoi: "ee.Geometry", vis_params: dict) -> str:
    """Get a thumbnail PNG from GEE and return as base64 string."""
    thumb_url = image.getThumbURL({
        **vis_params,
        'region': aoi,
        'dimensions': 512,
        'format': 'PNG',
    })
    import urllib.request
    with urllib.request.urlopen(thumb_url) as resp:
        img_bytes = resp.read()
    return base64.b64encode(img_bytes).decode('utf-8')


# ─── Public API ──────────────────────────────────────────────────────────────

def compute_indices(lat: float, lon: float, buffer_m: int = 500) -> Dict[str, Any]:
    """
    Compute NDVI, NDWI, EVI, SAVI for the given location.
    Fuses Sentinel-2 (cloud < 30%) and Sentinel-1 for cloudy periods.
    Returns base64-encoded false-colour composite and per-index thumbnails.
    """
    _init_gee()
    aoi = _get_aoi(lat, lon, buffer_m)
    end   = datetime.utcnow()
    start = end - timedelta(days=90)
    s_date = start.strftime('%Y-%m-%d')
    e_date = end.strftime('%Y-%m-%d')

    s2_col = _get_sentinel2(aoi, s_date, e_date)
    s2_count = s2_col.size().getInfo()

    if s2_count > 0:
        s2 = s2_col.median()
    else:
        # Fall back to least-cloudy image if nothing qualifies
        s2_col_fallback = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(aoi).filterDate(s_date, e_date)
            .sort('CLOUDY_PIXEL_PERCENTAGE')
            .select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12'])
        )
        s2 = s2_col_fallback.first()

    s2_masked = _mask_non_cropland(s2)
    indices_img = _compute_indices_image(s2_masked)
    indices_masked = _mask_non_cropland(indices_img)

    # Sentinel-1 composite for SAR context
    s1 = _get_sentinel1(aoi, s_date, e_date)

    # Thumbnails
    ndvi_b64 = _image_to_b64(
        indices_masked.select('NDVI'),
        aoi,
        {'min': -1, 'max': 1, 'palette': ['red', 'yellow', 'green']}
    )
    ndwi_b64 = _image_to_b64(
        indices_masked.select('NDWI'),
        aoi,
        {'min': -1, 'max': 1, 'palette': ['brown', 'white', 'blue']}
    )
    evi_b64 = _image_to_b64(
        indices_masked.select('EVI'),
        aoi,
        {'min': -1, 'max': 1, 'palette': ['red', 'yellow', 'darkgreen']}
    )
    savi_b64 = _image_to_b64(
        indices_masked.select('SAVI'),
        aoi,
        {'min': -1, 'max': 1, 'palette': ['brown', 'yellow', 'green']}
    )

    return {
        'ndvi_b64': ndvi_b64,
        'ndwi_b64': ndwi_b64,
        'evi_b64': evi_b64,
        'savi_b64': savi_b64,
        's2_scenes_used': s2_count,
        'date_range': f"{s_date} to {e_date}",
    }


def run_unsupervised_classification(
    lat: float, lon: float,
    buffer_m: int = 500,
    n_classes: int = 10
) -> Dict[str, Any]:
    """
    KMeans unsupervised classification using Sentinel-1 + Sentinel-2 features.
    Masks built-up, forest, water bodies.
    Minimum n_classes = 10.
    """
    _init_gee()
    aoi = _get_aoi(lat, lon, buffer_m)
    end   = datetime.utcnow()
    start = end - timedelta(days=90)
    s_date = start.strftime('%Y-%m-%d')
    e_date = end.strftime('%Y-%m-%d')

    s2_col = _get_sentinel2(aoi, s_date, e_date)
    s2 = s2_col.median() if s2_col.size().getInfo() > 0 else (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi).filterDate(s_date, e_date)
        .sort('CLOUDY_PIXEL_PERCENTAGE').select(['B2','B3','B4','B8','B11','B12']).first()
    )
    s1 = _get_sentinel1(aoi, s_date, e_date)
    indices = _compute_indices_image(s2.divide(10000))

    # Stack features: S2 bands + S1 + indices
    composite = s2.addBands(s1).addBands(indices)
    composite_masked = _mask_non_cropland(composite)

    # Sample for clustering
    training = composite_masked.sample(
        region=aoi, scale=10, numPixels=5000, seed=42
    )
    clusterer = ee.Clusterer.wekaKMeans(n_classes).train(training)
    classified = composite_masked.cluster(clusterer)
    classified_masked = _mask_non_cropland(classified)

    palette = [
        'FF0000','00FF00','0000FF','FFFF00','FF00FF',
        '00FFFF','FFA500','800080','008000','FFC0CB',
        'A52A2A','808080','ADD8E6','90EE90','FFD700',
        'DDA0DD','B0E0E6','F08080','E0FFFF','FAEBD7',
    ][:n_classes]

    result_b64 = _image_to_b64(
        classified_masked,
        aoi,
        {'min': 0, 'max': n_classes - 1, 'palette': palette}
    )
    return {
        'classification_b64': result_b64,
        'n_classes': n_classes,
        'method': 'KMeans (Weka)',
        'features': 'Sentinel-1 (VV,VH) + Sentinel-2 (B2-B12) + NDVI + NDWI + EVI + SAVI',
        'date_range': f"{s_date} to {e_date}",
    }


def run_supervised_classification(
    lat: float, lon: float,
    buffer_m: int = 500,
    crop_name: str = 'CropClass',
    training_points: List[Dict] = None
) -> Dict[str, Any]:
    """
    Supervised RandomForest classification.
    Uses provided training points (lat/lon pairs with class labels),
    plus the current survey point labeled with crop_name.
    """
    _init_gee()
    aoi = _get_aoi(lat, lon, buffer_m)
    end   = datetime.utcnow()
    start = end - timedelta(days=90)
    s_date = start.strftime('%Y-%m-%d')
    e_date = end.strftime('%Y-%m-%d')

    s2_col = _get_sentinel2(aoi, s_date, e_date)
    s2 = s2_col.median() if s2_col.size().getInfo() > 0 else (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi).filterDate(s_date, e_date)
        .sort('CLOUDY_PIXEL_PERCENTAGE').select(['B2','B3','B4','B8','B11','B12']).first()
    )
    s1 = _get_sentinel1(aoi, s_date, e_date)
    indices = _compute_indices_image(s2.divide(10000))
    composite = _mask_non_cropland(s2.addBands(s1).addBands(indices))

    # Build training FeatureCollection
    # Class 0 reserved for current crop_name
    all_training_pts = [{'lat': lat, 'lon': lon, 'label': 0, 'name': crop_name}]
    class_map = {crop_name: 0}
    next_class = 1

    if training_points:
        for pt in training_points:
            cname = pt.get('crop_name', 'Unknown')
            if cname not in class_map:
                class_map[cname] = next_class
                next_class += 1
            all_training_pts.append({
                'lat': pt['latitude'], 'lon': pt['longitude'],
                'label': class_map[cname], 'name': cname,
            })

    features = [
        ee.Feature(
            ee.Geometry.Point([p['lon'], p['lat']]),
            {'label': p['label'], 'class_name': p['name']}
        )
        for p in all_training_pts
    ]
    fc = ee.FeatureCollection(features)

    bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'VV', 'VH',
             'NDVI', 'NDWI', 'EVI', 'SAVI']
    training_data = composite.select(bands).sampleRegions(
        collection=fc, properties=['label'], scale=10
    )

    n_classes = max(2, len(class_map))
    classifier = ee.Classifier.smileRandomForest(50).train(
        features=training_data, classProperty='label', inputProperties=bands
    )
    classified = composite.select(bands).classify(classifier)
    classified_masked = _mask_non_cropland(classified)

    palette = [
        '00FF00','FF0000','0000FF','FFFF00','FF00FF',
        '00FFFF','FFA500','800080','008000','FFC0CB',
    ][:n_classes]

    result_b64 = _image_to_b64(
        classified_masked, aoi,
        {'min': 0, 'max': n_classes - 1, 'palette': palette}
    )
    return {
        'classification_b64': result_b64,
        'method': 'RandomForest (50 trees)',
        'n_classes': n_classes,
        'class_map': class_map,
        'primary_crop': crop_name,
        'date_range': f"{s_date} to {e_date}",
    }
