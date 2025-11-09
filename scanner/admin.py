from django.contrib import admin
from .models import ScannerSettings, AudioTransmission, ScannerSession


@admin.register(ScannerSettings)
class ScannerSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'volume', 'fetch_interval', 'vfr_only', 'geo_filter', 'updated_at']
    list_filter = ['vfr_only', 'geo_filter']
    search_fields = ['user__username']


@admin.register(AudioTransmission)
class AudioTransmissionAdmin(admin.ModelAdmin):
    list_display = ['transmission_id', 'station_name', 'frequency', 'pilot', 'airport', 'flight_rules', 'timestamp']
    list_filter = ['flight_rules', 'airport']
    search_fields = ['station_name', 'pilot', 'airport', 'frequency']
    ordering = ['-transmission_id']


@admin.register(ScannerSession)
class ScannerSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'started_at', 'ended_at', 'is_active', 'transmissions_count']
    list_filter = ['is_active']
    search_fields = ['user__username']
    ordering = ['-started_at']
