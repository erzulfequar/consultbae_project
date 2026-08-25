from django.db import models
from peopleData.models import Person


class AudioSubmission(models.Model):
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="audio_submissions")
    audio_file = models.FileField(upload_to="audio_submissions/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.PositiveIntegerField()
    duration_seconds = models.FloatField(null=True, blank=True)
    bitrate_kbps = models.FloatField(null=True, blank=True)
    sample_rate_hz = models.PositiveIntegerField(null=True, blank=True)
    channels = models.PositiveSmallIntegerField(null=True, blank=True)
    loudness_dbfs = models.FloatField(null=True, blank=True)
    noise_floor_dbfs = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Audio from {self.person.name} ({self.created_at:%Y-%m-%d})"

    @property
    def quality_label(self):
        if self.noise_floor_dbfs is None:
            return "Analysis pending"
        if self.noise_floor_dbfs > -25:
            return "High noise"
        if self.noise_floor_dbfs > -40:
            return "Moderate noise"
        return "Clear"
