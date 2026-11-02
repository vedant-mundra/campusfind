"""MODULE 3 (Student 2) - Browse & search items, view details, submit a claim."""
import math

from flask import Blueprint, g, jsonify, request

from auth import login_required
from db import get_db
from helpers import ITEM_SELECT, int_arg, item_to_dict, json_error
from validators import CATEGORIES, ITEM_TYPES, validate_claim

bp = Blueprint("browse", __name__)


def _like(text):
    """Escape LIKE wildcards so a search for '50%' matches literally."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@bp.get("/api/items")
def list_items():
    args = request.args
    query = args.get("q", "").strip()[:80]
    item_type = args.get("type", "")
    category = args.get("category", "")
    include_resolved = args.get("resolved") == "1"
    oldest_first = args.get("sort") == "oldest"
    page = max(int_arg(args.get("page"), 1), 1)
    per_page = min(max(int_arg(args.get("per_page"), 9), 1), 24)

    where, params = [], []
    if not include_resolved:
        where.append("i.status = 'open'")
    if item_type in ITEM_TYPES:
        where.append("i.type = ?")
        params.append(item_type)
    if category in CATEGORIES:
        where.append("i.category = ?")
        params.append(category)
    if query:
        like = _like(query)
        where.append(
            "(i.title LIKE ? ESCAPE '\\' OR i.description LIKE ? ESCAPE '\\'"
            " OR i.location LIKE ? ESCAPE '\\')"
        )
        params += [like, like, like]
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    order = "i.created_at ASC, i.id ASC" if oldest_first else "i.created_at DESC, i.id DESC"

    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM items i" + clause, params).fetchone()[0]
    rows = db.execute(
        ITEM_SELECT + clause + f" ORDER BY {order} LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page],
    ).fetchall()

    return jsonify({
        "items": [item_to_dict(r) for r in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(math.ceil(total / per_page), 1),
    })


@bp.get("/api/items/<int:item_id>")
def item_detail(item_id):
    db = get_db()
    row = db.execute(ITEM_SELECT + " WHERE i.id = ?", (item_id,)).fetchone()
    if row is None:
        return json_error("Item not found.", 404)

    is_owner = g.user is not None and g.user["id"] == row["user_id"]
    my_claim = None
    if g.user is not None and not is_owner:
        claim = db.execute(
            "SELECT id, status, message, created_at FROM claims WHERE item_id = ? AND claimant_id = ?",
            (item_id, g.user["id"]),
        ).fetchone()
        my_claim = dict(claim) if claim else None

    # Contact details are private: owner, or a claimant whose claim was approved.
    show_contact = is_owner or (my_claim is not None and my_claim["status"] == "approved")
    data = item_to_dict(row, show_contact=show_contact)
    data["is_owner"] = is_owner
    data["my_claim"] = my_claim
    return jsonify({"item": data})


@bp.post("/api/items/<int:item_id>/claims")
@login_required
def create_claim(item_id):
    db = get_db()
    item = db.execute("SELECT id, user_id, status FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        return json_error("Item not found.", 404)
    if item["user_id"] == g.user["id"]:
        return json_error("You cannot claim your own report.", 403)
    if item["status"] != "open":
        return json_error("This item has already been resolved.", 409)

    cleaned, errors = validate_claim(request.get_json(silent=True) or {})
    if errors:
        return json_error("Please fix the highlighted fields.", 422, errors)

    already = db.execute(
        "SELECT 1 FROM claims WHERE item_id = ? AND claimant_id = ?", (item_id, g.user["id"])
    ).fetchone()
    if already:
        return json_error("You have already sent a claim for this item.", 409)

    cur = db.execute(
        "INSERT INTO claims (item_id, claimant_id, message) VALUES (?, ?, ?)",
        (item_id, g.user["id"], cleaned["message"]),
    )
    db.commit()
    claim = db.execute(
        "SELECT id, status, message, created_at FROM claims WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    response = jsonify({"claim": dict(claim)})
    response.status_code = 201
    return response


@bp.get("/api/stats")
def public_stats():
    db = get_db()
    count = lambda sql: db.execute(sql).fetchone()[0]  # noqa: E731
    return jsonify({
        "open_lost": count("SELECT COUNT(*) FROM items WHERE type='lost' AND status='open'"),
        "open_found": count("SELECT COUNT(*) FROM items WHERE type='found' AND status='open'"),
        "resolved": count("SELECT COUNT(*) FROM items WHERE status='resolved'"),
        "members": count("SELECT COUNT(*) FROM users"),
    })
