import sqlite3 as db
import time
from typing import Any

#connect with database
def get_db_connection():
    conn = db.connect("HelpingHands.db")
    # cast from tuple to dictionary to call with column not order
    conn.row_factory = db.Row
    #for safety
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

#create tables --> users - request - support 
def tables_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        role TEXT CHECK (role IN ('requester', 'donor', 'admin')) NOT NULL
    );
    """
    cursor.execute(users_table)

    requests_table = """
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        amount_needed REAL CHECK (amount_needed > 0) NOT NULL,
        status TEXT CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_url TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """
    cursor.execute(requests_table)

    supports_table = """
    CREATE TABLE IF NOT EXISTS supports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        donor_id INTEGER NOT NULL,
        message TEXT,
        amount REAL CHECK (amount > 0),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests (id) ON DELETE CASCADE,
        FOREIGN KEY (donor_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """
    cursor.execute(supports_table)

    #save and close
    conn.commit()
    conn.close()

tables_db()


def current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S")

#User Functions
def email_exists(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    #select data from database and return the raw if existed
    cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()  #selsct one

    conn.close()

    #if true then the email is already exists
    if result :
        return True
    else :
        return False


# Creates a new user record if the email is unique, returning the generated user_id or None if duplicate
def create_user(name: str, email: str, password_hash: str, phone: str, role: str):

    if email_exists(email) :
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Parameterized query to prevent SQL injection and map parameters to placeholders
        query = "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)"

        #insert data to database
        cursor.execute(query, (name, email, password_hash, phone, role))
        conn.commit()

        # Retrieve the auto-incremented PRIMARY KEY of the newly inserted row
        user_id = cursor.lastrowid
        return user_id
    finally:
        conn.close()


def get_user_by_email(email: str):
    #connect with databse + access by cursor
    conn = get_db_connection()
    cursor = conn.cursor()

    #if mail exists will return the < user > else return < None > then close database
    try :
        #select data from database
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone() 
        return user
    finally :
        conn.close()

def get_user_by_id(user_id: int):
    #connect with databse + access by cursor
    conn = get_db_connection()
    cursor = conn.cursor()

    #if mail exists will return the < user_id > else return < None > then close database
    try :
        #select data from database
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone() 
        return user
    finally :
        conn.close()

def get_all_users():
    #connect with databse + access by cursor
    conn = get_db_connection()
    cursor = conn.cursor()

    #if there is users return them all with information but not password for safety then close database
    try :
        #select data from database
        cursor.execute("SELECT id, name, email, phone, role FROM users")
        all_users = cursor.fetchall()
        return all_users
    finally :
        conn.close()

#request functions
def create_request(user_id: int, title: str, description: str , amount_needed: float, category: str = "general", image_url: str = None):
    if amount_needed is None or amount_needed <= 0:
        return None
    
    #connect with databse + access by cursor
    conn = get_db_connection()
    cursor = conn.cursor()

    #try..finally --> to make sure that in all cases the database will close --> keep it safe + easier to debugg the code
    try :
        created_at = current_time()
        query = "INSERT INTO requests (user_id, title, description, category, amount_needed, status, created_at, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

        #insert data to database
        cursor.execute(query, (user_id, title, description, category, amount_needed, "pending", created_at, image_url))
        conn.commit()
        request_id  =cursor.lastrowid
        return request_id
    finally :
        conn.close()


def get_request_by_id(request_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    #if request exists will return the < request > else return < None > then close database
    try :
        #select data from database
        cursor.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        request = cursor.fetchone() 
        return request
    finally :
        conn.close()


def get_request_by_user_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    #if request exists will return the < request > else return < None > then close database
    try :
        #select data from database
        cursor.execute("SELECT * FROM requests WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        request = cursor.fetchall() 
        return request
    finally :
        conn.close()


def get_all_requests(status: str | None = "approved", category: str | None = None):
    """
    Fetches all requests from the database with optional filtering by status and category.

    Parameters:
    - status (str | None): Defaults to "approved" so regular users only see approved requests. 
                           Can be set to None (e.g., by admins) to fetch requests regardless of status.
    - category (str | None): Defaults to None (fetch all categories). If specified, filters by that category.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Condition 1: Both status and category are provided.
        # SQLite filters using both conditions connected with 'AND'.
        if status and category:
            cursor.execute(
                "SELECT * FROM requests WHERE status = ? AND category = ? ORDER BY created_at DESC", 
                (status, category)
            )
            
        # Condition 2: Only status is provided (e.g., default user view for all categories).
        elif status:
            cursor.execute(
                "SELECT * FROM requests WHERE status = ? ORDER BY created_at DESC", 
                (status,)
            )
            
        # Condition 3: Only category is provided while status is None (e.g., admin viewing a specific category across all statuses).
        elif category:
            cursor.execute(
                "SELECT * FROM requests WHERE category = ? ORDER BY created_at DESC", 
                (category,)
            )
            
        # Condition 4: Neither status nor category is provided (admin fetching all requests without any filter).
        else:
            cursor.execute("SELECT * FROM requests ORDER BY created_at DESC")


        all_requests = cursor.fetchall()
        return all_requests
        
    finally:
        conn.close()


def search_requests(keyword: str, status: str | None = "approved"):
    """
    Searches for a keyword inside request titles, descriptions, or categories, with optional status filtering.

    Parameters:
    - keyword (str): The search phrase entered by the user.
    - status (str | None): Defaults to "approved" for general search. Set to None for admin global search.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Prepare partial matching for SQLite using wildcard characters (%)
    # The '%' wildcard matches any sequence of characters before or after the keyword
    search_pattern = f"%{keyword}%"

    try:
        # Scenario 1: Status filtering is active (regular user search).
        # Parentheses group the OR statements for fields so the AND status condition applies correctly.
        # Pass search_pattern 3 times to match the 3 LIKE placeholders + 1 for status (total 4 parameters).
        if status:
            cursor.execute(
                "SELECT * FROM requests WHERE (title LIKE ? OR description LIKE ? OR category LIKE ?) AND status = ? ORDER BY created_at DESC", 
                (search_pattern, search_pattern, search_pattern, status)
            )
            
        # Scenario 2: Status is None (admin searching across pending, approved, and rejected requests).
        # The status constraint is removed, requiring only 3 parameters for the LIKE placeholders.
        else:
            cursor.execute(
                "SELECT * FROM requests WHERE (title LIKE ? OR description LIKE ? OR category LIKE ?) ORDER BY created_at DESC", 
                (search_pattern, search_pattern, search_pattern)
            )
            
        requests = cursor.fetchall()
        return requests
        
    finally:
        conn.close()



# REQUESTS FUNCTIONS


def update_request(request_id: int, user_id: int, admin_override: bool = False, **fields: Any) -> bool:
    """
    Updates specific fields of an existing request.
    
    Logic:
    - Verifies request existence and ensures caller is the owner (or an admin with admin_override=True).
    - Filters incoming fields against 'allowed_fields' to prevent unauthorized updates.
    - Dynamically generates the SQL SET clause based on provided arguments.
    
    SQL Query:
    - query = f"UPDATE requests SET {set_clause} WHERE id = ?"
    - Uses parameterized placeholders (?) to prevent SQL Injection.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    allowed_fields = ["title", "description", "category", "amount_needed", "image_url"]

    try:
        request = get_request_by_id(request_id) 
        if not request or (request["user_id"] != user_id and not admin_override):
            return False

        updates: dict[str, Any] = {}
        for key, value in fields.items():
            if key in allowed_fields:
                updates[key] = value
        
        if not updates:
            return False
            
        if "amount_needed" in updates and updates["amount_needed"] <= 0:
            return False

        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(request_id)

        query = f"UPDATE requests SET {set_clause} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        return True
    finally:
        conn.close()


def delete_request(request_id: int, user_id: int, admin_override: bool = False) -> bool:
    """
    Deletes a specific request from the database.
    
    Logic:
    - Verifies request existence and checks owner permission or admin override.
    - Permanently removes the record from the 'requests' table.
    
    SQL Query:
    - "DELETE FROM requests WHERE id = ?"
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        request = get_request_by_id(request_id) 
        if not request or (request["user_id"] != user_id and not admin_override):
            return False
        
        cursor.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def update_request_status(request_id: int, status: str) -> bool:
    """
    Updates the status of a request (Admin feature: Approve/Reject).
    
    Logic:
    - Validates that the status string belongs to allowed statuses ('pending', 'approved', 'rejected').
    
    SQL Query:
    - "UPDATE requests SET status = ? WHERE id = ?"
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    allowed_status = ["pending", "approved", "rejected"]

    try:
        if get_request_by_id(request_id) and status in allowed_status:
            cursor.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
            conn.commit()
            return True
        else:
            return False
    finally:
        conn.close()



# SUPPORT FUNCTIONS


def has_donor_supported(request_id: int, donor_id: int) -> bool:
    """
    Checks if a donor has already pledged support for a specific request.
    
    Logic:
    - Prevents duplicate supports/pledges from the same donor for the same request.
    
    SQL Query:
    - "SELECT 1 FROM supports WHERE request_id = ? AND donor_id = ?"
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM supports WHERE request_id = ? AND donor_id = ?", (request_id, donor_id))
        support = cursor.fetchone()
        return support is not None
    finally:
        conn.close()


def create_support(request_id: int, donor_id: int, message: str ,amount: float | None = None):
    """
    Records a new support/pledge entry for a request.
    
    Logic:
    - Checks for prior support first, inserts the pledge with current timestamp, and returns the generated ID.
    
    SQL Query:
    - "INSERT INTO supports (request_id, donor_id, message, amount, created_at) VALUES (?, ?, ?, ?, ?)"
    """
    if has_donor_supported(request_id, donor_id):
        return None
    
    if amount is not None and amount <= 0:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = current_time()

    try:
        query = "INSERT INTO supports (request_id, donor_id, message, amount, created_at) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, (request_id, donor_id, message, amount, created_at))
        support_id = cursor.lastrowid
        conn.commit()
        return support_id
    finally:
        conn.close()


def get_supports_for_request(request_id: int) -> list[dict]:
    """
    Retrieves all support records for a given request.
    
    Logic:
    - Fetches support records joined with donor user info (name, email) for display on the request details page.
    
    SQL Query:
    - JOIN users u ON s.donor_id = u.id (Links support table with user table to retrieve donor details).
    - ORDER BY s.created_at DESC (Sorts pledges from newest to oldest).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            s.id, s.request_id, s.donor_id, s.message, s.amount, s.created_at,
            u.name AS donor_name, u.email AS donor_email
        FROM supports s
        JOIN users u ON s.donor_id = u.id
        WHERE s.request_id = ?
        ORDER BY s.created_at DESC
        """
        cursor.execute(query, (request_id,))
        donor = cursor.fetchall()
        return [dict(row) for row in donor]
    finally:
        conn.close()


def get_supports_by_donor(donor_id: int) -> list[dict]:
    """
    Retrieves all supports created by a specific donor.
    
    Logic:
    - Fetches user pledges along with target request details for the donor dashboard/profile.
    
    SQL Query:
    - JOIN requests r ON s.request_id = r.id (Links support table with requests table for titles and status).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT 
            s.id, s.request_id, s.donor_id, s.message, s.amount, s.created_at,
            r.title AS request_title, r.status AS request_status
        FROM supports s
        JOIN requests r ON s.request_id = r.id
        WHERE s.donor_id = ?
        ORDER BY s.created_at DESC
        """
        cursor.execute(query, (donor_id,))
        supported = cursor.fetchall()
        return [dict(row) for row in supported]
    finally:
        conn.close()


def get_total_pledged(request_id: int) -> float:
    """
    Calculates the total amount pledged/supported for a specific request.
    
    Logic:
    - Sums all pledges and handles NULL results using COALESCE to safely return 0.0 if no pledges exist.
    
    SQL Query:
    - SELECT COALESCE(SUM(amount), 0) FROM supports WHERE request_id = ?
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM supports WHERE request_id = ?", (request_id,))
        result = cursor.fetchone()[0]
        return float(result)
    finally:
        conn.close()


# ADMIN FUNCTIONS

def get_admin_stats() -> dict[str, int]:
    """
    Calculates system metrics for the admin dashboard.
    
    Logic:
    - Returns counts of users, total requests, and request breakdowns by status.
    
    SQL Query:
    - Uses aggregate COUNT(*) queries across users and requests tables.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_requests = cursor.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        pending_requests = cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'").fetchone()[0]
        approved_requests = cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'approved'").fetchone()[0]
        rejected_requests = cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'rejected'").fetchone()[0]

        return {
            "total_users": total_users,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests
        }
    finally:
        conn.close()


#get_all_users() & update_request_status() --> also for admin




