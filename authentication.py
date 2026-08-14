#render_template: takes me to the actual html page
#redirect: sends user to another page
#url_for: find a flask route by its function name
#session: remembers the user is logged in 3amel zy id card mo2aqat
#flash: shows a one-time message on the next page (used instead of returning raw text,
#       so error/success messages look consistent everywhere - Member 5 fix)

from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash #turns text(pass) into a secure hash before we put it in the database
from database import (email_exists, create_user, get_user_by_email, get_user_by_id, get_all_requests, get_admin_stats)
from functools import wraps

auth_bp = Blueprint("auth", __name__)


# ===================== authorization part =========================

# access to pages available for logged in users
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("auth.login"))

        return function(*args, **kwargs)
    return wrapper

# access to pages available for logged in users and required role
def role_required(required_role):
    def function_required(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please login first.", "warning")
                return redirect(url_for("auth.login"))

            if session["role"] != required_role:
                flash("You are not allowed to access this page.", "danger")
                return redirect(url_for("auth.home"))

            return function(*args, **kwargs)
        return wrapper
    return function_required

@auth_bp.route("/") #going to the url to run the home function

def home():
    # Real numbers from the database, not placeholders - the homepage
    # should feel like the site is actually being used.
    stats = get_admin_stats()
    recent_requests = get_all_requests(status="approved")[:3]

    return render_template(
        "homepage.html",
        user=session,
        stats=stats,
        recent_requests=recent_requests,
    )


# ===================== about us part =========================
@auth_bp.route("/about")

def about():
    return render_template("about.html")

# ===================== registration part =========================
@auth_bp.route("/register", methods=["GET", "POST"]) #goes to the register page. get:shows the page. post:sends info to flask

def register(): #request.method is how the brwoser contacts flask by either get or post
    if request.method == "POST": #if the user submitted the info or not
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        role = request.form["role"]

        # Security: the public registration form only offers "requester" or
        # "donor" (see register.html). Even so, never trust the client -
        # reject anything else server-side so no one can hand-craft an
        # "admin" value in the POST request.
        if role not in ("requester", "donor"):
            flash("Invalid role selected.", "danger")
            return render_template("register.html")

        if email_exists(email):
            flash("This email is already registered.", "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        user_id = create_user(
            name,
            email,
            password_hash,
            phone,
            role
        )

        if user_id is None:
            flash("This email is already registered.", "danger")
            return render_template("register.html")

        flash("Registration successful! You can log in now.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ===================== login part =========================
@auth_bp.route("/login", methods=["GET", "POST"])

def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = get_user_by_email(email) #bagyb el user elly 3ndo this email

        # mn 8eir el session the user will be fogotten b3d el request ma ykhls
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("auth.home")) #sends user to home()

        flash("Invalid email or password.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


# ===================== logout part =========================
@auth_bp.route("/logout")

def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.home"))


# NOTE for the team: the old placeholder "/admin" route that used to live
# here has moved into its own admin.py Blueprint (Member 5's part), so the
# real admin dashboard, user list, and request moderation tools all live
# under /admin/... now instead of a single page that just said "Welcome".
