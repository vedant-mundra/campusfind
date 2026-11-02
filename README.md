# CampusFind: Campus Lost & Found Portal

Full-stack Web Technology mini project (ICT 3131). Students and staff report lost or found items, search them,
send claims, and the reporter approves a claim to release their contact details.

**Stack:** Flask 3 (Python) + SQLite, HTML5 + Bootstrap 5.3 + vanilla JavaScript (fetch / JSON), PyJWT for login
cookies, Pillow for safe photo uploads. Bootstrap, fonts and icons are bundled, so it works without internet.

## Run it

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS / Linux:  source .venv/bin/activate
pip install -r requirements.txt

python seed.py --reset      # optional: demo users, 14 reports, 5 claims
python app.py               # open http://localhost:5000
```

Demo accounts (after `python seed.py --reset`), all with the password **Demo@1234**:

| Name | Email |
| --- | --- |
| Asha Rao | asha@example.com |
| Rohan Kamath | rohan@example.com |
| Meera Shetty | meera@example.com |
| Kiran Pai | kiran@example.com |

Asha has pending claims waiting on her dashboard, so log in as her to try approving a claim.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

23 API tests cover registration, login, validation, photo handling, ownership rules, search, claims and the
rule that contact details stay hidden until a claim is approved.

## Features and work split

| # | Feature | Module | Student |
| --- | --- | --- | --- |
| 1 | Register (client + server validation, hashed password) | User Authentication | 1 |
| 2 | Log in / log out (JWT in an HttpOnly cookie) | User Authentication | 1 |
| 3 | Report a lost or found item with photo | Report an Item | 1 |
| 4 | Edit / delete own report, replace or remove photo | Report an Item | 1 |
| 5 | Browse, search, filter, sort, paginate | Browse, Search & Claim | 2 |
| 6 | Item details and send a claim | Browse, Search & Claim | 2 |
| 7 | Approve / decline claims, contact reveal | Dashboard & Claim Review | 2 |
| 8 | Dashboard: stats, my reports, mark returned, my claims | Dashboard & Claim Review | 2 |

## Project layout

```
app.py            create_app(), HTML page routes, error pages, security headers
config.py         settings (secret key, database, upload folder, limits)
db.py, schema.sql SQLite connection and table definitions
auth.py           Module 1  /api/auth/*   register, login, logout, current user
items.py          Module 2  /api/items    create, edit, delete a report (multipart form)
browse.py         Module 3  /api/items    list/search, item detail, claims, public stats
dashboard.py      Module 4  /api/me/*, claim decisions, mark returned
validators.py     server-side validation rules
images.py         photo checking and re-encoding
helpers.py        shared JSON helpers
seed.py           demo data (photos are drawn with Pillow)
templates/        Jinja pages: base layout + index, login, register, report, browse, dashboard, 404
static/js/        common.js (shared helpers) + one script per page
static/css/       style.css (theme on top of Bootstrap)
static/vendor/    Bootstrap 5.3.2 (MIT licence)
tests/            unittest API tests
```

## Security notes

* Passwords are stored as salted scrypt hashes (Werkzeug), never in plain text.
* Login token: JWT in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` when `CAMPUSFIND_HTTPS=1`).
* All SQL uses `?` parameters; all text is escaped before it is put into the page.
* Uploaded photos are opened with Pillow and re-encoded as new JPEG files with random names.
* Content-Security-Policy, `X-Content-Type-Options`, `X-Frame-Options` headers on every response.
* Set `CAMPUSFIND_SECRET` to a long random value before any real deployment.

## Put it on GitHub

```bash
git init
git add .
git commit -m "CampusFind: campus lost and found portal"
git branch -M main
git remote add origin https://github.com/<your-username>/campusfind.git
git push -u origin main
```

Then paste the repository link into the report (Section 1, "Source code").
