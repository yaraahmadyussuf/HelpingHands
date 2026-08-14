"""
Seed the database with demo data so the site isn't empty on first run.

Run it once, from the project folder, with the virtual environment active:

    python seed_data.py

Safe to re-run: it wipes and recreates users/requests/supports every time
(the schema itself - tables_db() - is untouched, so no columns are lost).

This only uses functions that already exist in database.py
(create_user, create_request, create_support) - no new DB logic here.
"""

import sqlite3
from werkzeug.security import generate_password_hash

import database as db


def wipe_existing_data():
    conn = db.get_db_connection()
    conn.execute("DELETE FROM supports")
    conn.execute("DELETE FROM requests")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


def seed():
    db.tables_db()  # make sure tables exist
    wipe_existing_data()

    password = generate_password_hash("password123")

    # ---------------- Users ----------------
    admin_id = db.create_user("Admin", "admin@helpinghands.com", password, "01000000000", "admin")

    sara_id = db.create_user("Sara Ahmed", "sara@example.com", password, "01011111111", "requester")
    mostafa_id = db.create_user("Mostafa Ali", "mostafa@example.com", password, "01022222222", "requester")
    nourhan_id = db.create_user("Nourhan Fathy", "nourhan@example.com", password, "01033333333", "requester")

    omar_id = db.create_user("Omar Hassan", "omar@example.com", password, "01044444444", "donor")
    yasmin_id = db.create_user("Yasmin Adel", "yasmin@example.com", password, "01055555555", "donor")

    print("Created users (all passwords: password123)")

    # ---------------- Requests ----------------
    r1 = db.create_request(
        sara_id,
        "Tuition fees for final year",
        "I'm in my final year of college and short on tuition fees this semester. Any support would mean a lot.",
        4500,
        "Education",
    )

    r2 = db.create_request(
        mostafa_id,
        "Medication for my father",
        "My father needs monthly medication for a chronic condition and we're struggling to cover the cost.",
        2200,
        "Medical",
    )

    r3 = db.create_request(
        nourhan_id,
        "Groceries for the month",
        "Lost my job last month and I'm trying to cover groceries for my two kids until I find work again.",
        1200,
        "Food",
    )

    r4 = db.create_request(
        sara_id,
        "Rent support for this month",
        "Behind on rent this month after an unexpected car repair. Trying to catch up before the deadline.",
        3000,
        "Housing",
    )

    r5 = db.create_request(
        mostafa_id,
        "School supplies for my siblings",
        "Need to buy books and supplies for my younger siblings before the new school term starts.",
        800,
        "Education",
    )

    # Approve some, reject one, leave one pending - so the admin dashboard
    # and the public list both have something interesting to show.
    db.update_request_status(r1, "approved")
    db.update_request_status(r2, "approved")
    db.update_request_status(r3, "approved")
    db.update_request_status(r4, "rejected")
    # r5 stays "pending" (the default) on purpose

    print("Created requests: 3 approved, 1 rejected, 1 pending")

    # ---------------- Supports ----------------
    db.create_support(r1, omar_id, "Happy to help cover part of this - good luck with your finals!")
    db.create_support(r1, yasmin_id, "Wishing you all the best.")
    db.create_support(r2, omar_id, "Sending support for your father's care.")
    db.create_support(r3, yasmin_id, "Hope this helps even a little.")

    print("Created supports")
    print()
    print("Done. Demo accounts (password for all: password123):")
    print("  admin@helpinghands.com   (admin)")
    print("  sara@example.com         (requester)")
    print("  mostafa@example.com      (requester)")
    print("  nourhan@example.com      (requester)")
    print("  omar@example.com         (donor)")
    print("  yasmin@example.com       (donor)")


if __name__ == "__main__":
    seed()
