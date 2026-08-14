"""
seed_fake_data.py -- Helping Hands

Generates realistic dummy data for local testing/demos: users (admins,
requesters, donors), support requests across categories, and pledges
linking donors to requests.

DESIGN NOTE: this script calls into database.py's own functions
(create_user, create_request, create_support, ...) instead of writing a
second set of raw INSERT statements. Those functions already run fully
parameterized SQL and already enforce the constraints that matter here --
create_user returns None on a duplicate email, create_support returns None
on a duplicate donor/request pair -- so idempotency and "don't crash on a
constraint violation" come for free, without a second copy of the schema's
rules to keep in sync with database.py.

Usage:
    python seed_fake_data.py            # wipes existing data, then reseeds
    python seed_fake_data.py --keep     # adds fake data on top of what's there

Requires: faker (pip install faker --break-system-packages)
Falls back to a small built-in name list automatically if faker isn't installed.
"""

import random
import argparse
import faker
import werkzeug

import database as db

# --- password hashing -------------------------------------------------------
try:
    from werkzeug.security import generate_password_hash
except ImportError:
    import hashlib
    def generate_password_hash(pw):
        # Fallback only -- NOT how the real app should hash passwords.
        # Just keeps this script runnable on a machine without Flask/werkzeug.
        return "sha256$" + hashlib.sha256(pw.encode()).hexdigest()

# --- name generation ---------------------------------------------------------
try:
    from faker import Faker
    _fake = Faker()

    def random_name():
        return _fake.name()

except ImportError:
    print("[seed_fake_data] 'faker' not installed -- using a small built-in name list instead.")
    print("[seed_fake_data] For more variety: pip install faker --break-system-packages\n")

    _FIRST_NAMES = ["Ahmed", "Sara", "Omar", "Laila", "Youssef", "Mona", "Khaled", "Nour",
                    "Hassan", "Aya", "Mostafa", "Rana", "Karim", "Dina", "Tarek", "Salma",
                    "Amir", "Heba", "Ziad", "Yasmin"]
    _LAST_NAMES = ["Ibrahim", "Mahmoud", "Farouk", "Adel", "El-Sayed", "Hassan", "Fathy",
                   "Kamal", "Nasser", "Aziz"]

    def random_name():
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"


def random_email(name, tag):
    base = name.lower().replace(" ", ".").replace("'", "")
    return f"{base}{tag}@example.com"


def random_phone():
    return "01" + "".join(random.choice("0123456789") for _ in range(9))


def random_image_url(seed):
    # Lightweight placeholder image service -- no network call needed at seed time,
    # just produces a valid-looking, stable URL string for the given seed.
    return f"https://picsum.photos/seed/{seed}/600/400"


# --- config -------------------------------------------------------------------
NUM_ADMINS = 1
NUM_REQUESTERS = 8
NUM_DONORS = 15
MIN_REQUESTS_PER_REQUESTER = 1
MAX_REQUESTS_PER_REQUESTER = 3
MAX_SUPPORTS_PER_REQUEST = 4

CATEGORIES = ["Medical", "Education", "Housing", "Food", "Emergency", "Debt", "Other"]

# Weighted so the public browse page has plenty to show, some pending
# requests for the admin to review, and a few rejected for realism.
STATUS_WEIGHTS = [("approved", 0.55), ("pending", 0.35), ("rejected", 0.10)]

REQUEST_TITLES = {
    "Medical": ["Emergency surgery costs", "Chemotherapy treatment support",
                "Hospital bill assistance", "Medication for chronic illness"],
    "Education": ["University tuition fees", "School supplies for children",
                  "Laptop for online classes", "Exam fees support"],
    "Housing": ["Rent assistance this month", "Help rebuilding after fire damage",
                "Moving costs for new apartment", "Overdue utility bills"],
    "Food": ["Groceries for the month", "Meals for family of five",
             "Baby formula and essentials", "Food packages for the holidays"],
    "Emergency": ["Flood damage recovery", "Urgent car repair for work commute",
                  "Lost job, need immediate help", "Emergency travel for family"],
    "Debt": ["Small business loan repayment", "Credit card debt relief",
             "Overdue utility debt"],
    "Other": ["General living expenses", "Wheelchair purchase",
              "Funeral cost assistance"],
}

SUPPORT_MESSAGES = [
    "Happy to help cover part of this.",
    "Sending what I can this month.",
    "Wishing you strength -- here's my contribution.",
    "I'd like to help however I can.",
    "Praying for you, will contribute soon.",
    "Let me know how else I can support.",
]

DEMO_PASSWORD = "Passw0rd!"  # same for every seeded account, so you can log in as any of them


