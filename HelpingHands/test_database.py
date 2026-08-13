"""
test_database.py
Standalone unittest suite for HelpingHands' database.py

Run with no Flask app running at all:
    python test_database.py

WHY THE chdir TRICK AT THE TOP:
database.py's get_db_connection() hardcodes a relative path,
"HelpingHands.db", and tables_db() is executed once automatically
at import time. That means simply `import database` would create/touch
a real "HelpingHands.db" file in whatever directory the test is run
from. To keep tests from ever touching your real dev database, we
create a throwaway temp directory and chdir into it BEFORE importing
database, so the very first tables_db() call (and every call after)
operates on an isolated file. Nothing here modifies database.py.

Place this file in the same folder as database.py.
"""

import os
import sys
import shutil
import sqlite3
import tempfile
import unittest

_ORIGINAL_CWD = os.getcwd()
_TEST_DIR = tempfile.mkdtemp(prefix="helpinghands_test_")


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.chdir(_TEST_DIR)
import database

DB_FILENAME = "HelpingHands.db"


def reset_db():
    """Delete the throwaway db file (if any) and rebuild fresh tables.
    Called before every test so tests never leak state into each other."""
    if os.path.exists(DB_FILENAME):
        os.remove(DB_FILENAME)
    database.tables_db()


def insert_support_with_amount(request_id, donor_id, amount, message="pledge"):
    """create_support() doesn't currently accept an `amount` argument,
    so pledges with a dollar amount are inserted directly here to
    exercise the `amount` column and get_total_pledged(). This also
    documents a gap: create_support() may need an `amount` param later."""
    conn = database.get_db_connection()
    try:
        conn.execute(
            "INSERT INTO supports (request_id, donor_id, message, amount, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (request_id, donor_id, message, amount, database.current_time()),
        )
        conn.commit()
    finally:
        conn.close()


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        reset_db()



# Users

class TestUsers(BaseTestCase):
    def test_email_exists_false_when_no_user(self):
        self.assertFalse(database.email_exists("nobody@example.com"))

    def test_create_user_returns_id(self):
        user_id = database.create_user("Sarah", "sarah@example.com", "hash123", "0100000000", "requester")
        self.assertIsInstance(user_id, int)
        self.assertTrue(database.email_exists("sarah@example.com"))

    def test_create_user_duplicate_email_returns_none(self):
        database.create_user("Sarah", "sarah@example.com", "hash123", "0100000000", "requester")
        second = database.create_user("Sarah Clone", "sarah@example.com", "hash999", "0100000001", "donor")
        self.assertIsNone(second)

    def test_get_user_by_email(self):
        database.create_user("Omar", "omar@example.com", "hash", "0100000002", "donor")
        user = database.get_user_by_email("omar@example.com")
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Omar")

    def test_get_user_by_email_nonexistent_returns_none(self):
        self.assertIsNone(database.get_user_by_email("ghost@example.com"))

    def test_get_user_by_id(self):
        user_id = database.create_user("Omar", "omar@example.com", "hash", "0100000002", "donor")
        user = database.get_user_by_id(user_id)
        self.assertEqual(user["email"], "omar@example.com")

    def test_get_user_by_id_nonexistent_returns_none(self):
        self.assertIsNone(database.get_user_by_id(999999))

    def test_get_all_users_excludes_password(self):
        database.create_user("Sarah", "sarah@example.com", "hash123", "0100000000", "requester")
        database.create_user("Omar", "omar@example.com", "hash456", "0100000002", "donor")
        users = database.get_all_users()
        self.assertEqual(len(users), 2)
        for u in users:
            self.assertNotIn("password_hash", u.keys())



# Requests

