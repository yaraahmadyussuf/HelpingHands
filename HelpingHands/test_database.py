"""
test_database.py — Helping Hands

Standalone test script for database.py: Users, Requests, Supports, and
Admin functions.

Since get_db_connection() hardcodes "HelpingHands.db", this script does NOT
use a separate test database — it runs against the real file. Every test
row is tied to an email tagged "_TEST_". Cleanup only ever issues
"DELETE FROM users WHERE email LIKE '%_TEST_%'" — it never touches
requests/supports directly. That's deliberate: both tables have
ON DELETE CASCADE foreign keys back to users, so deleting the tagged test
users automatically cascades and removes every request and support they
created too. That only works if PRAGMA foreign_keys = ON for the deleting
connection, which get_db_connection() already sets.

Admin stats (get_admin_stats) count EVERY row in the real database, not
just test rows, so this script never asserts exact totals — only deltas
captured immediately before/after a specific action, which stay correct
regardless of how much real data already exists.

Run:
    python test_database.py
"""

import database as db
import gc

passed = 0
failed = 0

TEST_EMAIL_1 = "gehad_TEST_@example.com"
TEST_EMAIL_2 = "sara_TEST_@example.com"
TEST_DONOR_EMAIL = "mostafa_TEST_@example.com"


def check(label, condition):
    global passed, failed
    if condition:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failed += 1


def cleanup():
    """Removes any leftover test rows so re-runs start from a clean state."""
    conn = db.get_db_connection()
    conn.execute("DELETE FROM users WHERE email LIKE '%_TEST_%'")
    conn.commit()
    conn.close()


def test_tables_created():
    print("\n[SETUP]")
    db.tables_db()
    conn = db.get_db_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    table_names = [t["name"] for t in tables]
    check("users table exists", "users" in table_names)
    check("requests table exists", "requests" in table_names)
    check("supports table exists", "supports" in table_names)


def test_email_exists_before_creation():
    print("\n[EMAIL_EXISTS - before creation]")
    check("email_exists is False for unused test email",
          db.email_exists(TEST_EMAIL_1) is False)


def test_create_user():
    print("\n[CREATE_USER]")
    user_id = db.create_user("Gehad Test", TEST_EMAIL_1, "hashed_secret_123", "01012345678", "admin")
    check("create_user returns an int id", isinstance(user_id, int))
    return user_id


def test_duplicate_email(user_id):
    print("\n[DUPLICATE EMAIL]")
    dup_id = db.create_user("Impersonator", TEST_EMAIL_1, "hashed_secret_456", "01112345678", "donor")
    check("create_user returns None for duplicate email", dup_id is None)

    # confirm the duplicate attempt did NOT overwrite or create a second row
    conn = db.get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE email = ?", (TEST_EMAIL_1,)
    ).fetchone()[0]
    conn.close()
    check("still exactly one row for that email after duplicate attempt", count == 1)


def test_email_exists_after_creation():
    print("\n[EMAIL_EXISTS - after creation]")
    check("email_exists is True after create_user",
          db.email_exists(TEST_EMAIL_1) is True)


def test_get_user_by_email(user_id):
    print("\n[GET_USER_BY_EMAIL]")
    user = db.get_user_by_email(TEST_EMAIL_1)
    check("get_user_by_email finds the user", user is not None)
    check("get_user_by_email returns correct name", user["name"] == "Gehad Test")
    check("get_user_by_email returns correct role", user["role"] == "admin")
    check("get_user_by_email returns correct id", user["id"] == user_id)

    missing = db.get_user_by_email("does_not_exist_TEST_@nowhere.com")
    check("get_user_by_email returns None for unknown email", missing is None)


def test_get_user_by_id(user_id):
    print("\n[GET_USER_BY_ID]")
    user = db.get_user_by_id(user_id)
    check("get_user_by_id finds the user", user is not None)
    check("get_user_by_id returns correct email", user["email"] == TEST_EMAIL_1)

    missing = db.get_user_by_id(9999999)
    check("get_user_by_id returns None for unknown id", missing is None)


def test_role_constraint():
    print("\n[ROLE CONSTRAINT]")
    error_type = None
    try:
        db.create_user("Bad Role", TEST_EMAIL_2, "hashed_xyz", "0100000000", "superadmin")
    except Exception as e:
        error_type = type(e).__name__
    # Note: while 'e' stays in scope, its traceback keeps create_user's
    # local `conn` alive (it never reached conn.close()), so the lock
    # isn't released until 'e' goes out of scope. Force that now.
    gc.collect()
    check(f"invalid role is rejected by CHECK constraint ({error_type})", error_type is not None)


