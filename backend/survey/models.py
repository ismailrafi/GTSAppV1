"""
Survey Models
Table: GTSurvey in database: LandUseInfo
"""
from django.db import models


class GTSurvey(models.Model):
    """
    Ground Truth Survey record.
    Stores field data collected by surveyors.
    """
    # ── Primary Key ──────────────────────────────────────────────────────────
    sno = models.AutoField(primary_key=True, verbose_name="Serial No")

    # ── User & Location ──────────────────────────────────────────────────────
    user_id = models.CharField(max_length=150, verbose_name="User ID")
    latitude = models.FloatField(verbose_name="Latitude")
    longitude = models.FloatField(verbose_name="Longitude")
    bearing_distance = models.FloatField(
        null=True, blank=True,
        verbose_name="Bearing Distance (m)"
    )
    bearing_angle = models.FloatField(
        null=True, blank=True,
        verbose_name="Bearing Angle (°)"
    )

    # ── Date & Time ──────────────────────────────────────────────────────────
    date_time = models.DateTimeField(verbose_name="Date & Time")

    # ── Crop Info ────────────────────────────────────────────────────────────
    crop_name = models.TextField(verbose_name="Crop Name")
    crop_stage = models.TextField(null=True, blank=True, verbose_name="Crop Stage")
    water_source = models.TextField(null=True, blank=True, verbose_name="Water Source")
    season = models.TextField(null=True, blank=True, verbose_name="Season")

    # ── Classified Images ────────────────────────────────────────────────────
    indices = models.ImageField(
        upload_to='indices/', null=True, blank=True,
        verbose_name="Spectral Indices (NDVI/NDWI/EVI/SAVI)"
    )
    unsupervised_classification = models.ImageField(
        upload_to='unsupervised/', null=True, blank=True,
        verbose_name="Unsupervised Classification"
    )
    supervised_classification = models.ImageField(
        upload_to='supervised/', null=True, blank=True,
        verbose_name="Supervised Classification"
    )

    # ── Geotagged Photos ─────────────────────────────────────────────────────
    photo1 = models.ImageField(
        upload_to='photos/', null=True, blank=True, verbose_name="Photo 1"
    )
    photo2 = models.ImageField(
        upload_to='photos/', null=True, blank=True, verbose_name="Photo 2"
    )
    photo3 = models.ImageField(
        upload_to='photos/', null=True, blank=True, verbose_name="Photo 3"
    )

    # ── Remarks ──────────────────────────────────────────────────────────────
    description_rem = models.TextField(
        null=True, blank=True, verbose_name="Description / Remarks"
    )

    # ── Sync Metadata ────────────────────────────────────────────────────────
    synced_at = models.DateTimeField(auto_now_add=True, verbose_name="Synced At")

    class Meta:
        db_table = 'GTSurvey'
        verbose_name = "GT Survey"
        verbose_name_plural = "GT Surveys"
        ordering = ['-date_time']

    def __str__(self):
        return f"[{self.sno}] {self.crop_name} @ ({self.latitude:.5f}, {self.longitude:.5f}) — {self.date_time}"
