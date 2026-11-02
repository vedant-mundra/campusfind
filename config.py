"""Application configuration for CampusFind."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    # Secret used to sign the JWT login cookie. Override it outside development:
    #   export CAMPUSFIND_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    SECRET_KEY = os.environ.get(
        "CAMPUSFIND_SECRET", "dev-only-secret-change-me-in-production-0123456789"
    )

    DATABASE = os.environ.get(
        "CAMPUSFIND_DB", os.path.join(INSTANCE_DIR, "campusfind.db")
    )
    UPLOAD_FOLDER = os.environ.get(
        "CAMPUSFIND_UPLOADS", os.path.join(INSTANCE_DIR, "uploads")
    )

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # reject any request body above 4 MB
    MAX_IMAGE_BYTES = 3 * 1024 * 1024     # a single photo may be at most 3 MB

    JWT_HOURS = 8                          # how long a login stays valid
    COOKIE_NAME = "cf_token"
    # Set CAMPUSFIND_HTTPS=1 when serving over HTTPS so the cookie is Secure.
    COOKIE_SECURE = os.environ.get("CAMPUSFIND_HTTPS", "0") == "1"
