"""CampusFind - a campus Lost & Found portal (Flask + SQLite + Bootstrap)."""
import os
from datetime import date

from flask import (Flask, g, jsonify, redirect, render_template, request,
                   send_from_directory, url_for)

import auth
import browse
import dashboard
import db
import items
from config import Config
from validators import CATEGORIES


def safe_next(target):
    """Allow only same-site relative paths in ?next= (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.teardown_appcontext(db.close_db)
    app.before_request(auth.load_user)
    for blueprint in (auth.bp, items.bp, browse.bp, dashboard.bp):
        app.register_blueprint(blueprint)
    with app.app_context():
        db.init_db()

    # ---------- template context ----------
    @app.context_processor
    def inject_globals():
        return {"current_user": g.get("user"), "categories": CATEGORIES, "year": date.today().year}

    # ---------- HTML pages ----------
    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/login")
    def login_page():
        if g.user:
            return redirect(safe_next(request.args.get("next")) or url_for("dashboard_page"))
        return render_template("login.html", next_url=safe_next(request.args.get("next")) or "")

    @app.get("/register")
    def register_page():
        if g.user:
            return redirect(url_for("dashboard_page"))
        return render_template("register.html")

    @app.get("/browse")
    def browse_page():
        return render_template("browse.html")

    def login_redirect():
        return redirect(url_for("login_page", next=request.full_path.rstrip("?")))

    @app.get("/report")
    def report_page():
        if not g.user:
            return login_redirect()
        return render_template("report.html")

    @app.get("/dashboard")
    def dashboard_page():
        if not g.user:
            return login_redirect()
        return render_template("dashboard.html")

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, max_age=3600)

    # ---------- errors ----------
    def wants_json():
        return request.path.startswith("/api/")

    @app.errorhandler(404)
    def not_found(_e):
        if wants_json():
            return jsonify({"error": "Not found."}), 404
        return render_template("404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify({"error": "The upload is too large (limit 4 MB).",
                        "errors": {"photo": "Photo must be 3 MB or smaller."}}), 413

    @app.errorhandler(500)
    def server_error(_e):
        if wants_json():
            return jsonify({"error": "Something went wrong on the server."}), 500
        return render_template("404.html", server_error=True), 500

    # ---------- security headers ----------
    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; frame-ancestors 'none'",
        )
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
