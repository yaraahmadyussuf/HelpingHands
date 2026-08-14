import os   #==> -- to deal with file path (windows) -- >
import sqlite3
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import database as db
from authentication import login_required, role_required 
from requests import requests_bp  

# ==================== INIT ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = "HelpingHands_Secret_Key_Nti"  
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB Limit
app.register_blueprint (requests_bp)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Initialize database tables
db.tables_db()

                #====Routes====#
# ==================== 1. AUTHENTICATION & PUBLIC (auth.xxx) ====================

@app.route('/', endpoint='auth.home')
@app.route('/home', endpoint='auth.home')
def home():
    stats = db.get_admin_stats()
    all_reqs = db.get_all_requests(status="approved")
    recent_requests = all_reqs[:3] if all_reqs else []
    return render_template("homepage.html", stats=stats, requests=recent_requests)


@app.route("/about", endpoint='auth.about')
def about():
    return render_template("about.html")


                        # (HTTP) 
@app.route("/register", methods=["GET", "POST"], endpoint='auth.register')
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone", "")

        # Database only allows requester/donor/admin Templates historically posted
        role = request.form.get("role", "requester")
        if role == "beneficiary":  # ==>  # "beneficiary" map it
            role = "requester"

        if not name or not email or not password or not role:
            flash("Please fill all required fields", "danger")
            return render_template("register.html")

        hashed_password = generate_password_hash(password) # ==> From Werkzeug.security

        try:
            user_id = db.create_user(name, email, hashed_password, phone, role)
        except sqlite3.IntegrityError: # ==> if user use a repeated email ==> user_id=None
            user_id = None
            flash("Could not create account with the provided details", "danger")
            return render_template("register.html")

        if user_id is None:
            flash("Email already exists", "danger")
            return render_template("register.html")

        flash("Account created successfully! You can log in now.", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("register.html")  # ==> (GET)


@app.route("/login", methods=["GET", "POST"], endpoint='auth.login')
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.get_user_by_email(email)
        if user:
            user = dict(user)  # ==> to copy it ane easily edit it 

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))

        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        session["is_logged_in"] = True
        session["user_name"] = user["name"]

        flash(f"Welcome back, {session['name']}!", "success")
        return redirect(url_for("admin.dashboard") if session["role"] == "admin" else url_for("auth.home"))

    return render_template("login.html") # ==> (GET)


@app.route("/logout", endpoint='auth.logout')
def logout():
    session.clear() 
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.home"))


# ==================== DASHBOARD ====================

@app.route("/dashboard")
@login_required
def dashboard():
    user = db.get_user_by_id(session["user_id"])
    user_requests = db.get_request_by_user_id(session["user_id"])
    user_supports = db.get_supports_by_donor(session["user_id"])

    recommended_cases = []
    if session.get("role") == "donor":
        recommended_cases = db.get_all_requests(status="approved")[:6]

    return render_template(
        "dashboard.html",
        user=user,
        requests=user_requests,
        user_requests=user_requests,
        user_supports=user_supports,
        recommended_cases=recommended_cases,
    )



# ==================== Admin ====================

@app.route("/admin", endpoint='admin.dashboard')
@role_required("admin")
def admin():
    stats = db.get_admin_stats() 
    users = db.get_all_users()   # ==> # Get all registered users
    all_requests = db.get_all_requests(status=None)
    pending_requests = [c for c in all_requests if c["status"] == "pending"]

    return render_template(
        "dashboard.html",
        stats=stats,
        users=users,
        requests=all_requests,
        pending_requests=pending_requests
    )


@app.route("/admin/request/<int:request_id>/<status>", methods=["POST", "GET"], endpoint='admin.change_status')
def change_request_status(request_id, status):
    if "user_id" not in session or session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))

    if status not in ["approved", "rejected", "pending"]:
        flash("Invalid status", "danger")
        return redirect(url_for("admin.dashboard"))

    db.update_request_status(request_id, status)
    flash(f"Request status updated to {status} successfully", "success")
    return redirect(url_for("admin.dashboard"))


@app.route("/admin/request/<int:request_id>/delete", methods=["POST"], endpoint='admin.delete_request_admin')
def delete_request_admin(request_id):
    if "user_id" not in session or session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))

    db.delete_request(request_id, session["user_id"], admin_override=True)
    flash("Request deleted permanently", "success")
    return redirect(url_for("admin.dashboard"))


@app.errorhandler(404)  # ==> Handle error
def not_found(error):
    return render_template("404.html"), 404

# ==================== RUN ====================
if __name__ == "__main__":
    app.run(debug=True)