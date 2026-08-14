<<<<<<< HEAD
from flask import Flask
from routes.requests import requests_bp
from authentication import auth_bp

# Create the Flask application
app = Flask(__name__)

# Secret key is needed for Flask sessions
app.secret_key = "helping-hands-secret-key"

# Register the authentication Blueprint
app.register_blueprint(auth_bp)

# Register the requests Blueprint
app.register_blueprint(requests_bp)


# Run the application
=======
import os   #==> -- to deal with file path (windows) -- >
import sqlite3
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import database as db

# ==================== INIT ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = "HelpingHands_Secret_Key_Nti"  
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB Limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== CATEGORIES (no categories table in the schema) ====================
CATEGORIES = [
    {"id": 1, "name": "medical", "display_name": "Medical", "description": "Medical and health support"},
    {"id": 2, "name": "social", "display_name": "Social", "description": "Social welfare and community support"},
    {"id": 3, "name": "education", "display_name": "Education", "description": "Scholarships and educational support"},
]


def category_by_id(cat_id):
    try:
        cat_id = int(cat_id)
    except (TypeError, ValueError):
        return None
    return next((c for c in CATEGORIES if c["id"] == cat_id), None) # ==> Generator expression 


def category_by_name(name):
    if not name:
        return None
    return next((c for c in CATEGORIES if c["name"] == name), None)


# ==================== ENRICHMENT HELPERS ====================

# The `requests` table has no user join image_path, or category_id column.
def enrich_case(row):
    if row is None:
        return None
    case = dict(row)

    user = db.get_user_by_id(case.get("user_id"))
    case["user_name"] = user["name"] if user else "Unknown" # ==> Ternary operator

    cat = category_by_name(case.get("category"))
    case["category_display"] = cat["display_name"] if cat else (case.get("category") or "").capitalize() # ==> Ternary operator
    case["category_id"] = cat["id"] if cat else None

    # default avatar whenever this is falsy.
    case["image_path"] = case.get("image_url")

    return case


def enrich_cases(rows):
    return [enrich_case(r) for r in rows] # ==> List Comprehension


#Initialize database tables
db.tables_db()

                #====Routes====#
# ==================== HOME ====================

@app.route('/')
@app.route('/home')
def home():
    return render_template("index.html", categories=CATEGORIES)


# ==================== AUTHENTICATION ====================

                        # (HTTP) 
@app.route("/register", methods=["GET", "POST"])
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
        return redirect(url_for("login"))
    
    return render_template("register.html")  # ==> (GET)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.get_user_by_email(email)
        if user:
            user = dict(user)  # ==> to copy it ane easily edit it 

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))

        
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        session["is_logged_in"] = True
        session["user_name"] = user["name"]

        flash(f"Welcome back, {session['name']}!", "success")
        return redirect(url_for("admin") if session["role"] == "admin" else url_for("dashboard"))

    return render_template("login.html") # ==> (GET)


@app.route("/logout")
def logout():
    session.clear() 
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))


# ==================== DASHBOARD ====================

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    user = db.get_user_by_id(session["user_id"])
    user_requests = enrich_cases(db.get_request_by_user_id(session["user_id"]))
    user_supports = db.get_supports_by_donor(session["user_id"])

    recommended_cases = []
    if session.get("role") == "donor":
        recommended_cases = enrich_cases(db.get_all_requests(status="approved"))[:6]

    return render_template(
        "dashboard.html",
        user=user,
        user_requests=user_requests,
        user_supports=user_supports,
        recommended_cases=recommended_cases,
    )


# ==================== REQUESTS MANAGEMENT ====================

@app.route("/requests")
def view_requests():
    keyword = request.args.get("search", "").strip() # ==> request.args==> Query Parameters
    category_id = request.args.get("category_id", "")
    status_arg = request.args.get("status", "approved")
    status = None if status_arg == "all" else status_arg

    category = category_by_id(category_id)
    category_name = category["name"] if category else None

    if keyword:
     # db.search_requests() has no category parameter, so a keyword search intentionally ignores the category filter.
        rows = db.search_requests(keyword, status=status)
    else:
        rows = db.get_all_requests(status=status, category=category_name)

    cases = enrich_cases(rows)
    return render_template("requests.html", cases=cases, categories=CATEGORIES)