def test_get_all_users(user_id):
    print("\n[GET_ALL_USERS]")
    all_users = db.get_all_users()
    check("get_all_users returns a list", isinstance(all_users, list))

    match = [u for u in all_users if u["id"] == user_id]
    check("created test user appears in get_all_users", len(match) == 1)

    if all_users:
        keys = all_users[0].keys()
        check("get_all_users does NOT expose password_hash", "password_hash" not in keys)


def test_create_request(user_id):
    print("\n[CREATE_REQUEST]")
    request_id = db.create_request(user_id, "Help with rent TEST", "Lost my job, need rent support.", 1500, "housing")
    check("create_request returns an int id", isinstance(request_id, int))
    return request_id


def test_get_request_by_id(request_id, user_id):
    print("\n[GET_REQUEST_BY_ID]")
    req = db.get_request_by_id(request_id)
    check("get_request_by_id finds the request", req is not None)
    check("status defaults to 'pending'", req["status"] == "pending")
    check("category stored correctly", req["category"] == "housing")
    check("user_id matches owner", req["user_id"] == user_id)

    missing = db.get_request_by_id(999999999)
    check("get_request_by_id returns None for missing id", missing is None)


def test_create_request_default_category(user_id):
    print("\n[CREATE_REQUEST - default category]")
    rid = db.create_request(user_id, "Generic help needed TEST", "desc", 200)
    req = db.get_request_by_id(rid)
    check("category defaults to 'general' when omitted", req["category"] == "general")
    return rid


def test_get_request_by_user_id(user_id, request_id):
    print("\n[GET_REQUEST_BY_USER_ID]")
    reqs = db.get_request_by_user_id(user_id)
    check("get_request_by_user_id returns a list", isinstance(reqs, list))
    ids = [r["id"] for r in reqs]
    check("created request appears in this user's requests", request_id in ids)


def test_get_all_requests_default_hides_pending(request_id):
    print("\n[GET_ALL_REQUESTS - default status]")
    approved_only = db.get_all_requests()
    ids = [r["id"] for r in approved_only]
    check("pending request is hidden from the default (approved) view", request_id not in ids)


def test_approve_and_reveal(request_id):
    print("\n[UPDATE_REQUEST_STATUS]")
    ok = db.update_request_status(request_id, "approved")
    check("update_request_status approves successfully", ok is True)

    approved_only = db.get_all_requests()
    ids = [r["id"] for r in approved_only]
    check("approved request is now visible in the default view", request_id in ids)

    bad = db.update_request_status(request_id, "not_a_real_status")
    check("update_request_status rejects an invalid status string", bad is False)

    missing = db.update_request_status(9999999, "approved")
    check("update_request_status returns False for a nonexistent request", missing is False)


def test_get_all_requests_category_filter(user_id):
    print("\n[GET_ALL_REQUESTS - category filter]")
    med_id = db.create_request(user_id, "Medical bills TEST", "desc", 800, "medical")
    db.update_request_status(med_id, "approved")

    medical_results = db.get_all_requests(status="approved", category="medical")
    ids = [r["id"] for r in medical_results]
    check("category filter returns the matching medical request", med_id in ids)

    housing_results = db.get_all_requests(status="approved", category="housing")
    ids2 = [r["id"] for r in housing_results]
    check("category filter excludes a non-matching category", med_id not in ids2)


def test_search_requests(request_id):
    print("\n[SEARCH_REQUESTS]")
    results = db.search_requests("rent TEST")
    ids = [r["id"] for r in results]
    check("search_requests matches a title keyword", request_id in ids)

    none_results = db.search_requests("zzz_no_such_keyword_zzz")
    check("search_requests returns an empty list for no match", len(none_results) == 0)


def test_update_request(request_id, owner_id):
    print("\n[UPDATE_REQUEST]")
    ok = db.update_request(request_id, owner_id, title="Help with rent - urgent TEST")
    check("update_request succeeds for the owner", ok is True)
    updated = db.get_request_by_id(request_id)
    check("title was actually changed", updated["title"] == "Help with rent - urgent TEST")

    blocked = db.update_request(request_id, 9999999, title="Hijacked title")
    check("update_request is blocked for a non-owner", blocked is False)

    bad_amount = db.update_request(request_id, owner_id, amount_needed=-50)
    check("update_request rejects a non-positive amount_needed", bad_amount is False)

    no_fields = db.update_request(request_id, owner_id, not_a_real_field="x")
    check("update_request returns False when no allowed fields are given", no_fields is False)


