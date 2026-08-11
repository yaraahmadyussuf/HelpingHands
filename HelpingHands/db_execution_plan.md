# Helping Hands — Database Engineer: Execution Plan & Blueprint

**Role:** Database & Data Logic Engineer
**Timeline:** 4 days, working solo, then handed off to the team
**Deliverables:** `database.py` (by you, following this spec), `test_database.py`, a demo data seeder, and a handover doc

This document is the spec. You write the code from it — nothing here is meant to be copy-pasted.

---

## 1. The 4-Day Roadmap

### Day 1 — Schema + Connection Layer + Users
- Finalize the three tables exactly as given (users, requests, supports) — do not add columns yet, resist the urge.
- Write your connection helper and `init_db()`.
- Decide your foreign key behavior up front: requests.user_id → users.id, supports.request_id → requests.id, supports.donor_id → users.id. Both should cascade on delete (if a user or request is deleted, their dependent rows go with them) — decide this now, it affects your delete functions later.
- Build and manually verify every **Users** function (Section 2.1).
- End of day checkpoint: you can create a user, fetch it by email, fetch it by id, and duplicate-email creation correctly fails.

### Day 2 — Requests
- Build every **Requests** function (Section 2.2): create, get-by-id, get-by-user, get-all (with status/category filters), search, update, delete, status change.
- Bake in the two business rules that matter most for your team's Phase 19 security requirements: only the owning user can edit/delete their request; amount_needed must be > 0.
- End of day checkpoint: a request can be created as "pending," is invisible to the public browse function until "approved," and an edit/delete from a non-owner is correctly rejected.

### Day 3 — Supports + Admin + Full Test Suite
- Build every **Supports** function (Section 2.3): create support, duplicate prevention, fetch supporters for a request, fetch a donor's history.
- Build **Admin** functions (Section 2.4): stats, list all users, approve/reject.
- Write the full standalone test script (Section 3) and run it to green. This is your definition of done for the whole layer — don't move on until every check passes.
- End of day checkpoint: `test_database.py` runs clean with zero failures, covering all three tables.

### Day 4 — Demo Data + Handover + Buffer
- Write `seed_demo_data()` (Section 4) and run it once against a clean database; manually browse the resulting data to confirm it tells a coherent story (a pending request, an approved one, at least one support).
- Write the handover doc (Section 5) and send it to Members 3, 4, and 5 — don't wait for them to ask.
- Reserve the second half of Day 4 as buffer: sit with each teammate while they wire their first call to your module, since integration bugs (wrong argument order, wrong table assumptions) surface here, not in your own tests.
- Freeze `database.py`. After today, changes go through you on request, not ad hoc edits by others.

---

## 2. Function Blueprint

Organize these into four sections inside `database.py`, matching the order below. Every function should open its own connection and close it before returning — don't leave connections open across calls.

### 2.0 Foundation

**`get_db_connection()`**
- Input: none
- Returns: a connection object configured so rows can be accessed by column name (not just index) — this matters because every other function and every teammate will read fields like `row["name"]`.
- Logic: also enable foreign key enforcement on the connection, since SQLite has it off by default.

**`init_db()`**
- Input: none
- Returns: nothing
- Logic: creates all three tables if they don't exist, with the constraints below. Safe to call on every app startup.
  - `users.role` constrained to one of requester/donor/admin.
  - `users.email` unique.
  - `requests.status` constrained to one of pending/approved/rejected, defaulting to pending.
  - `requests.amount_needed` constrained to be greater than 0 at the schema level as a second line of defense (your function-level check is the first).
  - Foreign keys as decided on Day 1, with cascade delete.

**`_now()`** (private helper)
- Input: none
- Returns: a timestamp string for `created_at` columns
- Logic: single source of truth for timestamp formatting so all three tables stay consistent.

### 2.1 Users

**`email_exists(email: str)`**
- Returns: boolean
- Logic: simple existence check, used internally before insert and externally by Member 3 before registration attempts.

**`create_user(name: str, email: str, password_hash: str, phone: str, role: str)`**
- Returns: the new user's id (int) on success, or `None` if the email is already taken
- Logic: reject the insert if `email_exists` is true, rather than relying on the database's unique constraint to fail loudly. This is a deliberate choice — a clean `None` return is easier for the auth route to handle than catching a database exception.
- Note: this function does NOT hash the password. Member 3 hands you an already-hashed string. Document this loudly in your handover — it's the single most common integration bug.

**`get_user_by_email(email: str)`**
- Returns: the matching row, or `None`
- Used by: login flow, duplicate checks.

