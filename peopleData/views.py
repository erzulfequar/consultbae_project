import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Person
from .utils import clean_email, clean_name, clean_phone


@csrf_exempt
def check_duplicate(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST method allowed"},
            status=405
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400
        )

    # n8n may send raw CSV values (+91 prefix, leading zero, varied casing).
    # Normalize again at the API boundary so duplicate matching is consistent.
    name = clean_name(data.get("name"))
    email = clean_email(data.get("email"))
    phone = clean_phone(data.get("phone"))

    duplicate_person = None
    match_type = None

    # 1. Email check
    if email:
        duplicate_person = Person.objects.filter(
            email__iexact=email
        ).first()

        if duplicate_person:
            match_type = "email"

    # 2. Phone check
    if not duplicate_person and phone:
        duplicate_person = Person.objects.filter(
            phone=phone
        ).first()

        if duplicate_person:
            match_type = "phone"

    # 3. Name check
    if not duplicate_person and name:
        duplicate_person = Person.objects.filter(
            name__iexact=name
        ).first()

        if duplicate_person:
            match_type = "name"

    # Duplicate found
    if duplicate_person:
        return JsonResponse({
            "duplicate": True,
            "message": "Warning: Duplicate person found",
            "match_type": match_type,
            "person_id": duplicate_person.id,
            "existing_name": duplicate_person.name,
            "existing_email": duplicate_person.email,
            "existing_phone": duplicate_person.phone,
        })

    # No duplicate found
    return JsonResponse({
        "duplicate": False,
        "message": "No duplicate found"
    })
