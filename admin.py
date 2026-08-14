from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os

# ==========================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================
app = Flask(__name__)
app.secret_key = 'helpinghands_secret_key_for_session_management'
DATABASE = 'database.db'


# ==========================================
# 2. DATABASE HELPER FUNCTIONS
# ==========================================
def get_db_connection():
    """Create and return a row-factory database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'requester', 'donor')) NOT NULL
        )
    ''')

    # Requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            amount_needed REAL NOT NULL,
            status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'fulfilled')) DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Supports / Donations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            request_id INTEGER NOT NULL,
            amount_donated REAL NOT NULL,
            FOREIGN KEY (donor_id) REFERENCES users (id),
            FOREIGN KEY (request_id) REFERENCES requests (id)
        )
    ''')

    conn.commit()
    conn.close()


# ==========================================
# 3. AUTHENTICATION & AUTHORIZATION DECORATORS
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('role') not in roles:
                flash("Access denied: Unauthorized role.", "danger")
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==========================================
# 4. GENERAL & HOME ROUTES
# ==========================================
@app.route('/')
def home():
    conn = get_db_connection()
    # Fetch approved requests for public display
    approved_requests = conn.execute(
        "SELECT r.*, u.username FROM requests r JOIN users u ON r.user_id = u.id WHERE r.status = 'approved'"
    ).fetchall()
    conn.close()
    return render_template('home.html', requests=approved_requests)


# ==========================================
# 5. AUTHENTICATION ROUTES
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, role)
            )
            conn.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists.", "danger")
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome back, {user['username']}!", "success")
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))


# ==========================================
# 6. REQUESTS & DONATIONS ROUTES
# ==========================================
@app.route('/create_request', methods=['GET', 'POST'])
@login_required
@role_required('requester')
def create_request():
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        category = request.form['category']
        amount_needed = float(request.form['amount_needed'])

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO requests (user_id, title, description, category, amount_needed) VALUES (?, ?, ?, ?, ?)",
            (session['user_id'], title, description, category, amount_needed)
        )
        conn.commit()
        conn.close()

        flash("Request submitted successfully and is pending admin approval.", "info")
        return redirect(url_for('my_requests'))

    return render_template('create_request.html')


@app.route('/my_requests')
@login_required
@role_required('requester')
def my_requests():
    conn = get_db_connection()
    user_requests = conn.execute(
        "SELECT * FROM requests WHERE user_id = ?", (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('my_requests.html', requests=user_requests)


@app.route('/support/<int:request_id>', methods=['POST'])
@login_required
@role_required('donor')
def support_request(request_id):
    amount = float(request.form['amount'])
    
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO supports (donor_id, request_id, amount_donated) VALUES (?, ?, ?)",
        (session['user_id'], request_id, amount)
    )
    conn.commit()
    conn.close()

    flash("Thank you for your donation!", "success")
    return redirect(url_for('home'))


# ==========================================
# 7. ADMIN DASHBOARD ROUTES
# ==========================================
@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    conn = get_db_connection()
    
    # System Statistics
    stats = {
        'total_users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'total_requests': conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
        'pending_requests': conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'").fetchone()[0],
        'total_donations': conn.execute("SELECT SUM(amount_donated) FROM supports").fetchone()[0] or 0
    }
    
    # Pending requests awaiting approval
    pending_list = conn.execute(
        "SELECT r.*, u.username FROM requests r JOIN users u ON r.user_id = u.id WHERE r.status = 'pending'"
    ).fetchall()
    
    conn.close()
    return render_template('admin.html', stats=stats, pending_requests=pending_list)


@app.route('/admin/change_status/<int:request_id>/<string:new_status>')
@login_required
@role_required('admin')
def change_status(request_id, new_status):
    if new_status in ['approved', 'rejected', 'fulfilled']:
        conn = get_db_connection()
        conn.execute("UPDATE requests SET status = ? WHERE id = ?", (new_status, request_id))
        conn.commit()
        conn.close()
        flash(f"Request status updated to '{new_status}'.", "success")
    
    return redirect(url_for('admin_dashboard'))


# ==========================================
# 8. ERROR HANDLERS & APP RUNNER
# ==========================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    init_db()  # Auto-creates database tables on startup
    app.run(debug=True)