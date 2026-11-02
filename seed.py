"""Load demo users, reports and claims so the site is not empty.

    python seed.py            # add demo data (skipped if users already exist)
    python seed.py --reset    # wipe the database and uploads first

All demo accounts use the password  Demo@1234
The demo photos are simple illustrations drawn with Pillow (no external images).
"""
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw
from werkzeug.security import generate_password_hash

from app import create_app
from db import get_db

PASSWORD = "Demo@1234"
SCALE = 2
W, H = 800 * SCALE, 500 * SCALE


# ------------------------------------------------------------------ tiny illustration helpers
def _canvas(bg):
    image = Image.new("RGB", (W, H), bg)
    return image, ImageDraw.Draw(image, "RGBA")


def _shadow(d, box):
    d.ellipse(box, fill=(14, 26, 58, 40))


def _finish(image):
    return image.resize((W // SCALE, H // SCALE), Image.LANCZOS)


def draw_backpack():
    img, d = _canvas("#e3e9f8")
    _shadow(d, (430, 850, 1170, 930))
    d.arc((690, 150, 910, 330), 180, 360, fill="#16244f", width=30)
    d.rounded_rectangle((420, 420, 500, 720), 36, fill="#16244f")
    d.rounded_rectangle((1100, 420, 1180, 720), 36, fill="#16244f")
    d.rounded_rectangle((500, 250, 1100, 860), 150, fill="#233a7a")
    d.rounded_rectangle((560, 520, 1040, 810), 90, fill="#2f4b9a")
    d.line((590, 380, 1010, 380), fill="#b9c6ef", width=12)
    d.ellipse((985, 355, 1035, 405), fill="#f5c542")
    d.line((620, 590, 980, 590), fill="#f5c542", width=10)
    d.line((1010, 405, 1040, 520), fill="#c0262d", width=8)
    d.ellipse((1020, 510, 1062, 552), fill="#c0262d")
    return _finish(img)


def _key(head_color, shaft_color):
    layer = Image.new("RGBA", (240, 700), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((100, 170, 140, 640), 16, fill=shaft_color)
    for y, w in ((520, 62), (570, 46), (615, 58)):
        d.rectangle((140, y, 140 + w, y + 24), fill=shaft_color)
    d.ellipse((30, 20, 210, 200), fill=head_color)
    d.ellipse((92, 80, 148, 136), fill=(0, 0, 0, 0))
    return layer


def draw_keys():
    img, d = _canvas("#fdf1c9")
    _shadow(d, (480, 880, 1120, 940))
    keys = [(_key("#c9a227", "#c9a227"), -28), (_key("#9aa3b5", "#9aa3b5"), 3), (_key("#d6dbe6", "#d6dbe6"), 30)]
    for layer, angle in keys:
        rotated = layer.rotate(angle, expand=True, resample=Image.BICUBIC, center=(120, 40))
        img.paste(rotated, (800 - rotated.width // 2, 300), rotated)
    d.ellipse((650, 140, 950, 440), outline="#5f6b85", width=26)
    return _finish(img)


def draw_phone():
    img, d = _canvas("#e1f1ea")
    _shadow(d, (520, 870, 1080, 940))
    d.rounded_rectangle((530, 110, 1070, 890), 110, fill="#2e9e6b")
    d.rounded_rectangle((565, 145, 1035, 855), 80, fill="#0b1020")
    for i in range(660):
        t = i / 660
        d.line((590, 180 + i, 1010, 180 + i), fill=(int(40 + 20 * t), int(90 - 30 * t), int(220 - 80 * t)))
    for r in range(4):
        for c in range(3):
            x, y = 625 + c * 125, 330 + r * 130
            d.rounded_rectangle((x, y, x + 90, y + 90), 24, fill=(255, 255, 255, 190))
    d.ellipse((780, 168, 820, 208), fill="#0b1020")
    return _finish(img)


def draw_idcard():
    img, d = _canvas("#e9e4f7")
    _shadow(d, (330, 800, 1270, 870))
    d.rounded_rectangle((380, 200, 1220, 780), 54, fill="#ffffff")
    d.rounded_rectangle((380, 200, 1220, 350), 54, fill="#2a4fd6")
    d.rectangle((380, 290, 1220, 350), fill="#2a4fd6")
    d.rounded_rectangle((740, 232, 860, 262), 14, fill="#e9e4f7")
    d.rounded_rectangle((450, 410, 710, 700), 24, fill="#cfd8ee")
    d.ellipse((520, 450, 640, 570), fill="#8c9ac4")
    d.pieslice((480, 560, 680, 760), 180, 360, fill="#8c9ac4")
    for y, w in ((430, 330), (500, 270), (570, 300), (640, 200)):
        d.rounded_rectangle((770, y, 770 + w, y + 30), 14, fill="#4b5878" if y == 430 else "#b6bfd6")
    return _finish(img)


def draw_bottle():
    img, d = _canvas("#dff3f4")
    _shadow(d, (600, 850, 1000, 925))
    d.rounded_rectangle((640, 250, 960, 860), 100, fill="#0e9aa7")
    d.rounded_rectangle((710, 160, 890, 290), 34, fill="#0b7e89")
    d.rounded_rectangle((690, 70, 910, 190), 40, fill="#1f2937")
    d.rectangle((640, 480, 960, 690), fill="#e8f7f8")
    d.rounded_rectangle((720, 540, 880, 575), 12, fill="#0e9aa7")
    d.rounded_rectangle((720, 600, 840, 628), 12, fill="#7fcfd6")
    d.rounded_rectangle((680, 300, 712, 450), 16, fill=(255, 255, 255, 90))
    return _finish(img)


def draw_umbrella():
    img, d = _canvas("#f3e9d8")
    _shadow(d, (480, 880, 1120, 940))
    left, top, right, bottom = 300, 170, 1300, 900
    shades = ["#1f2937", "#374151", "#1f2937", "#374151", "#1f2937"]
    for i, shade in enumerate(shades):
        d.pieslice((left, top, right, bottom), 180 + i * 36, 216 + i * 36, fill=shade)
    d.rectangle((left - 5, 535, right + 5, 560), fill="#f3e9d8")
    for i in range(5):  # scalloped edge
        x0 = left + i * 200
        d.pieslice((x0, 470, x0 + 200, 610), 0, 180, fill=shades[i])
    d.rectangle((792, 535, 808, 800), fill="#6b4a25")
    d.arc((712, 740, 808, 860), 0, 180, fill="#a8743a", width=26)
    d.rectangle((793, 140, 807, 180), fill="#6b4a25")
    return _finish(img)


DRAWERS = {"backpack": draw_backpack, "keys": draw_keys, "phone": draw_phone,
           "idcard": draw_idcard, "bottle": draw_bottle, "umbrella": draw_umbrella}


def save_illustration(kind, folder):
    os.makedirs(folder, exist_ok=True)
    name = uuid.uuid4().hex + ".jpg"
    DRAWERS[kind]().save(os.path.join(folder, name), "JPEG", quality=88)
    return name


# ------------------------------------------------------------------ demo content
USERS = [
    ("Asha Rao", "asha@example.com"),
    ("Rohan Kamath", "rohan@example.com"),
    ("Meera Shetty", "meera@example.com"),
    ("Kiran Pai", "kiran@example.com"),
]

# (owner index, type, title, category, location, days ago, description, phone, image kind, status)
ITEMS = [
    (3, "lost", "Silver wristwatch", "Other", "Sports Complex", 10,
     "Silver analogue watch with a brown leather strap. The back has initials K.P. engraved.", "", None, "open"),
    (0, "found", "Pencil case with blue pens", "Books & Stationery", "Academic Block 1", 9,
     "Green zip pencil case with six blue pens and a small ruler. Left on a bench near room 104.", "98450 12345", None, "resolved"),
    (1, "lost", "Prescription glasses", "Other", "Bus Stop", 8,
     "Black rectangular frame in a grey hard case. Strong prescription, I cannot see well without them.", "", None, "open"),
    (3, "found", "Wireless earbuds in white case", "Electronics", "Auditorium", 6,
     "White charging case with a small scratch on the lid. Found on seat row F after the guest lecture.", "", None, "open"),
    (2, "lost", "Brown leather wallet", "Wallet & Money", "Food Court", 6,
     "Brown bi-fold wallet with a student card and a bank card inside. Please do not use the cards.", "", None, "open"),
    (0, "found", "Grey hooded sweatshirt", "Bags & Clothing", "Parking Area", 5,
     "Plain grey hoodie, size M, with a ripped left pocket. Found folded on a scooter seat.", "", None, "open"),
    (3, "lost", "Data Structures textbook", "Books & Stationery", "Central Library", 4,
     "Hardcover, blue cover. Has colourful sticky notes on the chapters about trees and graphs.", "", None, "open"),
    (1, "found", "Casio scientific calculator", "Electronics", "Academic Block 2", 3,
     "Black Casio fx-991 in a blue slip cover. Found on the desk near the window after the exam.", "", None, "open"),
    (2, "lost", "Teal steel water bottle", "Other", "Hostel Block", 3,
     "750 ml teal bottle with a dent near the bottom and a white label with a wave drawing.", "", "bottle", "open"),
    (0, "found", "Student ID card", "Documents & ID", "Main Gate", 2,
     "Blue-banded university ID card, found near the gate security desk. The name is partly worn off.", "", "idcard", "open"),
    (3, "lost", "Phone with green case", "Electronics", "Sports Complex", 2,
     "Black phone in a green rubber case. Lock screen is a photo of a beach at sunset.", "", "phone", "open"),
    (2, "found", "Set of three keys on a ring", "Keys", "Academic Block 1", 1,
     "One gold and two silver keys on a steel ring. No keychain. Handed to the lab assistant for now.", "", "keys", "open"),
    (1, "lost", "Navy blue backpack", "Bags & Clothing", "Central Library", 1,
     "Navy backpack with a red keychain on the zip. Holds two notebooks and a pencil case.", "", "backpack", "open"),
    (0, "found", "Black umbrella with wooden handle", "Other", "Food Court", 0,
     "Large black umbrella, wooden J-shaped handle. Left beside the tray return after the rain.", "98450 12345", "umbrella", "open"),
]

# (item title, claimant index, message, status)
CLAIMS = [
    ("Black umbrella with wooden handle", 1, "Mine has a small chip on the tip of the handle and I wrote my initials R.K. on the strap.", "pending"),
    ("Black umbrella with wooden handle", 2, "I left it near the tray return around 4 pm. It has a loose button on the strap.", "pending"),
    ("Pencil case with blue pens", 3, "The ruler has my roll number scratched on the back. The pens are Reynolds Trimax.", "approved"),
    ("Navy blue backpack", 0, "I think I saw this on the second-floor reading table yesterday and kept it at the library desk.", "pending"),
    ("Teal steel water bottle", 0, "I found a similar bottle at the hostel entrance. The label has a wave drawing.", "rejected"),
]


def seed(reset=False):
    app = create_app()
    with app.app_context():
        if reset:
            for path in (app.config["DATABASE"],):
                if os.path.exists(path):
                    os.remove(path)
            shutil.rmtree(app.config["UPLOAD_FOLDER"], ignore_errors=True)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            from db import init_db
            init_db()
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            print("Database already has users. Run with --reset to start over.")
            return

        password_hash = generate_password_hash(PASSWORD)
        user_ids = []
        for name, email in USERS:
            cur = db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                             (name, email, password_hash))
            user_ids.append(cur.lastrowid)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        item_ids = {}
        for n, (owner, kind, title, category, location, days, desc, phone, image, status) in enumerate(ITEMS):
            event_day = (datetime.now() - timedelta(days=days)).date().isoformat()
            created = (now - timedelta(days=days, hours=2) + timedelta(minutes=n)).strftime("%Y-%m-%d %H:%M:%S")
            filename = save_illustration(image, app.config["UPLOAD_FOLDER"]) if image else None
            cur = db.execute(
                "INSERT INTO items (user_id, type, title, description, category, location, event_date,"
                " phone, image, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (user_ids[owner], kind, title, desc, category, location, event_day,
                 phone or None, filename, status, created))
            item_ids[title] = cur.lastrowid

        for n, (title, claimant, message, status) in enumerate(CLAIMS):
            created = (now - timedelta(hours=5 - n)).strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO claims (item_id, claimant_id, message, status, created_at) VALUES (?,?,?,?,?)",
                       (item_ids[title], user_ids[claimant], message, status, created))
        db.commit()
        print(f"Seeded {len(USERS)} users, {len(ITEMS)} items and {len(CLAIMS)} claims.")
        print(f"Log in with any of these emails and the password {PASSWORD}:")
        for name, email in USERS:
            print(f"  {name:<14} {email}")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
