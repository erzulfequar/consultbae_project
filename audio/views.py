"""Views for audio collection and CSV-to-n8n forwarding."""

import csv
import io
import logging
import re

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
import requests

from peopleData.models import Person
from peopleData.utils import clean_city, clean_email, clean_name, clean_phone, clean_text

from .analysis import extract_audio_analysis
from .models import AudioSubmission


logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 20 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-wav",
}


def normalize_csv_for_n8n(csv_file):
    """Return a UTF-8 CSV with consistent duplicate-check identifiers for n8n.

    The three source exports use different names for the same identifiers. n8n
    can therefore always use ``name``, ``email``, ``phone`` and ``city``.
    """
    try:
        text = csv_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("CSV must be UTF-8 encoded.")

    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
    except csv.Error as exc:
        raise ValueError(f"Invalid CSV: {exc}") from exc
    if not reader.fieldnames or not any(clean_text(header) for header in reader.fieldnames):
        raise ValueError("CSV is missing a header row.")

    def normalized_header(value):
        return re.sub(r"[^a-z0-9]+", "_", clean_text(value).lower()).strip("_")

    header_aliases = {
        "full_name": "name", "worker_name": "name", "name": "name",
        "email": "email", "email_id": "email",
        "phone": "phone", "phone_number": "phone",
        "city": "city", "location": "city",
    }
    fieldnames = [header_aliases.get(normalized_header(header), normalized_header(header)) for header in reader.fieldnames]
    if not all(fieldnames) or len(set(fieldnames)) != len(fieldnames):
        raise ValueError("CSV headers must be non-empty and cannot normalize to duplicates.")

    field_cleaners = {
        "name": clean_name, "email": clean_email,
        "phone": clean_phone, "city": clean_city,
    }
    rows = []
    try:
        for source_row, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Row {source_row} has more values than its header row.")
            normalized = {
                fieldname: clean_text(row.get(source_header, ""))
                for source_header, fieldname in zip(reader.fieldnames, fieldnames)
            }
            if not any(normalized.values()):
                continue
            for field, cleaner in field_cleaners.items():
                if field in normalized:
                    normalized[field] = cleaner(normalized[field])
            rows.append(normalized)
    except csv.Error as exc:
        raise ValueError(f"Invalid CSV: {exc}") from exc

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def optional_float(value, minimum=None, maximum=None):
    """Return a number only when it falls inside the accepted range."""
    try:
        number = float(value)
        if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
            return None
        return number
    except (TypeError, ValueError):
        return None


def optional_int(value, minimum=1, maximum=384000):
    """Return a bounded integer value, or ``None`` for invalid input."""
    number = optional_float(value, minimum, maximum)
    return int(number) if number is not None else None


@require_http_methods(["GET", "POST"])
def collect_audio(request):
    """Render the form or store one validated audio submission."""
    if request.method == "GET":
        return render(request, "audio/collect.html")

    name = clean_name(request.POST.get("name"))
    phone = clean_phone(request.POST.get("phone"))
    audio = request.FILES.get("audio")
    if not name or len(phone) != 10 or not audio:
        return HttpResponseBadRequest("Please provide a name, a valid 10-digit phone number, and an audio file.")
    if audio.size > MAX_AUDIO_BYTES:
        return HttpResponseBadRequest("Audio must be 20 MB or smaller.")
    if audio.content_type and audio.content_type not in ALLOWED_AUDIO_TYPES:
        return HttpResponseBadRequest("Please upload a supported audio file.")

    with transaction.atomic():
        # Phone is the Task 1 strong identifier. Avoid creating a second person
        # when a worker already exists in the consolidated database.
        person = Person.objects.filter(phone=phone).order_by("id").first()
        if person is None:
            person = Person.objects.create(name=name, phone=phone, source_summary="audio_submission")
        submission = AudioSubmission.objects.create(
            person=person, audio_file=audio, original_filename=audio.name[:255],
            content_type=audio.content_type or "unknown", file_size_bytes=audio.size,
            duration_seconds=optional_float(request.POST.get("duration_seconds"), 0.01, 7200),
            bitrate_kbps=optional_float(request.POST.get("bitrate_kbps"), 1, 10000),
            sample_rate_hz=optional_int(request.POST.get("sample_rate_hz"), 8000, 384000),
            channels=optional_int(request.POST.get("channels"), 1, 16),
            loudness_dbfs=optional_float(request.POST.get("loudness_dbfs"), -120, 0),
            noise_floor_dbfs=optional_float(request.POST.get("noise_floor_dbfs"), -120, 0),
        )
        # Do not rely on browser metadata: analyse the file after storage so
        # every accepted upload has server-derived values.
        try:
            analysis = extract_audio_analysis(submission.audio_file.path)
        except Exception:
            # Metadata extraction depends on native audio decoders. A decoder
            # failure must not discard an otherwise valid user upload.
            logger.exception("Audio analysis failed for submission %s", submission.pk)
            analysis = {}
        if analysis:
            for field, value in analysis.items():
                setattr(submission, field, value)
            submission.save(update_fields=tuple(analysis))
    return redirect("audio:success", submission_id=submission.pk)


@require_http_methods(["GET"])
def success(request, submission_id):
    """Show the confirmation page for a saved submission."""
    submission = get_object_or_404(AudioSubmission.objects.select_related("person"), pk=submission_id)
    return render(request, "audio/success.html", {"submission": submission})


@require_http_methods(["GET"])
def submissions(request):
    """List submissions together with their server-derived metadata."""
    return render(request, "audio/submissions.html", {
        "submissions": AudioSubmission.objects.select_related("person").all(),
    })


@require_http_methods(["GET"])
def csv_to_n8n(request):
    """Render the CSV upload screen configured with the active webhook URL."""
    return render(request, "audio/csv_to_n8n.html", {"webhook_url": settings.N8N_CSV_WEBHOOK_URL})


@require_http_methods(["POST"])
def forward_csv_to_n8n(request):
    """Normalize an uploaded CSV and proxy it to the configured n8n webhook."""
    csv_file = request.FILES.get("data")
    if not csv_file or not csv_file.name.lower().endswith(".csv"):
        return HttpResponseBadRequest("Please choose a CSV file.")
    try:
        normalized_csv = normalize_csv_for_n8n(csv_file)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    try:
        response = requests.post(
            settings.N8N_CSV_WEBHOOK_URL,
            files={"data": (csv_file.name, io.BytesIO(normalized_csv), "text/csv")},
            timeout=60,
        )
    except requests.RequestException as exc:
        return JsonResponse({"error": f"Could not reach n8n: {exc}"}, status=502)
    return HttpResponse(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type", "application/json"),
    )