@app.route("/category/<category_name>") # ==> <category_name> ==> Url parameter 
def category_cases(category_name):
    rows = db.get_all_requests(status="approved", category=category_name)
    cases = enrich_cases(rows)

    cat = category_by_name(category_name)
    category_data = cat if cat else {"display_name": category_name.capitalize()}

    return render_template("category_cases.html", category=category_data, cases=cases)


@app.route("/create-request", methods=["GET", "POST"])
def create_request():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    if session.get("role") not in ["requester"]:
        flash("Only requesters can create requests", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description", "")
        category_id = request.form.get("category_id")
        amount = request.form.get("amount_needed")

        category = category_by_id(category_id)
        category_name = category["name"] if category else "general"

        if not title or not amount:
            flash("Please fill all required fields", "danger")
            return render_template("create_request.html", categories=CATEGORIES)

        try:
            amount = float(amount)
            if amount <= 0:
                flash("Amount needed must be greater than 0", "danger")
                return render_template("create_request.html", categories=CATEGORIES)
        except ValueError:
            flash("Invalid amount format", "danger")
            return render_template("create_request.html", categories=CATEGORIES)

        image_url = None
        # Fetch the uploaded image file object from the HTML form using Flask's request module
        image = request.files.get("image") 
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Unsupported image format", "danger")
                return render_template("create_request.html", categories=CATEGORIES)
            
            filename = secure_filename(f"{int(time.time())}_{image.filename}") # From werkzeug.utils to secure files 
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_url = f"/static/images/{filename}"

        db.create_request(
            user_id=session["user_id"],
            title=title,
            description=description,
            amount_needed=amount,
            category=category_name,
            image_url=image_url  
        )
        flash("Request submitted successfully! Awaiting admin approval.", "success")
        return redirect(url_for("dashboard"))

    return render_template("create_request.html", categories=CATEGORIES)

@app.route("/my-requests")
def my_requests():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    cases = enrich_cases(db.get_request_by_user_id(session["user_id"]))
    return render_template("requests.html", cases=cases, categories=CATEGORIES)


@app.route("/request/<int:request_id>")
@app.route("/case/<int:case_id>")
def case_detail(request_id=None, case_id=None):
    cid = case_id if case_id is not None else request_id
    row = db.get_request_by_id(cid)

    if row is None:
        flash("Request not found", "danger")
        return redirect(url_for("view_requests"))

    case = enrich_case(row)
    supports = db.get_supports_for_request(cid)

    has_supported = False
    if "user_id" in session:
        has_supported = db.has_donor_supported(cid, session["user_id"])

    total_collected = db.get_total_pledged(cid)

    return render_template(
        "case_detail.html",
        case=case,
        supports=supports,
        has_supported=has_supported,
        total_collected=total_collected,
    )


@app.route("/case/<int:case_id>/edit", methods=["POST"])
def edit_case(case_id):
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    title = request.form.get("title")
    description = request.form.get("description")
    category_id = request.form.get("category_id")
    amount = request.form.get("amount_needed")

    try:
        amount = float(amount)
        if amount <= 0:
            flash("Amount must be greater than 0", "danger")
            return redirect(url_for("case_detail", case_id=case_id))
    except (TypeError, ValueError):
        flash("Invalid amount", "danger")
        return redirect(url_for("case_detail", case_id=case_id))

    category = category_by_id(category_id)
    fields = {"title": title, "description": description, "amount_needed": amount}

    if category:
        fields["category"] = category["name"]

    image = request.files.get("image")

    if image and image.filename:
        if not allowed_file(image.filename):
            flash("Unsupported image format", "danger")
            return redirect(url_for("case_detail", case_id=case_id))
        
        filename = secure_filename(f"{int(time.time())}_{image.filename}")
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        fields["image_url"] = f"/static/images/{filename}"

    # True if user role is admin, otherwise False
    is_admin = session.get("role") == "admin" 

    success = db.update_request(
        request_id=case_id,
        user_id=session["user_id"],
        admin_override=is_admin,
        **fields
    )

    if not success:
        flash("Unauthorized: You can only edit your own requests", "danger")
        return redirect(url_for("view_requests"))

    flash("Request updated successfully!", "success")
    return redirect(url_for("admin") if is_admin else url_for("case_detail", case_id=case_id))

@app.route("/case/<int:case_id>/delete", methods=["POST"])
def delete_case(case_id):
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    is_admin = session.get("role") == "admin"
    case = db.get_request_by_id(case_id)

    if is_admin :
        success = db.delete_request(case_id, session["user_id"], admin_override=True)
    else:
        success = db.delete_request(case_id, session["user_id"])

    if not success:
        flash("Unauthorized: You can only delete your own requests", "danger")
        return redirect(url_for("view_requests"))

    if case and case.get("image_url"):
        relative_path = case["image_url"].lstrip("/")
        file_path = os.path.join(app.root_path, relative_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)

    flash("Request deleted successfully", "success")
    return redirect(url_for("admin") if is_admin else url_for("view_requests"))


# ==================== DONATION & SUPPORTS ====================

@app.route("/case/<int:case_id>/support", methods=["POST"])
def support_case(case_id):
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    if session.get("role") != "donor":
        flash("Only donors can support requests", "danger")
        return redirect(url_for("case_detail", case_id=case_id))

    message = request.form.get("message", "")
    raw_amount = request.form.get("amount", "").strip()
    
    amount = None
    if raw_amount:
        try:
            amount = float(raw_amount)
            if amount <= 0:
                flash("Amount must be greater than 0", "danger")
                return redirect(url_for("case_detail", case_id=case_id))
        except ValueError:
            flash("Invalid amount", "danger")
            return redirect(url_for("case_detail", case_id=case_id))
        
    support_id = db.create_support(request_id=case_id, donor_id=session["user_id"], message=message,amount=amount)
  
    if support_id is None:
        flash("You have already offered help for this request!", "info")
        return redirect(url_for("case_detail", case_id=case_id))

    flash("Thank you for your support!", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/my-supports")
def my_supports():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    if session.get("role") != "donor":
        flash("Only donors can access this page", "danger")
        return redirect(url_for("dashboard"))

    return redirect(url_for("dashboard"))


# ==================== ADMIN ====================

@app.route("/admin")
def admin():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("dashboard"))

    stats = db.get_admin_stats() # ==> Get site stats (total donations, cases, users)
    users = db.get_all_users()   # ==> # Get all registered users

    all_requests = enrich_cases(db.get_all_requests(status=None))
    pending_requests = [c for c in all_requests if c["status"] == "pending"]

    return render_template(
        "admin.html",
        stats=stats,
        users=users,
        all_requests=all_requests,
        pending_requests=pending_requests,
        categories=CATEGORIES,
    )


@app.route("/admin/request/<int:request_id>/<status>", methods=["POST", "GET"])
def change_request_status(request_id, status):
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("dashboard"))

    if status not in ["approved", "rejected", "pending"]:
        flash("Invalid status", "danger")
        return redirect(url_for("admin"))

    success = db.update_request_status(request_id, status)

    if not success:
        flash("Could not update request status", "danger")
        return redirect(url_for("admin"))

    flash(f"Request status updated to {status} successfully", "success")
    return redirect(url_for("admin"))


@app.errorhandler(404)  # ==> Handle error
def not_found(error):
    return render_template("404.html"), 404

# ==================== RUN ====================
>>>>>>> 6a435556fdc054d1d084c3da212332825e4b5c85
if __name__ == "__main__":
    app.run(debug=True)