class TestRequests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner_id = database.create_user("Sarah", "sarah@example.com", "hash", "010", "requester")
        self.other_id = database.create_user("Omar", "omar@example.com", "hash", "011", "donor")

    def _make_request(self, amount_needed=500, category="education"):
        return database.create_request(self.owner_id, "Tuition help", "desc", amount_needed, category)

    def test_create_request_starts_pending(self):
        request_id = self._make_request()
        request = database.get_request_by_id(request_id)
        self.assertEqual(request["status"], "pending")
        self.assertEqual(request["user_id"], self.owner_id)

    def test_get_request_by_id_nonexistent_returns_none(self):
        self.assertIsNone(database.get_request_by_id(999999))

    def test_get_request_by_user_id(self):
        self._make_request()
        self._make_request(amount_needed=200)
        rows = database.get_request_by_user_id(self.owner_id)
        self.assertEqual(len(rows), 2)

    def test_pending_request_hidden_from_default_browse(self):
        self._make_request()
        approved_only = database.get_all_requests()  # default status="approved"
        self.assertEqual(len(approved_only), 0)

    def test_request_visible_after_approval(self):
        request_id = self._make_request()
        database.update_request_status(request_id, "approved")
        approved_only = database.get_all_requests()
        self.assertEqual(len(approved_only), 1)
        self.assertEqual(approved_only[0]["id"], request_id)

    def test_get_all_requests_status_none_returns_everything(self):
        self._make_request()
        all_statuses = database.get_all_requests(status=None)
        self.assertEqual(len(all_statuses), 1)

    def test_get_all_requests_category_filter(self):
        self._make_request(category="education")
        database.update_request_status(1, "approved")
        matches = database.get_all_requests(status="approved", category="education")
        no_matches = database.get_all_requests(status="approved", category="medical")
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(no_matches), 0)

    def test_search_requests_by_keyword(self):
        self._make_request()
        database.update_request_status(1, "approved")
        found = database.search_requests("tuition")
        not_found = database.search_requests("bicycle")
        self.assertEqual(len(found), 1)
        self.assertEqual(len(not_found), 0)

    def test_update_request_rejects_non_owner(self):
        request_id = self._make_request()
        result = database.update_request(request_id, self.other_id, title="Hacked title")
        self.assertFalse(result)
        self.assertEqual(database.get_request_by_id(request_id)["title"], "Tuition help")

    def test_update_request_succeeds_for_owner(self):
        request_id = self._make_request()
        result = database.update_request(request_id, self.owner_id, title="New title")
        self.assertTrue(result)
        self.assertEqual(database.get_request_by_id(request_id)["title"], "New title")

    def test_update_request_admin_override_bypasses_ownership(self):
        request_id = self._make_request()
        result = database.update_request(
            request_id, self.other_id, admin_override=True, title="Admin edited"
        )
        self.assertTrue(result)
        self.assertEqual(database.get_request_by_id(request_id)["title"], "Admin edited")

    def test_update_request_rejects_invalid_amount(self):
        request_id = self._make_request()
        result = database.update_request(request_id, self.owner_id, amount_needed=0)
        self.assertFalse(result)

    def test_update_request_ignores_disallowed_fields(self):
        request_id = self._make_request()
        # "status" isn't in allowed_fields, so it should be silently dropped.
        database.update_request(request_id, self.owner_id, status="approved")
        request = database.get_request_by_id(request_id)
        self.assertEqual(request["status"], "pending")

    def test_update_request_cannot_smuggle_user_id_via_fields(self):
        # user_id is a named positional parameter, so passing it as a
        # kwarg collides at the Python call level before it ever reaches
        # the allowed_fields whitelist -- it can never leak through **fields.
        request_id = self._make_request()
        with self.assertRaises(TypeError):
            database.update_request(request_id, self.owner_id, user_id=self.other_id)

    def test_delete_request_rejects_non_owner(self):
        request_id = self._make_request()
        result = database.delete_request(request_id, self.other_id)
        self.assertFalse(result)
        self.assertIsNotNone(database.get_request_by_id(request_id))

    def test_delete_request_succeeds_for_owner(self):
        request_id = self._make_request()
        result = database.delete_request(request_id, self.owner_id)
        self.assertTrue(result)
        self.assertIsNone(database.get_request_by_id(request_id))

    def test_delete_request_admin_override_bypasses_ownership(self):
        request_id = self._make_request()
        result = database.delete_request(request_id, self.other_id, admin_override=True)
        self.assertTrue(result)
        self.assertIsNone(database.get_request_by_id(request_id))

    def test_delete_request_cascades_to_supports(self):
        request_id = self._make_request()
        database.update_request_status(request_id, "approved")
        database.create_support(request_id, self.other_id, "I can help!")
        database.delete_request(request_id, self.owner_id)
        remaining_supports = database.get_supports_for_request(request_id)
        self.assertEqual(len(remaining_supports), 0)

    def test_update_request_status_valid(self):
        request_id = self._make_request()
        self.assertTrue(database.update_request_status(request_id, "approved"))
        self.assertEqual(database.get_request_by_id(request_id)["status"], "approved")

    def test_update_request_status_invalid_value_rejected(self):
        request_id = self._make_request()
        result = database.update_request_status(request_id, "banana")
        self.assertFalse(result)
        self.assertEqual(database.get_request_by_id(request_id)["status"], "pending")



# Supports

