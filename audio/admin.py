from django.contrib import admin
from .models import AudioSubmission


@admin.register(AudioSubmission)
class AudioSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "person", "original_filename", "duration_seconds", "bitrate_kbps", "loudness_dbfs", "noise_floor_dbfs", "created_at")
    search_fields = ("person__name", "person__phone", "original_filename")
