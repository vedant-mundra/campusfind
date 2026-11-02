"""MODULE 1 (Student 1) - User authentication: register, login, logout.

Sessions use a JWT stored in an HttpOnly cookie, so JavaScript can never read the token.
"""
import datetime as dt
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db
from helpers import json_error
from validators import validate_login, validate_registration

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Compared against when the e-mail is unknown, so the response time does not reveal
# whether an account exists.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


# ---------- token helpers ----------
def issue_token(user_id):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(hours=current_app.config["JWT_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def read_token(token):
    """Return the user id inside a valid token, or None if it is invalid/expired."""
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def set_auth_cookie(response, user_id):
    response.set_cookie(
        current_app.config["COOKIE_NAME"],
        issue_token(user_id),
        max_age=current_app.config["JWT_HOURS"] * 3600,
        httponly=True,                      # not readable from JavaScript
        samesite="Lax",                     # not sent on cross-site POSTs (CSRF defence)
        secure=current_app.config["COOKIE_SECURE"],
    )
    return response


def load_user():
    """before_request hook: put the logged-in user (or None) on flask.g."""
    g.user = None
    token = request.cookies.get(current_app.config["COOKIE_NAME"])
    user_id = read_token(token) if token else None
    if user_id:
        g.user = get_db().execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    """Decorator for API routes that need a logged-in user."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return json_error("Please log in to continue.", 401)
        return view(*args, **kwargs)
    return wrapped


def user_json(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


# ---------- routes ----------
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_registration(data)
    if errors:
        return json_error("Please fix the highlighted fields.", 422, errors)

    db = get_db()
    exists = db.execute("SELECT 1 FROM users WHERE email = ?", (cleaned["email"],)).fetchone()
    if exists:
        return json_error(
            "Please fix the highlighted fields.", 422,
            {"email": "An account with this email already exists."},
        )

    cur = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (cleaned["name"], cleaned["email"], generate_password_hash(cleaned["password"])),
    )
    db.commit()
    user = db.execute("SELECT id, name, email FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    response = jsonify({"user": user_json(user)})
    response.status_code = 201
    return set_auth_cookie(response, user["id"])


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_login(data)
    if errors:
        return json_error("Please fix the highlighted fields.", 422, errors)

    row = get_db().execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?", (cleaned["email"],)
    ).fetchone()
    stored_hash = row["password_hash"] if row else _DUMMY_HASH
    password_ok = check_password_hash(stored_hash, cleaned["password"])
    if not row or not password_ok:
        return json_error("Incorrect email or password.", 401)

    return set_auth_cookie(jsonify({"user": user_json(row)}), row["id"])


@bp.post("/logout")
def logout():
    response = jsonify({"ok": True})
    response.delete_cookie(current_app.config["COOKIE_NAME"])
    return response


@bp.get("/me")
def me():
    return jsonify({"user": user_json(g.user) if g.user else None})
