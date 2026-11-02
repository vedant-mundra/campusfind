"""API tests. Run from the project folder with:  python -m unittest discover -s tests -v"""
import io
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from app import create_app  # noqa: E402

TODAY = date.today().isoformat()


def png_bytes(size=(40, 30), color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    return buf


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "DATABASE": os.path.join(self.tmp.name, "test.db"),
            "UPLOAD_FOLDER": os.path.join(self.tmp.name, "uploads"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    # ----- helpers -----
    def new_client(self):
        return self.app.test_client()

    def register(self, client, name="Asha Rao", email="asha@example.com", password="secret123"):
        return client.post("/api/auth/register", json={
            "name": name, "email": email, "password": password, "confirm_password": password})

    def item_form(self, **overrides):
        data = {"type": "lost", "title": "Blue water bottle", "category": "Other",
                "location": "Central Library", "event_date": TODAY,
                "description": "Steel bottle with a dent near the bottom.", "phone": ""}
        data.update(overrides)
        return data

    def create_item(self, client, photo=False, **overrides):
        data = self.item_form(**overrides)
        if photo:
            data["photo"] = (png_bytes(), "bottle.png")
        return client.post("/api/items", data=data, content_type="multipart/form-data")


class AuthTests(ApiTestCase):
    def test_register_logs_in_and_me_works(self):
        res = self.register(self.client)
        self.assertEqual(res.status_code, 201)
        self.assertIn("cf_token", res.headers.get("Set-Cookie", ""))
        self.assertIn("HttpOnly", res.headers.get("Set-Cookie", ""))
        me = self.client.get("/api/auth/me").get_json()
        self.assertEqual(me["user"]["email"], "asha@example.com")

    def test_register_validation_errors(self):
        res = self.client.post("/api/auth/register", json={
            "name": "A", "email": "bad", "password": "short", "confirm_password": "x"})
        self.assertEqual(res.status_code, 422)
        errors = res.get_json()["errors"]
        self.assertEqual(set(errors), {"name", "email", "password"})

    def test_password_needs_letter_and_digit_and_must_match(self):
        res = self.client.post("/api/auth/register", json={
            "name": "Asha", "email": "a@b.co", "password": "onlyletters",
            "confirm_password": "onlyletters"})
        self.assertIn("password", res.get_json()["errors"])
        res = self.client.post("/api/auth/register", json={
            "name": "Asha", "email": "a@b.co", "password": "secret123",
            "confirm_password": "secret124"})
        self.assertIn("confirm_password", res.get_json()["errors"])

    def test_duplicate_email_rejected_case_insensitively(self):
        self.register(self.client)
        res = self.register(self.new_client(), email="ASHA@example.com")
        self.assertEqual(res.status_code, 422)
        self.assertIn("email", res.get_json()["errors"])

    def test_login_logout(self):
        self.register(self.client)
        other = self.new_client()
        bad = other.post("/api/auth/login", json={"email": "asha@example.com", "password": "nope1234"})
        self.assertEqual(bad.status_code, 401)
        good = other.post("/api/auth/login", json={"email": "Asha@Example.com", "password": "secret123"})
        self.assertEqual(good.status_code, 200)
        self.assertIsNotNone(other.get("/api/auth/me").get_json()["user"])
        other.post("/api/auth/logout")
        self.assertIsNone(other.get("/api/auth/me").get_json()["user"])

    def test_passwords_are_hashed(self):
        self.register(self.client)
        with self.app.app_context():
            from db import get_db
            stored = get_db().execute("SELECT password_hash FROM users").fetchone()[0]
        self.assertNotIn("secret123", stored)

    def test_tampered_token_is_ignored(self):
        self.register(self.client)
        self.client.set_cookie("cf_token", "not.a.token")
        self.assertIsNone(self.client.get("/api/auth/me").get_json()["user"])

    def test_protected_pages_redirect_and_next_is_safe(self):
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login?next=/dashboard", res.headers["Location"])
        self.register(self.client)
        res = self.client.get("/login?next=//evil.com")
        self.assertEqual(res.headers["Location"], "/dashboard")


class ItemTests(ApiTestCase):
    def test_requires_login(self):
        self.assertEqual(self.create_item(self.client).status_code, 401)

    def test_create_with_photo_stores_jpeg(self):
        self.register(self.client)
        res = self.create_item(self.client, photo=True)
        self.assertEqual(res.status_code, 201)
        url = res.get_json()["item"]["image_url"]
        self.assertTrue(url.endswith(".jpg"))
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_validation_errors(self):
        self.register(self.client)
        future = (date.today() + timedelta(days=2)).isoformat()
        res = self.create_item(self.client, title="x", category="Weapons", description="short",
                               event_date=future, phone="12")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(set(res.get_json()["errors"]),
                         {"title", "category", "description", "event_date", "phone"})

    def test_fake_image_is_rejected(self):
        self.register(self.client)
        data = self.item_form()
        data["photo"] = (io.BytesIO(b"<?php echo 1; ?>"), "shell.jpg")
        res = self.client.post("/api/items", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 422)
        self.assertIn("photo", res.get_json()["errors"])
        data["photo"] = (png_bytes(), "photo.gif")
        res = self.client.post("/api/items", data=data, content_type="multipart/form-data")
        self.assertIn("photo", res.get_json()["errors"])

    def test_only_owner_can_edit_or_delete(self):
        self.register(self.client)
        item_id = self.create_item(self.client).get_json()["item"]["id"]
        other = self.new_client()
        self.register(other, name="Rohan", email="rohan@example.com")
        res = other.put(f"/api/items/{item_id}", data=self.item_form(),
                        content_type="multipart/form-data")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(other.delete(f"/api/items/{item_id}").status_code, 403)

    def test_edit_and_delete_remove_photo_files(self):
        self.register(self.client)
        item = self.create_item(self.client, photo=True).get_json()["item"]
        folder = self.app.config["UPLOAD_FOLDER"]
        self.assertEqual(len(os.listdir(folder)), 1)
        res = self.client.put(f"/api/items/{item['id']}",
                              data=self.item_form(title="Green bottle", remove_photo="1"),
                              content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["item"]["title"], "Green bottle")
        self.assertIsNone(res.get_json()["item"]["image_url"])
        self.assertEqual(os.listdir(folder), [])
        self.assertEqual(self.client.delete(f"/api/items/{item['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/items/{item['id']}").status_code, 404)


class BrowseTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.register(self.client)
        self.create_item(self.client, title="Black backpack", category="Bags & Clothing",
                         type="lost", location="Food Court")
        self.create_item(self.client, title="Casio calculator", category="Electronics",
                         type="found", location="Academic Block 1")
        self.create_item(self.client, title="Hostel room key", category="Keys",
                         type="found", location="Hostel Block")

    def titles(self, query=""):
        return [i["title"] for i in self.new_client().get("/api/items" + query).get_json()["items"]]

    def test_public_listing_and_filters(self):
        self.assertEqual(len(self.titles()), 3)
        self.assertEqual(self.titles("?type=found"), ["Hostel room key", "Casio calculator"])
        self.assertEqual(self.titles("?category=Keys"), ["Hostel room key"])
        self.assertEqual(self.titles("?q=backpack"), ["Black backpack"])
        self.assertEqual(self.titles("?q=food"), ["Black backpack"])     # matches location
        self.assertEqual(self.titles("?sort=oldest")[0], "Black backpack")

    def test_search_treats_wildcards_literally(self):
        self.assertEqual(self.titles("?q=%25"), [])

    def test_pagination(self):
        page = self.new_client().get("/api/items?per_page=2&page=2").get_json()
        self.assertEqual((page["total"], page["pages"], len(page["items"])), (3, 2, 1))

    def test_contact_is_hidden_from_public(self):
        item = self.new_client().get("/api/items/1").get_json()["item"]
        self.assertNotIn("contact", item)
        self.assertNotIn("reporter_email", item)


class ClaimTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.client
        self.register(self.owner)
        self.item_id = self.create_item(self.owner, type="found", phone="9876543210").get_json()["item"]["id"]
        self.claimer = self.new_client()
        self.register(self.claimer, name="Rohan", email="rohan@example.com")
        self.third = self.new_client()
        self.register(self.third, name="Meera", email="meera@example.com")

    def claim(self, client, message="It has my initials scratched under the lid."):
        return client.post(f"/api/items/{self.item_id}/claims", json={"message": message})

    def test_claim_rules(self):
        self.assertEqual(self.new_client().post(f"/api/items/{self.item_id}/claims",
                                                json={"message": "x" * 12}).status_code, 401)
        self.assertEqual(self.claim(self.owner).status_code, 403)          # own item
        self.assertEqual(self.claim(self.claimer, "too short").status_code, 422)
        self.assertEqual(self.claim(self.claimer).status_code, 201)
        self.assertEqual(self.claim(self.claimer).status_code, 409)        # duplicate

    def test_approval_flow_reveals_contact_and_resolves_item(self):
        self.claim(self.claimer)
        self.claim(self.third)
        received = self.owner.get("/api/me/claims/received").get_json()["claims"]
        self.assertEqual(len(received), 2)
        self.assertNotIn("claimant_email", received[0])                    # hidden until approved

        detail = self.claimer.get(f"/api/items/{self.item_id}").get_json()["item"]
        self.assertNotIn("contact", detail)                                # still private

        claim_id = [c["id"] for c in received if c["claimant_name"] == "Rohan"][0]
        self.assertEqual(self.third.post(f"/api/claims/{claim_id}/decision",
                                         json={"decision": "approved"}).status_code, 403)
        res = self.owner.post(f"/api/claims/{claim_id}/decision", json={"decision": "approved"})
        self.assertEqual(res.status_code, 200)

        detail = self.claimer.get(f"/api/items/{self.item_id}").get_json()["item"]
        self.assertEqual(detail["status"], "resolved")
        self.assertEqual(detail["contact"]["email"], "asha@example.com")
        self.assertEqual(detail["contact"]["phone"], "9876543210")
        mine = self.claimer.get("/api/me/claims").get_json()["claims"][0]
        self.assertEqual(mine["status"], "approved")
        self.assertIn("contact", mine)

        other_detail = self.third.get(f"/api/items/{self.item_id}").get_json()["item"]
        self.assertNotIn("contact", other_detail)
        self.assertEqual(other_detail["my_claim"]["status"], "rejected")   # auto-rejected
        self.assertEqual(self.owner.post(f"/api/claims/{claim_id}/decision",
                                         json={"decision": "rejected"}).status_code, 409)
        self.assertEqual(self.claim(self.third).status_code, 409)          # item resolved

    def test_reject_keeps_item_open(self):
        self.claim(self.claimer)
        claim_id = self.owner.get("/api/me/claims/received").get_json()["claims"][0]["id"]
        self.owner.post(f"/api/claims/{claim_id}/decision", json={"decision": "rejected"})
        self.assertEqual(self.owner.get(f"/api/items/{self.item_id}").get_json()["item"]["status"], "open")

    def test_resolve_and_stats(self):
        self.claim(self.claimer)
        stats = self.owner.get("/api/me/stats").get_json()
        self.assertEqual((stats["reports"], stats["open"], stats["pending_received"]), (1, 1, 1))
        self.assertEqual(self.claimer.post(f"/api/items/{self.item_id}/resolve").status_code, 403)
        self.assertEqual(self.owner.post(f"/api/items/{self.item_id}/resolve").status_code, 200)
        stats = self.owner.get("/api/me/stats").get_json()
        self.assertEqual((stats["open"], stats["resolved"], stats["pending_received"]), (0, 1, 0))
        public = self.new_client().get("/api/stats").get_json()
        self.assertEqual((public["resolved"], public["members"]), (1, 3))

    def test_deleting_item_removes_claims(self):
        self.claim(self.claimer)
        self.owner.delete(f"/api/items/{self.item_id}")
        self.assertEqual(self.claimer.get("/api/me/claims").get_json()["claims"], [])


if __name__ == "__main__":
    unittest.main()