def pick_status():
    r = random.random()
    cumulative = 0
    for status, weight in STATUS_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return status
    return STATUS_WEIGHTS[-1][0]


def wipe_all():
    conn = db.get_db_connection()
    conn.execute("DELETE FROM supports")
    conn.execute("DELETE FROM requests")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


def create_unique_user(role, tag, max_attempts=20):
    """
    Keeps trying fresh name/email combos until create_user succeeds.
    Returns (user_id, next_tag). On repeated collisions (extremely unlikely
    given the random numeric tag), gives up after max_attempts and
    returns (None, next_tag) rather than looping forever or crashing.
    """
    for _ in range(max_attempts):
        name = random_name()
        email = random_email(name, tag)
        tag += 1
        if db.email_exists(email):
            continue
        user_id = db.create_user(name, email, generate_password_hash(DEMO_PASSWORD), random_phone(), role)
        if user_id is not None:
            return user_id, tag
    return None, tag


def seed(reset: bool):
    db.tables_db()

    if reset:
        print("Wiping existing data (reset mode)...")
        wipe_all()

    # Random starting suffix so a --keep run doesn't collide with a previous run's emails.
    tag = random.randint(1000, 9999)

    print(f"Creating {NUM_ADMINS} admin(s), {NUM_REQUESTERS} requester(s), {NUM_DONORS} donor(s)...")
    admin_ids, requester_ids, donor_ids = [], [], []

    for _ in range(NUM_ADMINS):
        uid, tag = create_unique_user("admin", tag)
        if uid:
            admin_ids.append(uid)

    for _ in range(NUM_REQUESTERS):
        uid, tag = create_unique_user("requester", tag)
        if uid:
            requester_ids.append(uid)

    for _ in range(NUM_DONORS):
        uid, tag = create_unique_user("donor", tag)
        if uid:
            donor_ids.append(uid)

    print(f"  admins: {len(admin_ids)}, requesters: {len(requester_ids)}, donors: {len(donor_ids)}")

    if not requester_ids:
        print("No requesters were created -- aborting request/support seeding.")
        return

    print("Creating requests...")
    request_ids = []
    for requester_id in requester_ids:
        for _ in range(random.randint(MIN_REQUESTS_PER_REQUESTER, MAX_REQUESTS_PER_REQUESTER)):
            category = random.choice(CATEGORIES)
            title = random.choice(REQUEST_TITLES[category])
            description = f"{title}. Any support is deeply appreciated during this difficult time."
            amount_needed = round(random.uniform(200, 8000), 2)
            image_url = random_image_url(f"{requester_id}-{len(request_ids)}") if random.random() < 0.7 else None

            request_id = db.create_request(requester_id, title, description, amount_needed, category, image_url)
            if request_id is None:
                continue  # shouldn't happen with these amounts, but stay safe rather than crash

            status = pick_status()
            if status != "pending":  # create_request always inserts as 'pending'
                db.update_request_status(request_id, status)

            request_ids.append((request_id, amount_needed, status))

    print(f"  created {len(request_ids)} requests")

    if not donor_ids:
        print("No donors were created -- skipping support/pledge seeding.")
        return

    print("Creating supports/pledges...")
    support_count = 0
    for request_id, amount_needed, status in request_ids:
        if status != "approved":
            continue  # donors only ever see/pledge on approved requests in the real app

        num_supporters = random.randint(0, MAX_SUPPORTS_PER_REQUEST)
        supporters = random.sample(donor_ids, k=min(num_supporters, len(donor_ids)))

        for donor_id in supporters:
            already_pledged = db.get_total_pledged(request_id)
            remaining = amount_needed - already_pledged
            if remaining <= 1:
                break  # essentially fully funded -- stop piling on more pledges

            if random.random() < 0.2:
                # message-only "I Want to Help", no committed amount
                amount = None
            else:
                # pledge a realistic slice of what's left: 10%-50% of the
                # remaining need, capped at what's actually still needed --
                # keeps totals sane relative to the request's goal
                amount = round(min(remaining, remaining * random.uniform(0.1, 0.5)), 2)

            support_id = db.create_support(request_id, donor_id, random.choice(SUPPORT_MESSAGES), amount)
            if support_id is not None:
                support_count += 1

    print(f"  created {support_count} supports/pledges")
    print(f"\nDone. Every seeded account's password is: {DEMO_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed HelpingHands.db with realistic fake data.")
    parser.add_argument("--keep", action="store_true",
                         help="Add fake data on top of what's already there instead of wiping first.")
    args = parser.parse_args()
    seed(reset=not args.keep)
