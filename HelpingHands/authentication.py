#render_template: takes me to the actual html page
#redirect: sends user to another page
#url_for: find a flask route by its function name
#session: remembers the user is logged in 3amel zy id card mo2aqat

from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash #turns text(pass) into a secure hash before we put it in the database
from database import (email_exists, create_user, get_user_by_email, get_user_by_id)
from functools import wraps

helping_hands = Flask(__name__)
helping_hands.secret_key = "helping-hands-secret-key" #protects the session data


# ===================== authorization part =========================

# access to pages available for logged in users
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return "Please login first."

        return function(*args, **kwargs)
    return wrapper

# access to pages available for logged in users and required role
def role_required(required_role):
    def function_required(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return "Please login first."

            if session["role"] != required_role:
                return "You are not allowed to acces this page."

            return function(*args, **kwargs)
        return wrapper
    return function_required

@helping_hands.route("/") #going to the url to run the home function

def home():
    return render_template("homepage.html", user=session)

# ===================== registration part =========================
@helping_hands.route("/register", methods=["GET", "POST"]) #goes to the register page. get:shows the page. post:sends info to flask

def register(): #request.method is how the brwoser contacts flask by either get or post
    if request.method == "POST": #if the user submitted the info or not
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        role = request.form["role"]

        if email_exists(email):
            return "This email is already registered."

        password_hash = generate_password_hash(password)

        user_id = create_user(
            name,
            email,
            password_hash,
            phone,
            role
        )

        if user_id is None:
            return "This email is already registered."
        
        return "Registration Succesful!"
    
    return render_template("register.html")


# ===================== login part =========================
@helping_hands.route("/login", methods=["GET", "POST"])

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

            return redirect(url_for("home")) #sends user to home()

        return "Invalid email or password."

    return render_template("login.html")


# ===================== logout part =========================
@helping_hands.route("/logout")

def logout():
    session.clear()
    return redirect(url_for("home"))


# ===================== role: Admin =========================
@helping_hands.route("/admin")

@role_required("admin")
def admin(): #admin is the function sent as an argument to login_required
    return "Welcome to the Admin Dashboard!"


if __name__ == "__main__":
    helping_hands.run(debug=True)