from django.db import models
from django.contrib.auth.models import User

class ScannerSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='scanner_settings')
    volume = models.FloatField(default=0.7)
    fetch_interval = models.IntegerField(default=20)
    vfr_only = models.BooleanField(default=False)
    geo_filter = models.BooleanField(default=False)
    prefetch_audio = models.BooleanField(default=True)
    use_websocket = models.BooleanField(default=True)
    airports = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scanner_settings'
        verbose_name_plural = 'Scanner Settings'

    def __str__(self):
        return f"Settings for {self.user.username}"


class AudioTransmission(models.Model):
    transmission_id = models.IntegerField(unique=True)
    url = models.URLField(max_length=500)
    who_from = models.CharField(max_length=100)
    frequency = models.CharField(max_length=50)
    station_name = models.CharField(max_length=100)
    pilot = models.CharField(max_length=100)
    airport = models.CharField(max_length=10)
    position = models.CharField(max_length=100)
    voice_name = models.CharField(max_length=100)
    from_userid = models.CharField(max_length=100)
    flight_rules = models.CharField(max_length=10)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audio_transmissions'
        ordering = ['-transmission_id']
        indexes = [
            models.Index(fields=['-transmission_id']),
            models.Index(fields=['airport']),
            models.Index(fields=['flight_rules']),
        ]

    def __str__(self):
        return f"#{self.transmission_id} - {self.station_name} ({self.frequency})"


class ScannerSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scanner_sessions', null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    transmissions_count = models.IntegerField(default=0)
    settings_snapshot = models.JSONField(default=dict)

    class Meta:
        db_table = 'scanner_sessions'
        ordering = ['-started_at']

    def __str__(self):
        status = "Active" if self.is_active else "Ended"
        return f"Session {self.id} - {status} - {self.started_at}"
