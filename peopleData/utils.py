import re
from datetime import datetime


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def clean_name(value):
    return " ".join(
        clean_text(value).lower().split()
    )


def clean_email(value):
    return clean_text(value).lower()


def clean_phone(value):
    digits = re.sub(r"\D", "", clean_text(value))

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    # Some local Indian numbers are exported with a leading trunk zero.
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    return digits

def clean_city(value):
    city = clean_text(value).lower()

    city_mapping = {
        "gurgaon": "gurugram",
        "gurugram": "gurugram",
        "bangalore": "bengaluru",
        "bengaluru": "bengaluru",
        "noida": "noida",
        "pune": "pune",
    }

    return city_mapping.get(city, city)

def clean_status(value):
    status = clean_text(value).lower()

    if status in ["active"]:
        return "active"

    if status in ["inactive"]:
        return "inactive"

    if status in ["paused"]:
        return "paused"

    return status

def clean_verified(value):
    verified = clean_text(value).lower()

    if verified in ["y", "yes"]:
        return "Yes"

    if verified in ["n", "no"]:
        return "No"

    return None

def clean_date(value):
    value = clean_text(value)

    formats = [
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%m/%d/%Y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return None

def clean_ctc(value):
    value = clean_text(value)

    if not value:
        return None

    try:
        ctc = float(value)

        if ctc < 100:
            return int(ctc * 100000)

        return int(ctc)

    except ValueError:
        return None

def clean_rate(value):
    value = clean_text(value).lower()

    if not value:
        return None

    if "/" not in value:
        return None

    amount, rate_type = value.split("/", 1)

    try:
        if amount.endswith("k"):
            amount = int(float(amount[:-1]) * 1000)
        else:
            amount = int(float(amount))

        return f"{amount}/{rate_type}"

    except ValueError:
        return None
