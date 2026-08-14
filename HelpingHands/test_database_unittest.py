"""
test_database_unittest.py -- Helping Hands

unittest-based test suite for database.py, covering Users, Requests,
Supports, and Admin functions.

DESIGN NOTES

- get_db_connection() hardcodes "HelpingHands.db", so this runs against
  your real database file -- there's no way to point it at a separate
  test DB without changing database.py. To stay safe, every row this
  suite creates is tagged with "_TEST_" in its email, and tearDown()
  deletes all "_TEST_" users after EVERY test (not just at the end).
  Requests and supports cascade away automatically (ON DELETE CASCADE),
  so a single DELETE FROM users is enough to clean up everything a test
  created, even after a test fails partway through.

- Each test is fully independent: it creates whatever users/requests it
  needs itself via the make_user()/make_approved_request() helpers, and
  cleans up after itself. Nothing relies on test execution order.

- get_admin_stats() counts every row in the real database, not just this
  suite's rows, so admin tests only ever assert deltas (before/after a
  specific action), never exact totals.

Run:
    python -m unittest test_database_unittest.py -v
    (or just: python test_database_unittest.py)
"""

import unittest
import uuid

import database as db


def cleanup_test_data():
    conn = db.get_db_connection()
    conn.execute("DELETE FROM users WHERE email LIKE '%_TEST_%'")
    conn.commit()
    conn.close()


def unique_email(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}_TEST_@example.com"


class BaseDatabaseTestCase(unittest.TestCase):
    """Shared setup/teardown and helper methods for all test classes below."""

    @classmethod
    def setUpClass(cls):
        db.tables_db()
        cleanup_test_data()  # in case a previous run crashed mid-way

    def tearDown(self):
        cleanup_test_data()  # cascades away any requests/supports this test created too

    def make_user(self, role="donor"):
        """Creates a uniquely-tagged test user. Returns (user_id, email)."""
        email = unique_email(role)
        user_id = db.create_user(f"{role.title()} Test", email, "hashed_pw", "0100000000", role)
        self.assertIsInstance(user_id, int, "helper failed to create a user")
        return user_id, email

    def make_approved_request(self, owner_id, amount_needed=500, category="general"):
        """Creates and approves a test request. Returns request_id."""
        request_id = db.create_request(
            owner_id, f"Request TEST {uuid.uuid4().hex[:6]}", "desc", amount_needed, category
        )
        self.assertIsInstance(request_id, int, "helper failed to create a request")
        db.update_request_status(request_id, "approved")
        return request_id


# ---------------------------------------------------------------------------
#                                   USERS
# ---------------------------------------------------------------------------

class TestUsers(BaseDatabaseTestCase):

    def test_create_user_returns_id(self):
        user_id, _ = self.make_user("requester")
        self.assertIsInstance(user_id, int)

    def test_duplicate_email_returns_none(self):
        _, email = self.make_user("requester")
        dup = db.create_user("Someone Else", email, "hashed", "0111111111", "donor")
        self.assertIsNone(dup)

        conn = db.get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,)).fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "duplicate attempt should not create a second row")

    def test_email_exists(self):
        self.assertFalse(db.email_exists(unique_email("ghost")))
        _, email = self.make_user()
        self.assertTrue(db.email_exists(email))

    def test_get_user_by_email(self):
        user_id, email = self.make_user("admin")
        user = db.get_user_by_email(email)
        self.assertIsNotNone(user)
        self.assertEqual(user["id"], user_id)
        self.assertEqual(user["role"], "admin")

    def test_get_user_by_email_missing(self):
        self.assertIsNone(db.get_user_by_email(unique_email("nobody")))

    def test_get_user_by_id(self):
        user_id, email = self.make_user()
        user = db.get_user_by_id(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], email)

    def test_get_user_by_id_missing(self):
        self.assertIsNone(db.get_user_by_id(999999999))

    def test_invalid_role_rejected(self):
        email = unique_email("badrole")
        with self.assertRaises(Exception):
            db.create_user("Bad Role", email, "hashed", "0100000000", "superadmin")
        # confirm no row leaked in despite the exception
        self.assertFalse(db.email_exists(email))

    def test_get_all_users_excludes_password(self):
        self.make_user()
        all_users = db.get_all_users()
        self.assertIsInstance(all_users, list)
        self.assertGreater(len(all_users), 0)
        self.assertNotIn("password_hash", all_users[0].keys())


# ---------------------------------------------------------------------------
#                               REQUESTS
# ---------------------------------------------------------------------------

