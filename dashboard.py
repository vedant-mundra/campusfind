"""MODULE 4 (Student 2) - Dashboard: my reports, claims received/sent, decisions, stats."""
from flask import Blueprint, g, jsonify, request

from auth import login_required
from db import get_db
from helpers import json_error

bp = Blueprint("dashboard", __name__, url_prefix="/api")


@bp.get("/me/stats")
@login_required
def my_stats():
    db = get_db()
    uid = g.user["id"]
    one = lambda sql: db.execute(sql, (uid,)).fetchone()[0]  # noqa: E731
    return jsonify({
        "reports": one("SELECT COUNT(*) FROM items WHERE user_id = ?"),
        "open": one("SELECT COUNT(*) FROM items WHERE user_id = ? AND status = 'open'"),
        "resolved": one("SELECT COUNT(*) FROM items WHERE user_id = ? AND status = 'resolved'"),
        "pending_received": one(
            "SELECT COUNT(*) FROM claims c JOIN items i ON i.id = c.item_id "
            "WHERE i.user_id = ? AND c.status = 'pending'"
        ),
        "claims_sent": one("SELECT COUNT(*) FROM claims WHERE claimant_id = ?"),
    })


@bp.get("/me/items")
@login_required
def my_items():
    rows = get_db().execute(
        "SELECT i.id, i.type, i.title, i.category, i.location, i.event_date, i.status,"
        " i.image, i.created_at,"
        " (SELECT COUNT(*) FROM claims c WHERE c.item_id = i.id AND c.status = 'pending')"
        "   AS pending_claims"
        " FROM items i WHERE i.user_id = ? ORDER BY i.created_at DESC, i.id DESC",
        (g.user["id"],),
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["image_url"] = f"/uploads/{d.pop('image')}" if r["image"] else None
        items.append(d)
    return jsonify({"items": items})


@bp.get("/me/claims/received")
@login_required
def claims_received():
    rows = get_db().execute(
        "SELECT c.id, c.item_id, c.message, c.status, c.created_at,"
        " i.title AS item_title, i.type AS item_type, u.name AS claimant_name,"
        " u.email AS claimant_email"
        " FROM claims c JOIN items i ON i.id = c.item_id JOIN users u ON u.id = c.claimant_id"
        " WHERE i.user_id = ?"
        " ORDER BY (c.status = 'pending') DESC, c.created_at DESC, c.id DESC",
        (g.user["id"],),
    ).fetchall()
    claims = []
    for r in rows:
        d = dict(r)
        if r["status"] != "approved":      # the claimant's e-mail is revealed only on approval
            d.pop("claimant_email")
        claims.append(d)
    return jsonify({"claims": claims})


@bp.get("/me/claims")
@login_required
def claims_sent():
    rows = get_db().execute(
        "SELECT c.id, c.item_id, c.message, c.status, c.created_at, i.title AS item_title,"
        " i.type AS item_type, i.phone AS reporter_phone, u.name AS reporter_name,"
        " u.email AS reporter_email"
        " FROM claims c JOIN items i ON i.id = c.item_id JOIN users u ON u.id = i.user_id"
        " WHERE c.claimant_id = ? ORDER BY c.created_at DESC, c.id DESC",
        (g.user["id"],),
    ).fetchall()
    claims = []
    for r in rows:
        d = dict(r)
        phone, email = d.pop("reporter_phone"), d.pop("reporter_email")
        if r["status"] == "approved":      # contact details are revealed only on approval
            d["contact"] = {"email": email, "phone": phone}
        claims.append(d)
    return jsonify({"claims": claims})


@bp.post("/claims/<int:claim_id>/decision")
@login_required
def decide_claim(claim_id):
    decision = (request.get_json(silent=True) or {}).get("decision")
    if decision not in ("approved", "rejected"):
        return json_error("Decision must be 'approved' or 'rejected'.", 422)

    db = get_db()
    claim = db.execute(
        "SELECT c.id, c.item_id, c.status, i.user_id AS owner_id, i.status AS item_status"
        " FROM claims c JOIN items i ON i.id = c.item_id WHERE c.id = ?",
        (claim_id,),
    ).fetchone()
    if claim is None:
        return json_error("Claim not found.", 404)
    if claim["owner_id"] != g.user["id"]:
        return json_error("Only the person who reported the item can decide on claims.", 403)
    if claim["status"] != "pending" or claim["item_status"] != "open":
        return json_error("This claim has already been decided.", 409)

    # One transaction: either all of these changes happen, or none.
    db.execute("UPDATE claims SET status = ? WHERE id = ?", (decision, claim_id))
    if decision == "approved":
        db.execute("UPDATE items SET status = 'resolved' WHERE id = ?", (claim["item_id"],))
        db.execute(
            "UPDATE claims SET status = 'rejected' WHERE item_id = ? AND status = 'pending'",
            (claim["item_id"],),
        )
    db.commit()
    return jsonify({"ok": True, "status": decision})


@bp.post("/items/<int:item_id>/resolve")
@login_required
def resolve_item(item_id):
    db = get_db()
    item = db.execute("SELECT user_id, status FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        return json_error("Item not found.", 404)
    if item["user_id"] != g.user["id"]:
        return json_error("You can only change your own reports.", 403)
    if item["status"] == "resolved":
        return json_error("This item is already resolved.", 409)

    db.execute("UPDATE items SET status = 'resolved' WHERE id = ?", (item_id,))
    db.execute("UPDATE claims SET status = 'rejected' WHERE item_id = ? AND status = 'pending'", (item_id,))
    db.commit()
    return jsonify({"ok": True})
