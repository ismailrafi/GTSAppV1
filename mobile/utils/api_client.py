"""
API Client — communicates with the Django backend.
All calls are synchronous; run them in background threads to keep the UI responsive.
"""
import os
import base64
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

BASE_URL = os.getenv('BACKEND_URL', 'http://192.168.1.100:8000/api')


def _url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _safe_post(path: str, json_data: dict = None, files: dict = None,
               timeout: int = 60) -> Dict[str, Any]:
    try:
        resp = requests.post(_url(path), json=json_data, files=files, timeout=timeout)
        resp.raise_for_status()
        return {'ok': True, 'data': resp.json()}
    except requests.Timeout:
        return {'ok': False, 'error': 'Request timed out'}
    except requests.ConnectionError:
        return {'ok': False, 'error': 'Cannot reach server. Check network.'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def _safe_get(path: str, timeout: int = 30) -> Dict[str, Any]:
    try:
        resp = requests.get(_url(path), timeout=timeout)
        resp.raise_for_status()
        return {'ok': True, 'data': resp.json()}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ─── Survey sync ─────────────────────────────────────────────────────────────

def sync_records(records: List[Dict]) -> Dict[str, Any]:
    """Bulk-upload locally collected records to the server."""
    return _safe_post('survey/sync/', json_data={'records': records}, timeout=120)


def fetch_all_surveys() -> Dict[str, Any]:
    return _safe_get('survey/')


# ─── GEE Analysis ────────────────────────────────────────────────────────────

def compute_indices(lat: float, lon: float, buffer_m: int = 500) -> Dict[str, Any]:
    return _safe_post('gee/indices/', json_data={
        'latitude': lat, 'longitude': lon, 'buffer_m': buffer_m
    }, timeout=180)


def run_unsupervised(lat: float, lon: float, buffer_m: int = 500,
                     n_classes: int = 10) -> Dict[str, Any]:
    return _safe_post('gee/unsupervised/', json_data={
        'latitude': lat, 'longitude': lon,
        'buffer_m': buffer_m, 'n_classes': n_classes
    }, timeout=180)


def run_supervised(lat: float, lon: float, crop_name: str,
                   training_points: List[Dict] = None,
                   buffer_m: int = 500) -> Dict[str, Any]:
    return _safe_post('gee/supervised/', json_data={
        'latitude': lat, 'longitude': lon,
        'crop_name': crop_name, 'buffer_m': buffer_m,
        'training_points': training_points or [],
    }, timeout=180)
