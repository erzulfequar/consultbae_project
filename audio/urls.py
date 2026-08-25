from django.urls import path

from . import views

app_name = "audio"

urlpatterns = [
    path("", views.collect_audio, name="collect"),
    path("submitted/<int:submission_id>/", views.success, name="success"),
    path("submissions/", views.submissions, name="submissions"),
    path("csv-check/", views.csv_to_n8n, name="csv_to_n8n"),
    path("csv-check/send/", views.forward_csv_to_n8n, name="forward_csv_to_n8n"),
]
