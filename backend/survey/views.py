"""
Survey API Views
Endpoints:
  POST   /api/survey/sync/          – Bulk upload (offline → server)
  GET    /api/survey/               – List all records
  GET    /api/survey/<pk>/          – Single record detail
  POST   /api/gee/indices/          – Compute spectral indices via GEE
  POST   /api/gee/unsupervised/     – Unsupervised classification via GEE
  POST   /api/gee/supervised/       – Supervised classification via GEE
"""
import os
import io
import base64
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response

from .models import GTSurvey
from .serializers import GTSurveySerializer, GTSurveyListSerializer
from .gee_service import (
    compute_indices,
    run_unsupervised_classification,
    run_supervised_classification,
)

logger = logging.getLogger(__name__)


# ─── Survey CRUD ─────────────────────────────────────────────────────────────

@api_view(['GET'])
def survey_list(request):
    """Return all survey records (summary fields only)."""
    records = GTSurvey.objects.all()
    serializer = GTSurveyListSerializer(records, many=True)
    return Response({'count': records.count(), 'results': serializer.data})


@api_view(['GET'])
def survey_detail(request, pk):
    """Return full detail for a single record."""
    try:
        record = GTSurvey.objects.get(pk=pk)
    except GTSurvey.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(GTSurveySerializer(record).data)


@api_view(['POST'])
@parser_classes([MultiPartParser, JSONParser])
def sync_surveys(request):
    """
    Bulk-upload collected survey records from mobile device.
    Accepts a list of records under the key 'records'.
    Each record matches GTSurvey fields.
    Images (base64-encoded) are decoded and saved automatically.
    """
    records_data = request.data.get('records', [])
    if not records_data:
        return Response({'error': 'No records provided'}, status=status.HTTP_400_BAD_REQUEST)

    created_ids = []
    errors = []

    for idx, rec in enumerate(records_data):
        try:
            # Decode base64 images if present
            for img_field in ['indices', 'unsupervised_classification',
                               'supervised_classification', 'photo1', 'photo2', 'photo3']:
                b64 = rec.pop(f'{img_field}_b64', None)
                if b64:
                    img_data = base64.b64decode(b64)
                    rec[img_field] = ContentFile(img_data, name=f'{img_field}_{idx}.jpg')

            serializer = GTSurveySerializer(data=rec)
            if serializer.is_valid():
                obj = serializer.save()
                created_ids.append(obj.sno)
            else:
                errors.append({'index': idx, 'errors': serializer.errors})

        except Exception as e:
            errors.append({'index': idx, 'error': str(e)})

    return Response({
        'synced': len(created_ids),
        'created_ids': created_ids,
        'errors': errors,
    }, status=status.HTTP_201_CREATED if created_ids else status.HTTP_400_BAD_REQUEST)


# ─── Google Earth Engine Endpoints ───────────────────────────────────────────

@api_view(['POST'])
def gee_indices(request):
    """
    Compute NDVI, NDWI, EVI, SAVI for a given location using Sentinel-2 data.
    Body: { "latitude": float, "longitude": float, "buffer_m": int }
    Returns: { "image_b64": "...", "thumbnail_url": "..." }
    """
    lat = request.data.get('latitude')
    lon = request.data.get('longitude')
    buffer_m = request.data.get('buffer_m', 500)

    if lat is None or lon is None:
        return Response({'error': 'latitude and longitude are required'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        result = compute_indices(float(lat), float(lon), int(buffer_m))
        return Response(result)
    except Exception as e:
        logger.exception("GEE indices error")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def gee_unsupervised(request):
    """
    Run unsupervised (k-means) classification with min 10 classes.
    Body: { "latitude": float, "longitude": float, "buffer_m": int, "n_classes": int }
    """
    lat = request.data.get('latitude')
    lon = request.data.get('longitude')
    buffer_m = request.data.get('buffer_m', 500)
    n_classes = max(10, request.data.get('n_classes', 10))

    if lat is None or lon is None:
        return Response({'error': 'latitude and longitude are required'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        result = run_unsupervised_classification(float(lat), float(lon), int(buffer_m), n_classes)
        return Response(result)
    except Exception as e:
        logger.exception("GEE unsupervised error")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def gee_supervised(request):
    """
    Run supervised RandomForest classification.
    Body: { "latitude": float, "longitude": float, "buffer_m": int,
            "crop_name": str, "training_points": [...] }
    """
    lat = request.data.get('latitude')
    lon = request.data.get('longitude')
    buffer_m = request.data.get('buffer_m', 500)
    crop_name = request.data.get('crop_name', 'Unknown')
    training_points = request.data.get('training_points', [])

    if lat is None or lon is None:
        return Response({'error': 'latitude and longitude are required'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        result = run_supervised_classification(
            float(lat), float(lon), int(buffer_m), crop_name, training_points
        )
        return Response(result)
    except Exception as e:
        logger.exception("GEE supervised error")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
