"""
test_database.py — Helping Hands

Standalone test script for the current database.py (Users functions only,
matching tables_db() / password_hash / no created_at column).

Since get_db_connection() hardcodes "HelpingHands.db", this script does NOT
use a separate test database — it runs against the real file, but every
test user it creates uses an email tagged "_TEST_" and gets deleted before
AND after the run. So it's safe to re-run as many times as you want without
leaving junk behind or needing to touch database.py.

Run:
    python test_database.py
"""

import database as db
import gc

passed = 0
failed = 0

TEST_EMAIL_1 = "gehad_TEST_@example.com"
TEST_EMAIL_2 = "sara_TEST_@example.com"


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


if __name__ == "__main__":
    print("Running database.py test suite (Users functions)...")

    db.tables_db()  # make sure tables exist even on a brand-new database file
    cleanup()  # in case a previous run crashed mid-way

    test_tables_created()
    test_email_exists_before_creation()
    user_id = test_create_user()
    test_duplicate_email(user_id)
    test_email_exists_after_creation()
    test_get_user_by_email(user_id)
    test_get_user_by_id(user_id)
    test_role_constraint()
    test_get_all_users(user_id)

    cleanup()  # leave the real database exactly as we found it

    print(f"\n{'='*40}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*40}")
