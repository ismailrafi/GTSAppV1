"""
GPS Utilities
- Get GPS location (waits for ≥3 m accuracy, up to 30 seconds)
- Offset location by bearing angle and distance
- Uses Plyer for cross-platform GPS access
"""
import math
import time
import threading
import logging
from typing import Optional, Tuple, Callable

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
EARTH_RADIUS_M   = 6_371_000.0
TARGET_ACCURACY_M = 3.0
MAX_WAIT_SECONDS  = 30


class GPSLocation:
    """Holds the latest GPS fix."""
    def __init__(self):
        self.latitude:  Optional[float] = None
        self.longitude: Optional[float] = None
        self.accuracy:  Optional[float] = None
        self.timestamp: Optional[float] = None
        self._lock = threading.Lock()

    def update(self, lat, lon, acc):
        with self._lock:
            self.latitude  = lat
            self.longitude = lon
            self.accuracy  = acc
            self.timestamp = time.time()

    @property
    def is_valid(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def meets_accuracy(self) -> bool:
        return self.is_valid and (self.accuracy is not None) and (self.accuracy <= TARGET_ACCURACY_M)


_current_location = GPSLocation()


def _on_location(**kwargs):
    """Plyer GPS callback – called when a new fix arrives."""
    lat = kwargs.get('lat', kwargs.get('latitude'))
    lon = kwargs.get('lon', kwargs.get('longitude'))
    acc = kwargs.get('accuracy')
    if lat is not None and lon is not None:
        _current_location.update(lat, lon, acc)
        logger.debug(f"GPS fix: {lat:.6f}, {lon:.6f}, acc={acc}m")


def _on_status(stype, status):
    logger.debug(f"GPS status: {stype} — {status}")


def start_gps():
    """Start GPS listener (Plyer)."""
    try:
        from plyer import gps
        gps.configure(on_location=_on_location, on_status=_on_status)
        gps.start(minTime=1000, minDistance=1)   # update every 1s or 1m
        logger.info("GPS started")
    except Exception as e:
        logger.warning(f"Could not start GPS (plyer): {e}")


def stop_gps():
    try:
        from plyer import gps
        gps.stop()
    except Exception:
        pass


def get_location_blocking(
    timeout: float = MAX_WAIT_SECONDS,
    target_accuracy: float = TARGET_ACCURACY_M,
    on_progress: Optional[Callable[[str], None]] = None
) -> Optional[GPSLocation]:
    """
    Block until a GPS fix with accuracy ≤ target_accuracy is received,
    or until timeout seconds have elapsed.
    Returns the GPSLocation object, or None on failure.
    """
    start_gps()
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = int(deadline - time.time())
        if on_progress:
            if _current_location.is_valid:
                acc_str = f"{_current_location.accuracy:.1f}m" if _current_location.accuracy else "?"
                on_progress(f"Acquiring… accuracy={acc_str}  ({remaining}s remaining)")
            else:
                on_progress(f"Waiting for GPS… ({remaining}s remaining)")

        if _current_location.meets_accuracy:
            logger.info(
                f"GPS ready: {_current_location.latitude:.6f}, "
                f"{_current_location.longitude:.6f}, "
                f"acc={_current_location.accuracy}m"
            )
            return _current_location

        time.sleep(1)

    # Return best available fix even if accuracy threshold wasn't met
    if _current_location.is_valid:
        logger.warning("GPS timeout; returning best available fix")
        return _current_location
    return None


# ─── Bearing / Distance Offset ───────────────────────────────────────────────

def offset_location(
    lat: float, lon: float,
    distance_m: float, bearing_deg: float
) -> Tuple[float, float]:
    """
    Calculate a new lat/lon by moving `distance_m` metres in direction `bearing_deg`
    (0° = North, 90° = East) from the starting point.
    Uses the spherical Earth approximation (accurate to < 1 cm for distances < 10 km).
    """
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    brg_r = math.radians(bearing_deg)
    d_r   = distance_m / EARTH_RADIUS_M

    new_lat_r = math.asin(
        math.sin(lat_r) * math.cos(d_r) +
        math.cos(lat_r) * math.sin(d_r) * math.cos(brg_r)
    )
    new_lon_r = lon_r + math.atan2(
        math.sin(brg_r) * math.sin(d_r) * math.cos(lat_r),
        math.cos(d_r) - math.sin(lat_r) * math.sin(new_lat_r)
    )
    return math.degrees(new_lat_r), math.degrees(new_lon_r)


def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Return distance in metres between two lat/lon points."""
    R = EARTH_RADIUS_M
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))
