from flask import Blueprint, render_template
from database import get_db_connection

# Create a Blueprint for all help-request routes
requests_bp = Blueprint("requests", __name__)

# Display the list of help requests

@requests_bp.route("/requests")
def list_requests():
    conn = get_db_connection()

    requests = conn.execute(
        "SELECT * FROM requests ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "requests/list.html",
        requests=requests
    )




