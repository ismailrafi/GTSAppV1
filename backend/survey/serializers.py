from rest_framework import serializers
from .models import GTSurvey


class GTSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = GTSurvey
        fields = '__all__'
        read_only_fields = ['sno', 'synced_at']


class GTSurveyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing records (no heavy image data)."""
    class Meta:
        model = GTSurvey
        fields = [
            'sno', 'user_id', 'latitude', 'longitude',
            'date_time', 'crop_name', 'crop_stage',
            'water_source', 'season', 'synced_at',
        ]