class TestRequests(BaseDatabaseTestCase):

    def test_create_request_returns_id(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Help TEST", "desc", 1000, "housing")
        self.assertIsInstance(request_id, int)

    def test_create_request_rejects_bad_amount(self):
        owner_id, _ = self.make_user("requester")
        self.assertIsNone(db.create_request(owner_id, "Zero TEST", "desc", 0, "general"))
        self.assertIsNone(db.create_request(owner_id, "Negative TEST", "desc", -50, "general"))

    def test_create_request_defaults(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Defaults TEST", "desc", 200)
        req = db.get_request_by_id(request_id)
        self.assertEqual(req["category"], "general")
        self.assertIsNone(req["image_url"])
        self.assertEqual(req["status"], "pending")

    def test_create_request_with_image_url(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Photo TEST", "desc", 300, "general", "/static/x.jpg")
        req = db.get_request_by_id(request_id)
        self.assertEqual(req["image_url"], "/static/x.jpg")

    def test_get_request_by_id_missing(self):
        self.assertIsNone(db.get_request_by_id(999999999))

    def test_get_request_by_user_id(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Mine TEST", "desc", 400, "general")
        reqs = db.get_request_by_user_id(owner_id)
        self.assertIn(request_id, [r["id"] for r in reqs])

    def test_default_view_hides_pending(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Pending TEST", "desc", 400, "general")
        ids = [r["id"] for r in db.get_all_requests()]
        self.assertNotIn(request_id, ids)

    def test_approve_reveals_request(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "ToApprove TEST", "desc", 400, "general")
        self.assertTrue(db.update_request_status(request_id, "approved"))
        ids = [r["id"] for r in db.get_all_requests()]
        self.assertIn(request_id, ids)

    def test_update_request_status_rejects_bad_status(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Status TEST", "desc", 400, "general")
        self.assertFalse(db.update_request_status(request_id, "not_a_status"))

    def test_update_request_status_missing_request(self):
        self.assertFalse(db.update_request_status(999999999, "approved"))

    def test_category_filter(self):
        owner_id, _ = self.make_user("requester")
        med_id = self.make_approved_request(owner_id, 800, "medical")
        matching = [r["id"] for r in db.get_all_requests(status="approved", category="medical")]
        self.assertIn(med_id, matching)
        non_matching = [r["id"] for r in db.get_all_requests(status="approved", category="housing")]
        self.assertNotIn(med_id, non_matching)

    def test_search_requests(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Findable Keyword TEST", "desc", 400, "general")
        db.update_request_status(request_id, "approved")
        matching = [r["id"] for r in db.search_requests("Findable Keyword")]
        self.assertIn(request_id, matching)
        self.assertEqual(db.search_requests("zzz_no_such_keyword_zzz"), [])

    def test_update_request_owner_succeeds(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Editable TEST", "desc", 400, "general")
        self.assertTrue(db.update_request(request_id, owner_id, title="Edited TEST"))
        self.assertEqual(db.get_request_by_id(request_id)["title"], "Edited TEST")

    def test_update_request_blocks_non_owner(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Protected TEST", "desc", 400, "general")
        self.assertFalse(db.update_request(request_id, 999999999, title="Hijacked"))

    def test_update_request_rejects_bad_amount(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "AmountCheck TEST", "desc", 400, "general")
        self.assertFalse(db.update_request(request_id, owner_id, amount_needed=-10))

    def test_update_request_no_allowed_fields(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "NoFields TEST", "desc", 400, "general")
        self.assertFalse(db.update_request(request_id, owner_id, not_a_field="x"))

    def test_update_request_admin_override(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "AdminEdit TEST", "desc", 400, "general")
        ok = db.update_request(request_id, 999999999, admin_override=True, description="Edited by admin TEST")
        self.assertTrue(ok)
        self.assertEqual(db.get_request_by_id(request_id)["description"], "Edited by admin TEST")

    def test_delete_request_blocks_non_owner(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "NoDelete TEST", "desc", 400, "general")
        self.assertFalse(db.delete_request(request_id, 999999999))
        self.assertIsNotNone(db.get_request_by_id(request_id))

    def test_delete_request_owner_succeeds(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Deletable TEST", "desc", 400, "general")
        self.assertTrue(db.delete_request(request_id, owner_id))
        self.assertIsNone(db.get_request_by_id(request_id))

    def test_delete_request_admin_override(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "AdminDelete TEST", "desc", 400, "general")
        self.assertFalse(db.delete_request(request_id, 999999999))  # blocked without override
        self.assertTrue(db.delete_request(request_id, 999999999, admin_override=True))
        self.assertIsNone(db.get_request_by_id(request_id))


# ---------------------------------------------------------------------------
#                               SUPPORTS
# ---------------------------------------------------------------------------

class TestSupports(BaseDatabaseTestCase):

    def test_has_donor_supported_false_initially(self):
        owner_id, _ = self.make_user("requester")
        donor_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id)
        self.assertFalse(db.has_donor_supported(request_id, donor_id))

    def test_create_support_message_only(self):
        owner_id, _ = self.make_user("requester")
        donor_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id)
        support_id = db.create_support(request_id, donor_id, "Happy to help!")
        self.assertIsInstance(support_id, int)
        supporters = db.get_supports_for_request(request_id)
        self.assertEqual(len(supporters), 1)
        self.assertIsNone(supporters[0]["amount"])

    def test_create_support_blocks_duplicate(self):
        owner_id, _ = self.make_user("requester")
        donor_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id)
        db.create_support(request_id, donor_id, "First")
        dup = db.create_support(request_id, donor_id, "Second")
        self.assertIsNone(dup)

    def test_create_support_with_amount(self):
        owner_id, _ = self.make_user("requester")
        donor_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id, amount_needed=1000)
        support_id = db.create_support(request_id, donor_id, "Here's my pledge", amount=250)
        self.assertIsInstance(support_id, int)
        self.assertEqual(db.get_total_pledged(request_id), 250)

    def test_create_support_rejects_non_positive_amount(self):
        owner_id, _ = self.make_user("requester")
        donor_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id)
        self.assertIsNone(db.create_support(request_id, donor_id, "Bad", amount=-10))
        self.assertIsNone(db.create_support(request_id, donor_id, "Bad", amount=0))

    def test_get_total_pledged_sums_multiple_donors(self):
        owner_id, _ = self.make_user("requester")
        donor1_id, _ = self.make_user("donor")
        donor2_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id, amount_needed=1000)
        db.create_support(request_id, donor1_id, "Part 1", amount=200)
        db.create_support(request_id, donor2_id, "Part 2", amount=300)
        self.assertEqual(db.get_total_pledged(request_id), 500)

    def test_get_supports_for_request_joins_donor_info(self):
        owner_id, _ = self.make_user("requester")
        donor_id, email = self.make_user("donor")
        request_id = self.make_approved_request(owner_id)
        db.create_support(request_id, donor_id, "hi", amount=50)
        supporters = db.get_supports_for_request(request_id)
        self.assertIn("donor_name", supporters[0])
        self.assertEqual(supporters[0]["donor_email"], email)

    def test_get_supports_by_donor_joins_request_info(self):
        owner_id, _ = self.make_user("requester")
        donor_id, _ = self.make_user("donor")
        request_id = self.make_approved_request(owner_id)
        db.create_support(request_id, donor_id, "hi", amount=50)
        history = db.get_supports_by_donor(donor_id)
        self.assertEqual(len(history), 1)
        self.assertIn("request_title", history[0])
        self.assertEqual(history[0]["request_status"], "approved")


# ---------------------------------------------------------------------------
#                                   ADMIN
# ---------------------------------------------------------------------------

class TestAdmin(BaseDatabaseTestCase):

    def test_get_admin_stats_delta_on_create(self):
        owner_id, _ = self.make_user("requester")
        before = db.get_admin_stats()
        db.create_request(owner_id, "Stats TEST", "desc", 250, "general")
        after = db.get_admin_stats()
        self.assertEqual(after["total_requests"], before["total_requests"] + 1)
        self.assertEqual(after["pending_requests"], before["pending_requests"] + 1)

    def test_get_admin_stats_delta_on_approve_reject(self):
        owner_id, _ = self.make_user("requester")
        request_id = db.create_request(owner_id, "Stats2 TEST", "desc", 250, "general")

        before = db.get_admin_stats()
        db.update_request_status(request_id, "approved")
        after_approve = db.get_admin_stats()
        self.assertEqual(after_approve["pending_requests"], before["pending_requests"] - 1)
        self.assertEqual(after_approve["approved_requests"], before["approved_requests"] + 1)

        db.update_request_status(request_id, "rejected")
        after_reject = db.get_admin_stats()
        self.assertEqual(after_reject["approved_requests"], after_approve["approved_requests"] - 1)
        self.assertEqual(after_reject["rejected_requests"], after_approve["rejected_requests"] + 1)

    def test_get_all_users_for_admin(self):
        self.make_user("donor")
        users = db.get_all_users()
        self.assertIsInstance(users, list)
        self.assertGreater(len(users), 0)




if __name__ == "__main__":
    unittest.main(verbosity=2)
