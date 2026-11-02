"""Server-side validation. The browser validates too, but the server never trusts it."""
import re
from datetime import date, timedelta

CATEGORIES = [
    "Electronics",
    "Documents & ID",
    "Books & Stationery",
    "Bags & Clothing",
    "Keys",
    "Wallet & Money",
    "Other",
]
ITEM_TYPES = ("lost", "found")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{8,13}[0-9]$")  # 10-15 digits, spaces/dashes allowed


def _text(data, key):
    """Read a field as a trimmed string (works for JSON dicts and form MultiDicts)."""
    value = data.get(key)
    return value.strip() if isinstance(value, str) else ""


def validate_registration(data):
    name = _text(data, "name")
    email = _text(data, "email").lower()
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    confirm = data.get("confirm_password") if isinstance(data.get("confirm_password"), str) else ""
    errors = {}

    if not 2 <= len(name) <= 60:
        errors["name"] = "Name must be 2 to 60 characters long."
    if not EMAIL_RE.match(email) or len(email) > 120:
        errors["email"] = "Enter a valid email address."
    if not 8 <= len(password) <= 128:
        errors["password"] = "Password must be 8 to 128 characters long."
    elif not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        errors["password"] = "Password must contain at least one letter and one number."
    if "password" not in errors and password != confirm:
        errors["confirm_password"] = "The two passwords do not match."

    return {"name": name, "email": email, "password": password}, errors


def validate_login(data):
    email = _text(data, "email").lower()
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    errors = {}
    if not email:
        errors["email"] = "Enter your email address."
    if not password:
        errors["password"] = "Enter your password."
    return {"email": email, "password": password}, errors


def validate_item(data):
    """Validate the report-an-item form. Returns (cleaned_values, errors)."""
    cleaned = {
        "type": _text(data, "type"),
        "title": _text(data, "title"),
        "category": _text(data, "category"),
        "location": _text(data, "location"),
        "event_date": _text(data, "event_date"),
        "description": _text(data, "description"),
        "phone": _text(data, "phone"),
    }
    errors = {}

    if cleaned["type"] not in ITEM_TYPES:
        errors["type"] = "Choose whether the item was lost or found."
    if not 3 <= len(cleaned["title"]) <= 80:
        errors["title"] = "Title must be 3 to 80 characters long."
    if cleaned["category"] not in CATEGORIES:
        errors["category"] = "Choose a category from the list."
    if not 2 <= len(cleaned["location"]) <= 80:
        errors["location"] = "Location must be 2 to 80 characters long."
    if not 10 <= len(cleaned["description"]) <= 500:
        errors["description"] = "Description must be 10 to 500 characters long."
    if cleaned["phone"] and not PHONE_RE.match(cleaned["phone"]):
        errors["phone"] = "Enter a valid phone number (10 to 15 digits) or leave it empty."

    try:
        when = date.fromisoformat(cleaned["event_date"])
        if when > date.today():
            errors["event_date"] = "The date cannot be in the future."
        elif when < date.today() - timedelta(days=365):
            errors["event_date"] = "The date cannot be more than a year ago."
    except ValueError:
        errors["event_date"] = "Enter a valid date."

    return cleaned, errors


def validate_claim(data):
    message = _text(data, "message")
    errors = {}
    if not 10 <= len(message) <= 500:
        errors["message"] = "Describe how you can prove this is yours (10 to 500 characters)."
    return {"message": message}, errors
