# CropSurvey GT — Ground Truth Survey Mobile App

A field data collection app for crop identification and land-use mapping,
combining GPS, Sentinel satellite imagery (via Google Earth Engine), and
machine learning classification.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  MOBILE APP  (Kivy + KivyMD — Python)                           │
│                                                                   │
│  Main ──► Collect Data ──► (GPS / GEE / Camera / Dropdowns)      │
│        ──► View Data    ──► (Table + Google Maps link)            │
│        ──► Sync Data    ──► (Upload pending records)              │
│                                                                   │
│  Local SQLite (offline-first, ~/. cropsurvey/local_survey.db)    │
└──────────────────────┬──────────────────────────────────────────┘
                       │  REST API (JSON + multipart)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  DJANGO BACKEND  (Python 3.11)                                   │
│                                                                   │
│  /api/survey/sync/        ← Bulk upload                          │
│  /api/survey/             ← List                                 │
│  /api/gee/indices/        ← Spectral indices                     │
│  /api/gee/unsupervised/   ← KMeans classification                │
│  /api/gee/supervised/     ← RandomForest classification          │
└──────────────────────┬──────────────────────────────────────────┘
          ┌────────────┴────────────┐
          ▼                         ▼
   PostgreSQL DB            Google Earth Engine
   (LandUseInfo.GTSurvey)  (Sentinel-1 & 2, ESA WorldCover)
```

---

## Features

### Collect Data Screen
| # | Feature | Detail |
|---|---------|--------|
| 1 | GPS Location | Accuracy ≤ 3 m, waits up to 30 s |
| 2 | Bearing Offset | Move coordinate by angle + distance |
| 3 | Manual Map | Opens Google Maps for manual pinning |
| 4 | Crop Name | Editable dropdown — 70+ crops in 4 categories |
| 5 | Date & Time | Auto-updated live |
| 6 | Spectral Indices | NDVI, NDWI, EVI, SAVI via Sentinel-2 |
| 7 | Unsupervised | KMeans, ≥10 classes, Sentinel-1 + 2 |
| 8 | Supervised | RandomForest, crop labels, Sentinel-1 + 2 |
| 9 | Photos (×3) | Geotagged landscape JPEGs with burned labels |
| 10 | Water Source | Surface / Ground Water |
| 11 | Crop Stage | 6 stages from Land Prep to Harvested |
| 12 | Season | Kharif / Rabi / Winter / Summer |
| 13 | Remarks | Free-text description |

### Satellite Imagery (GEE)
- **Sentinel-2 SR** — cloud cover < 30 %, last 90 days, 10 m resolution
- **Sentinel-1 GRD** — VV + VH median composite (fills cloud gaps)
- **Masking** — ESA WorldCover removes built-up (class 50), water (80), forest (10)
- **Indices** — NDVI, NDWI, EVI, SAVI with colour-coded thumbnails
- **Unsupervised** — Weka KMeans, minimum 10 classes
- **Supervised** — RandomForest (50 trees) using GPS point as training sample

---

## Quick Start

### 1. PostgreSQL — Create database

```sql
CREATE DATABASE "LandUseInfo";
```

### 2. Backend — Django

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # fill in DB credentials & GEE details
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

**GEE Authentication** (first time):
```bash
# Option A — interactive (development)
earthengine authenticate

# Option B — service account (production)
# Set GEE_SERVICE_ACCOUNT and GEE_KEY_FILE in .env
```

### 3. Mobile App — Desktop dev

```bash
cd mobile
pip install -r requirements.txt
python main.py
```

### 4. Mobile App — Android (APK)

```bash
cd mobile
pip install buildozer
buildozer android debug deploy run
```

---

## Database Schema

Table: `GTSurvey` in database `LandUseInfo`

| Field | Type | Description |
|-------|------|-------------|
| sno | AutoField (PK) | Serial number |
| user_id | CharField | Surveyor identifier |
| latitude | FloatField | Decimal degrees |
| longitude | FloatField | Decimal degrees |
| bearing_distance | FloatField | Offset distance (m) |
| bearing_angle | FloatField | Offset bearing (°) |
| date_time | DateTimeField | Survey timestamp |
| crop_name | TextField | Selected/typed crop |
| crop_stage | TextField | Growth stage |
| water_source | TextField | Surface / Ground |
| season | TextField | Kharif / Rabi / etc. |
| indices | ImageField | NDVI/NDWI/EVI/SAVI image |
| unsupervised_classification | ImageField | KMeans result |
| supervised_classification | ImageField | RF result |
| photo1–3 | ImageField | Geotagged field photos |
| description_rem | TextField | Remarks |
| synced_at | DateTimeField | Server upload timestamp |

---

## API Reference

### POST `/api/survey/sync/`
Upload collected records from mobile.
```json
{
  "records": [
    {
      "user_id": "surveyor_001",
      "latitude": 17.3850,
      "longitude": 78.4867,
      "date_time": "2025-06-01T10:30:00",
      "crop_name": "Rice",
      "crop_stage": "Vegetative",
      "season": "Kharif",
      "indices_b64": "<base64 PNG>",
      ...
    }
  ]
}
```

### POST `/api/gee/indices/`
```json
{ "latitude": 17.385, "longitude": 78.486, "buffer_m": 500 }
```
Response:
```json
{ "ndvi_b64": "...", "ndwi_b64": "...", "evi_b64": "...", "savi_b64": "..." }
```

### POST `/api/gee/unsupervised/`
```json
{ "latitude": 17.385, "longitude": 78.486, "buffer_m": 500, "n_classes": 10 }
```

### POST `/api/gee/supervised/`
```json
{
  "latitude": 17.385, "longitude": 78.486,
  "crop_name": "Rice", "buffer_m": 500,
  "training_points": [
    { "latitude": 17.39, "longitude": 78.49, "crop_name": "Wheat" }
  ]
}
```

---

## Notes

- **Offline-first**: All data is saved to local SQLite before any network call.
  The app works completely offline; sync when connectivity is available.
- **GEE quota**: The free GEE tier supports ~1000 computation requests/day.
  For production, use a Google Cloud Project with billing enabled.
- **Android permissions**: `ACCESS_FINE_LOCATION`, `CAMERA`,
  `WRITE_EXTERNAL_STORAGE` are declared in `buildozer.spec`.
- **Server URL**: Edit in the Sync screen at runtime, or set
  `BACKEND_URL` environment variable before launching the app.