**`get_user_by_id(user_id: int)`**
- Returns: the matching row, or `None`
- Used by: session lookups, joining requester/donor info onto other tables.

**`get_all_users()`**
- Returns: list of rows, excluding the password column
- Logic: never return the password field here, even hashed — this function feeds the admin "view users" panel directly to a template.

### 2.2 Requests

**`create_request(user_id: int, title: str, description: str, category: str, amount_needed: float)`**
- Returns: new request id (int)
- Logic: raise a validation error rather than silently inserting if `amount_needed <= 0`. Status is always forced to "pending" on creation — never accept status as a parameter here, since a requester should never be able to self-approve.

**`get_request_by_id(request_id: int)`**
- Returns: the row, or `None`
- Logic: join in the requester's name and email from `users` so the request-details page doesn't need a second query. This is the single most-used read function in the app — the details page, the "who posted this" check, and the ownership checks in update/delete all lean on it.

**`get_requests_by_user(user_id: int)`**
- Returns: list of rows, most recent first
- Used by: "My Requests" on the requester dashboard.

**`get_all_requests(status: str, category: str)`**
- Returns: list of rows, most recent first
- Logic: `status` defaults to "approved" (public visibility rule — pending/rejected requests should never appear on the public browse page by default). Passing `None` explicitly for status should return all statuses, which is what the admin panel needs. `category` similarly optional — `None` means no category filter.

**`search_requests(keyword: str, status: str)`**
- Returns: list of rows matching the keyword against title, description, or category (partial, case-insensitive)
- Logic: same status-defaulting behavior as `get_all_requests` — a public search should not surface pending or rejected requests.

**`update_request(request_id: int, user_id: int, **fields)`**
- Returns: boolean — true if the update happened, false otherwise
- Logic: **this is your most important rule function.** Look up the request's owner first; if `user_id` doesn't match, return false and touch nothing. Only allow title/description/category/amount_needed to be changed here — never let this function change `status` or `user_id`. Re-validate amount_needed > 0 if it's among the fields being changed.

**`delete_request(request_id: int, user_id: int)`**
- Returns: boolean
- Logic: identical ownership check to `update_request`. On success, supports tied to this request should cascade-delete (handled by the foreign key if you set it up on Day 1).

**`update_request_status(request_id: int, status: str)`**
- Returns: boolean
- Logic: this is the admin approve/reject action — deliberately has no `user_id`/ownership parameter, since only admin routes should call it, and that authorization check belongs in the Flask route, not here. Reject silently (return false) if the status string isn't one of the three valid values.

### 2.3 Supports

**`has_donor_supported(request_id: int, donor_id: int)`**
- Returns: boolean
- Logic: existence check, used internally before insert and externally by the UI to decide whether to show "I Want to Help" or "Already offered."

**`create_support(request_id: int, donor_id: int, message: str)`**
- Returns: new support id (int), or `None` if this donor already supports this request
- Logic: duplicate prevention is mandatory here — one donor should not be able to click "I Want to Help" twice on the same request and create two rows.

**`get_supports_for_request(request_id: int)`**
- Returns: list of rows joined with donor name/email
- Used by: the requester's "People Interested in Helping" view — this is one of the two functions that make the whole product's core loop visible, so get the join right and test it explicitly.

**`get_supports_by_donor(donor_id: int)`**
- Returns: list of rows joined with the request's title/status
- Used by: a donor's own support history, if the team builds that dashboard.

### 2.4 Admin

**`get_admin_stats()`**
- Returns: a small structured result with total user count, total request count, and counts of pending/approved/rejected requests
- Used by: the admin dashboard's summary numbers. Keep this cheap — five separate count queries is fine at this data scale, don't over-engineer it.

**`get_all_users()`** — already listed in 2.1, admin reuses it.

**`update_request_status()`** — already listed in 2.2, admin reuses it.

---

## 3. Testing & Validation Strategy

Build this as a single standalone script, `test_database.py`, that you can run with no Flask app running at all.

**Step 1 — Isolate the test database.** Before importing anything, override your module's database file path so tests run against a throwaway file, never the real `helpinghands.db`. Delete that throwaway file at the start of each run so tests are repeatable.

**Step 2 — Write a tiny check helper.** A single function that takes a label and a boolean, and prints PASS or FAIL. This avoids a real test framework dependency and keeps output readable for teammates who've never used one.

**Step 3 — Test users in isolation.** Create a user, confirm you get an id back. Attempt a duplicate email, confirm you get `None` back — not an exception. Fetch by email and by id, confirm both return the right row, and confirm a lookup for a nonexistent id returns `None` rather than raising.

