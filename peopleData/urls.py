from django.urls import path
from . import views

urlpatterns = [
    path(
        "check-duplicate/",
        views.check_duplicate,
        name="check_duplicate"
    ),
]