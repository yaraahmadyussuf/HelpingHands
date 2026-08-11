import sqlite3 as db
import time

#connect with database
def get_db_connection() :
    conn = db.connect("HelpingHands.db")
    conn.row_factory = db.Row        # cast from tuple to dictionary to call with column not order
    conn.execute("PRAGMA foreign_keys = ON;")        #for safety
    return conn

#create tables --> users - request - support 
def tables_db() :
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests (id) ON DELETE CASCADE,
        FOREIGN KEY (donor_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """
    cursor.execute(supports_table)

    #save and close
    conn.commit()
    conn.close()

def current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S")

#Users Functions
def email_exists(email: str) :
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))  #return the raw if existed
    result = cursor.fetchone()  #selsct one

    conn.close()

    #if true then the email is already exists
    if result :
        return True
    else :
        return False


# Creates a new user record if the email is unique, returning the generated user_id or None if duplicate
def create_user(name: str, email: str, password_hash: str, phone: str, role: str) :

    if email_exists(email) :
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    # Parameterized query to prevent SQL injection and map parameters to placeholders
    query = "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)"

    cursor.execute(query, (name, email, password_hash, phone, role))
    conn.commit()

    # Retrieve the auto-incremented PRIMARY KEY of the newly inserted row
    user_id = cursor.lastrowid

    conn.close()
    return user_id


def get_user_by_email(email: str) :
    #connect with databse + access by cursor
    conn = get_db_connection()
    cursor = conn.cursor()

    #if mail exists will return the < user > else return < None > then close database
    try :
        cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone() 
        return user
    finally :
        conn.close()

def get_user_by_id(user_id: int) :
    #connect with databse + access by cursor
    conn = get_db_connection()
    cursor = conn.cursor()

    #if mail exists will return the < user_id > else return < None > then close database
    try :
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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
        cursor = conn.execute("SELECT id, name, email, phone, role FROM users")
        all_users = cursor.fetchall()
        return all_users
    finally :
        conn.close()









#JUST TESTING FOR ME NOT RELATED TO CODE OR AFFECT DATABASE
if __name__ == "__main__":
    print("---> Starting Day 1 Tests <---")
    
    tables_db()
    print("1. Database initialized.")

    user_id = create_user("Gehad Khaled", "gehad@example.com", "hashed_secret_123", "01012345678", "admin")
    print(f"2. User created with ID: {user_id}")

    duplicate_user_id = create_user("Another Gehad", "gehad@example.com", "hashed_secret_456", "01112345678", "donor")
    print(f"3. Duplicate user attempt result (Should be None): {duplicate_user_id}")

    user_by_email = get_user_by_email("gehad@example.com")
    if user_by_email:
        print(f"4. Found by email: {user_by_email['name']} | Role: {user_by_email['role']}")

    if user_id is not None:
        user_by_id = get_user_by_id(user_id)
        if user_by_id:
            print(f"5. Found by ID: {user_by_id['email']}")

    all_users = get_all_users()
    print(f"6. Total users fetched: {len(all_users)}")
    for u in all_users:
        print("   User Data:", dict(u))

    print("---> All Day 1 Tests Finished <---")