**Step 4 — Test requests, using the user id from Step 3.** Create a request, confirm it starts as "pending." Confirm `get_all_requests` with the default status does NOT include it yet. Approve it via `update_request_status`, then confirm it now appears. Try an invalid amount (zero or negative) and confirm it's rejected. Attempt an update/delete using a *wrong* user id and confirm both are blocked; then repeat with the correct owner id and confirm both succeed.

**Step 5 — Test supports, using the request id from Step 4 and a second, newly created donor user.** Create a support, confirm an id comes back. Attempt the same donor supporting the same request again, confirm you get `None`. Confirm the "supports for this request" lookup returns exactly one row with the donor's name correctly joined in.

**Step 6 — Test admin functions.** Create a third user with role admin. Pull stats and confirm the counts match what you've inserted so far (this is where off-by-one mistakes in your count queries surface). Confirm `get_all_users` returns all users created in the run, with no password field present.

**Step 7 — Test deletion last, after everything else has been verified.** Delete the request from Step 4 and confirm it's gone. If you set cascade delete correctly, also confirm the associated support row from Step 5 is gone — this is an easy thing to get wrong and worth an explicit check.

**Step 8 — Print a final summary count of passed/failed checks, and clean up the throwaway database file.** Treat "0 failed" as your actual Day 3 milestone, not "the script ran without crashing."

Re-run this script after any change to `database.py`, for the rest of the project — it's your regression net.

---

## 4. Demo Data Guide

Write a separate function, `seed_demo_data()`, that is never called automatically by the app — only run manually, once, shortly before the presentation.

**What it should do:**
1. Wipe all three tables clean first (in dependency order: supports, then requests, then users) so re-running it doesn't create duplicates.
2. Create 2–3 users covering all three roles: at least one requester, one donor, one admin. Use realistic names/emails your team will recognize while demoing.
3. Create 2–3 requests under the requester(s), with different statuses on purpose — one pending (to demo the admin approval flow live), one already approved (to demo the public browse/search flow immediately).
4. Create at least one support record connecting the donor to the approved request, so the requester's "people interested in helping" view isn't empty on first load.

**What it should not do:**
- Don't hash real passwords for demo accounts with anything sensitive — these are throwaway accounts, but still route them through whatever hashing function Member 3 exposes, so login actually works during the live demo if someone tries to log in as the demo requester.
- Don't wire this into `init_db()` or app startup. It should be a deliberate, manual, one-line command someone runs the morning of the demo, not something that fires on every server restart and quietly resets real testing data.

---

## 5. Team Handover Protocol

Send each teammate only the section relevant to them, plus the shared ground rules. Keep it to function name, inputs, return value, and any gotcha — they don't need your internal implementation details.

### To Member 3 (Auth)
Hand off: `email_exists`, `create_user`, `get_user_by_email`, `get_user_by_id`.
Critical note to include explicitly: `create_user` expects an already-hashed password string — hashing is entirely their responsibility, you only store what they give you. Also flag that `create_user` returning `None` means "email taken," not an error — their route should check for that and re-render the form with a message, not crash.

### To Member 4 (Requests & Donors)
Hand off: `create_request`, `get_request_by_id`, `get_requests_by_user`, `get_all_requests`, `search_requests`, `update_request`, `delete_request`, `create_support`, `has_donor_supported`, `get_supports_for_request`, `get_supports_by_donor`.
Critical notes to include: ownership checks are already enforced inside `update_request`/`delete_request` — they pass the logged-in user's id and trust the boolean result, they should not re-check ownership themselves. `get_request_by_id` already includes the requester's name/email, so no second lookup is needed on the details page. `create_request` can raise a validation error on bad amounts — they need a try/except around that call.

### To Member 5 (Admin)
Hand off: `get_all_users`, `update_request_status`, `get_admin_stats`.
Critical note to include: `update_request_status` has no built-in permission check — it will happily execute if called, so their admin routes must independently confirm the logged-in user's role is "admin" before ever calling it. This is the one place your data layer deliberately does not enforce authorization, and it needs to be said out loud so it isn't assumed to be handled.

### Shared ground rules for all three
- No raw SQL anywhere outside `database.py` — new query needs come to you, not a teammate's own `sqlite3.connect` call.
- Rows behave like dictionaries for reading (`row["column"]`), but aren't real dicts — if someone needs to serialize to JSON, they wrap it themselves.
- Status strings are exactly `pending` / `approved` / `rejected`, role strings are exactly `requester` / `donor` / `admin` — lowercase, no synonyms, anywhere in the app.
- Nobody touches `database.py` after your Day 4 freeze without telling you first.
