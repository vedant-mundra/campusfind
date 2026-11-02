"""MODULE 2 (Student 1) - Report an item: create, edit and delete your own reports.

Requests arrive as multipart/form-data because they may carry a photo.
"""
from flask import Blueprint, current_app, g, jsonify, request

from auth import login_required
from db import get_db
from helpers import ITEM_SELECT, item_to_dict, json_error
from images import ImageError, delete_image, save_item_image
from validators import validate_item

bp = Blueprint("items", __name__, url_prefix="/api/items")


def _store_photo(errors):
    """Save the uploaded photo (if any). Returns the new file name or None."""
    photo = request.files.get("photo")
    if photo is None or not photo.filename:
        return None
    try:
        return save_item_image(
            photo, current_app.config["UPLOAD_FOLDER"], current_app.config["MAX_IMAGE_BYTES"]
        )
    except ImageError as exc:
        errors["photo"] = str(exc)
        return None


@bp.post("")
@login_required
def create_item():
    cleaned, errors = validate_item(request.form)
    filename = _store_photo(errors)
    if errors:
        delete_image(current_app.config["UPLOAD_FOLDER"], filename)
        return json_error("Please fix the highlighted fields.", 422, errors)

    db = get_db()
    cur = db.execute(
        "INSERT INTO items (user_id, type, title, description, category, location,"
        " event_date, phone, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (g.user["id"], cleaned["type"], cleaned["title"], cleaned["description"],
         cleaned["category"], cleaned["location"], cleaned["event_date"],
         cleaned["phone"] or None, filename),
    )
    db.commit()
    row = db.execute(ITEM_SELECT + " WHERE i.id = ?", (cur.lastrowid,)).fetchone()
    response = jsonify({"item": item_to_dict(row, show_contact=True)})
    response.status_code = 201
    return response


def _own_item_or_error(item_id):
    """Fetch an item the current user owns, or return (None, error_response)."""
    row = get_db().execute(ITEM_SELECT + " WHERE i.id = ?", (item_id,)).fetchone()
    if row is None:
        return None, json_error("Item not found.", 404)
    if row["user_id"] != g.user["id"]:
        return None, json_error("You can only change your own reports.", 403)
    return row, None


@bp.put("/<int:item_id>")
@login_required
def update_item(item_id):
    row, error = _own_item_or_error(item_id)
    if error:
        return error
    if row["status"] == "resolved":
        return json_error("A resolved report can no longer be edited.", 409)

    cleaned, errors = validate_item(request.form)
    new_filename = _store_photo(errors)
    if errors:
        delete_image(current_app.config["UPLOAD_FOLDER"], new_filename)
        return json_error("Please fix the highlighted fields.", 422, errors)

    image = row["image"]
    if new_filename:                                   # a replacement photo was uploaded
        delete_image(current_app.config["UPLOAD_FOLDER"], image)
        image = new_filename
    elif request.form.get("remove_photo") == "1":      # the user removed the photo
        delete_image(current_app.config["UPLOAD_FOLDER"], image)
        image = None

    db = get_db()
    db.execute(
        "UPDATE items SET type=?, title=?, description=?, category=?, location=?,"
        " event_date=?, phone=?, image=? WHERE id=?",
        (cleaned["type"], cleaned["title"], cleaned["description"], cleaned["category"],
         cleaned["location"], cleaned["event_date"], cleaned["phone"] or None, image, item_id),
    )
    db.commit()
    updated = db.execute(ITEM_SELECT + " WHERE i.id = ?", (item_id,)).fetchone()
    return jsonify({"item": item_to_dict(updated, show_contact=True)})


@bp.delete("/<int:item_id>")
@login_required
def delete_item(item_id):
    row, error = _own_item_or_error(item_id)
    if error:
        return error
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))  # claims go with it (CASCADE)
    db.commit()
    delete_image(current_app.config["UPLOAD_FOLDER"], row["image"])
    return jsonify({"ok": True})