def test_delete_request(request_id, owner_id):
    print("\n[DELETE_REQUEST]")
    blocked = db.delete_request(request_id, 9999999)
    check("delete_request is blocked for a non-owner", blocked is False)
    still_there = db.get_request_by_id(request_id)
    check("request still exists after a blocked delete attempt", still_there is not None)

    ok = db.delete_request(request_id, owner_id)
    check("delete_request succeeds for the owner", ok is True)
    gone = db.get_request_by_id(request_id)
    check("request no longer exists after delete", gone is None)


def test_supports(owner_id):
    print("\n[SUPPORTS]")
    donor_id = db.create_user("Mostafa Test", TEST_DONOR_EMAIL, "hashed_donor_1", "0109999999", "donor")
    check("donor test user created", isinstance(donor_id, int))

    support_request_id = db.create_request(owner_id, "Support flow TEST request", "desc", 400, "general")
    db.update_request_status(support_request_id, "approved")

    check("has_donor_supported is False before supporting",
          db.has_donor_supported(support_request_id, donor_id) is False)

    support_id = db.create_support(support_request_id, donor_id, "Happy to help!")
    check("create_support returns an int id", isinstance(support_id, int))

    check("has_donor_supported is True after supporting",
          db.has_donor_supported(support_request_id, donor_id) is True)

    dup = db.create_support(support_request_id, donor_id, "Trying again")
    check("create_support blocks a duplicate support from the same donor", dup is None)

    supporters = db.get_supports_for_request(support_request_id)
    check("get_supports_for_request returns a non-empty list of dicts",
          isinstance(supporters, list) and len(supporters) == 1 and isinstance(supporters[0], dict))
    check("get_supports_for_request joins donor_name correctly", supporters[0]["donor_name"] == "Mostafa Test")
    check("get_supports_for_request joins donor_email correctly", supporters[0]["donor_email"] == TEST_DONOR_EMAIL)

    history = db.get_supports_by_donor(donor_id)
    check("get_supports_by_donor returns a non-empty list of dicts",
          isinstance(history, list) and len(history) == 1 and isinstance(history[0], dict))
    check("get_supports_by_donor joins request_title correctly",
          history[0]["request_title"] == "Support flow TEST request")
    check("get_supports_by_donor joins request_status correctly", history[0]["request_status"] == "approved")


def test_admin_stats(owner_id):
    print("\n[ADMIN_STATS]")
    before = db.get_admin_stats()

    stats_request_id = db.create_request(owner_id, "Stats Test Request", "desc", 250, "general")
    after_create = db.get_admin_stats()
    check("total_requests +1 immediately after creating a request",
          after_create["total_requests"] == before["total_requests"] + 1)
    check("pending_requests +1 immediately after creating a request",
          after_create["pending_requests"] == before["pending_requests"] + 1)

    db.update_request_status(stats_request_id, "approved")
    after_approve = db.get_admin_stats()
    check("pending -1 and approved +1 after approving",
          after_approve["pending_requests"] == after_create["pending_requests"] - 1
          and after_approve["approved_requests"] == after_create["approved_requests"] + 1)

    db.update_request_status(stats_request_id, "rejected")
    after_reject = db.get_admin_stats()
    check("approved -1 and rejected +1 after rejecting",
          after_reject["approved_requests"] == after_approve["approved_requests"] - 1
          and after_reject["rejected_requests"] == after_approve["rejected_requests"] + 1)

    db.delete_request(stats_request_id, owner_id)
    after_delete = db.get_admin_stats()
    check("total_requests -1 after deleting the stats test request",
          after_delete["total_requests"] == after_reject["total_requests"] - 1)


if __name__ == "__main__":
    print("Running database.py test suite (Users, Requests, Supports, Admin)...")

    db.tables_db()  # make sure tables exist even on a brand-new database file
    cleanup()  # in case a previous run crashed mid-way

    # --- Users ---
    test_tables_created()
    test_email_exists_before_creation()
    user_id = test_create_user()
    test_duplicate_email(user_id)
    test_email_exists_after_creation()
    test_get_user_by_email(user_id)
    test_get_user_by_id(user_id)
    test_role_constraint()
    test_get_all_users(user_id)

    # --- Requests ---
    request_id = test_create_request(user_id)
    test_get_request_by_id(request_id, user_id)
    test_create_request_default_category(user_id)
    test_get_request_by_user_id(user_id, request_id)
    test_get_all_requests_default_hides_pending(request_id)
    test_approve_and_reveal(request_id)
    test_get_all_requests_category_filter(user_id)
    test_search_requests(request_id)
    test_update_request(request_id, user_id)
    test_delete_request(request_id, user_id)

    # --- Supports ---
    test_supports(user_id)

    # --- Admin ---
    test_admin_stats(user_id)

    cleanup()  # leave the real database exactly as we found it (cascades away all test requests/supports too)

    print(f"\n{'='*40}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*40}")
