"""SQLite connection handling (one connection per request)."""
import sqlite3

from flask import current_app, g


def get_db():
    """Return the request-scoped database connection, opening it on first use."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row          # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")  # enforce ON DELETE CASCADE
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the tables if they do not exist yet."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    db.commit()
