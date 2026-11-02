"""Small helpers shared by the API modules."""
from flask import jsonify


def json_error(message, status, errors=None):
    """Uniform error body: {"error": "...", "errors": {field: message}}."""
    body = {"error": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def item_to_dict(row, show_contact=False):
    """Convert a joined items/users row to the JSON shape sent to the browser.

    The reporter's e-mail and phone are private: they are included only when
    show_contact is True (the owner, or a claimant whose claim was approved).
    """
    data = {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "location": row["location"],
        "event_date": row["event_date"],
        "status": row["status"],
        "created_at": row["created_at"],
        "reporter_name": row["reporter_name"],
        "image_url": f"/uploads/{row['image']}" if row["image"] else None,
    }
    if show_contact:
        data["contact"] = {"email": row["reporter_email"], "phone": row["phone"]}
    return data


ITEM_SELECT = (
    "SELECT i.*, u.name AS reporter_name, u.email AS reporter_email "
    "FROM items i JOIN users u ON u.id = i.user_id"
)


def int_arg(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
