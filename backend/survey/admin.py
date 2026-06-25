from django.contrib import admin
from .models import GTSurvey


@admin.register(GTSurvey)
class GTSurveyAdmin(admin.ModelAdmin):
    list_display  = ['sno', 'user_id', 'crop_name', 'latitude', 'longitude',
                     'date_time', 'crop_stage', 'season', 'synced_at']
    list_filter   = ['crop_name', 'crop_stage', 'season', 'water_source']
    search_fields = ['user_id', 'crop_name', 'description_rem']
    readonly_fields = ['sno', 'synced_at']
    ordering = ['-date_time']