class TestSupports(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner_id = database.create_user("Sarah", "sarah@example.com", "hash", "010", "requester")
        self.donor_id = database.create_user("Omar", "omar@example.com", "hash", "011", "donor")
        self.request_id = database.create_request(self.owner_id, "Tuition help", "desc", 500, "education")
        database.update_request_status(self.request_id, "approved")

    def test_has_donor_supported_false_initially(self):
        self.assertFalse(database.has_donor_supported(self.request_id, self.donor_id))

    def test_create_support_returns_id(self):
        support_id = database.create_support(self.request_id, self.donor_id, "Happy to help")
        self.assertIsInstance(support_id, int)
        self.assertTrue(database.has_donor_supported(self.request_id, self.donor_id))

    def test_create_support_duplicate_returns_none(self):
        database.create_support(self.request_id, self.donor_id, "Happy to help")
        second = database.create_support(self.request_id, self.donor_id, "Again!")
        self.assertIsNone(second)

    def test_get_supports_for_request_includes_donor_info(self):
        database.create_support(self.request_id, self.donor_id, "Happy to help")
        rows = database.get_supports_for_request(self.request_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["donor_name"], "Omar")
        self.assertEqual(rows[0]["donor_email"], "omar@example.com")

    def test_get_supports_by_donor_includes_request_info(self):
        database.create_support(self.request_id, self.donor_id, "Happy to help")
        rows = database.get_supports_by_donor(self.donor_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["request_title"], "Tuition help")
        self.assertEqual(rows[0]["request_status"], "approved")

    def test_get_total_pledged_zero_when_no_supports(self):
        self.assertEqual(database.get_total_pledged(self.request_id), 0)

    def test_get_total_pledged_zero_when_supports_have_no_amount(self):
        database.create_support(self.request_id, self.donor_id, "Happy to help, no pledge yet")
        self.assertEqual(database.get_total_pledged(self.request_id), 0)

    def test_get_total_pledged_sums_amounts(self):
        second_donor_id = database.create_user("Layla", "layla@example.com", "hash", "012", "donor")
        insert_support_with_amount(self.request_id, self.donor_id, 150.0)
        insert_support_with_amount(self.request_id, second_donor_id, 75.5)
        self.assertAlmostEqual(database.get_total_pledged(self.request_id), 225.5)

    def test_get_total_pledged_ignores_other_requests(self):
        other_request_id = database.create_request(self.owner_id, "Groceries", "desc", 100, "general")
        insert_support_with_amount(self.request_id, self.donor_id, 150.0)
        self.assertEqual(database.get_total_pledged(other_request_id), 0)

    def test_get_total_pledged_nonexistent_request_returns_zero(self):
        self.assertEqual(database.get_total_pledged(999999), 0)


# Admin

class TestAdmin(BaseTestCase):
    def test_get_admin_stats_counts(self):
        owner_id = database.create_user("Sarah", "sarah@example.com", "hash", "010", "requester")
        database.create_user("Omar", "omar@example.com", "hash", "011", "donor")
        database.create_user("Admin", "admin@example.com", "hash", "012", "admin")

        r1 = database.create_request(owner_id, "Req 1", "desc", 100, "general")
        r2 = database.create_request(owner_id, "Req 2", "desc", 200, "general")
        database.create_request(owner_id, "Req 3", "desc", 300, "general")

        database.update_request_status(r1, "approved")
        database.update_request_status(r2, "rejected")

        stats = database.get_admin_stats()
        self.assertEqual(stats["total_users"], 3)
        self.assertEqual(stats["total_requests"], 3)
        self.assertEqual(stats["approved_requests"], 1)
        self.assertEqual(stats["rejected_requests"], 1)
        self.assertEqual(stats["pending_requests"], 1)



# Schema / migration

class TestSchemaMigration(BaseTestCase):
    def test_supports_table_has_amount_column(self):
        conn = database.get_db_connection()
        try:
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(supports)").fetchall()]
        finally:
            conn.close()
        self.assertIn("amount", columns)

    def test_amount_check_constraint_rejects_zero_or_negative(self):
        owner_id = database.create_user("Sarah", "sarah@example.com", "hash", "010", "requester")
        donor_id = database.create_user("Omar", "omar@example.com", "hash", "011", "donor")
        request_id = database.create_request(owner_id, "Req", "desc", 100, "general")

        with self.assertRaises(sqlite3.IntegrityError):
            insert_support_with_amount(request_id, donor_id, 0)

    def test_tables_db_is_idempotent_and_keeps_data(self):
        owner_id = database.create_user("Sarah", "sarah@example.com", "hash", "010", "requester")
        database.tables_db()
        self.assertIsNotNone(database.get_user_by_id(owner_id))



# Cleanup: remove the temp directory and restore the working directory

def _cleanup():
    os.chdir(_ORIGINAL_CWD)
    shutil.rmtree(_TEST_DIR, ignore_errors=True)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2, exit=False)
    finally:
        _cleanup()
