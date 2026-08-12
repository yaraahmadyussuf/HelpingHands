from flask import Flask, request, render_template #takes me to the actual html page
from werkzeug.security import generate_password_hash #turns text(pass) into a secure hash before we put it in the database
from database import (email_exists, create_user, get_user_by_email, get_user_by_id)

helping_hands = Flask(__name__)


@helping_hands.route("/") #going to the url to run the home function

def home():
    return render_template("homepage.html")


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

if __name__ == "__main__":
    helping_hands.run(debug=True)