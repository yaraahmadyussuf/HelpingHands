# request for receiving the info submitted by HTML
# redirect for sending the user to another page after successfully creating the request
# url_for for generating url for another flask route
# render_template takes the HTML file from the template folder and sends it
# to the browser for the user to see

from flask import Blueprint, render_template, request, redirect, url_for
from database import get_db_connection, get_request_by_id


# Blueprint in Flask is a way to organize related routes
# into a separate section of the project.

# Create a Blueprint for all help-request routes.
# This organizes it separately from the app.py file.

requests_bp = Blueprint("requests", __name__)


# ---------------------------------------------------------
# DISPLAY AND SEARCH HELP REQUESTS
# ---------------------------------------------------------

# Display all help requests and allow the user to search for requests.

@requests_bp.route("/requests")
def list_requests():

    # Get the search text from the URL.
    # If there is no search text, use an empty string.
    search = request.args.get("search", "").strip()

    # Open a connection with the SQLite database.
    conn = get_db_connection()

    # If the user entered a search term, search the requests.
    if search:

        # Add % so the search term can appear anywhere in the text.
        search_pattern = f"%{search}%"

        # Search the title, description, and category.
        requests = conn.execute(
            """
            SELECT * FROM requests
            WHERE title LIKE ?
               OR description LIKE ?
               OR category LIKE ?
            ORDER BY created_at DESC
            """,
            (search_pattern, search_pattern, search_pattern)
        ).fetchall()

    # If there is no search term, display all requests.
    else:

        requests = conn.execute(
            """
            SELECT * FROM requests
            ORDER BY created_at DESC
            """
        ).fetchall()

    # Close the database connection.
    conn.close()

    # Send the requests and search text to the HTML page.
    return render_template(
        "requests/list.html",
        requests=requests,
        search=search
    )


# ---------------------------------------------------------
# CREATE A HELP REQUEST
# ---------------------------------------------------------

# Display the create request form and handle submitted request data.

@requests_bp.route("/requests/create", methods=["GET", "POST"])
def create_request():

    # If the user submitted the form, process the submitted data.
    if request.method == "POST":

        # Get the values entered by the user from the form.
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        amount_needed = request.form["amount_needed"]

        # For now, print the submitted data so we can test
        # that Flask receives it.
        print("Title:", title)
        print("Description:", description)
        print("Category:", category)
        print("Amount Needed:", amount_needed)

        # Return to the requests page after receiving the data.
        return redirect(url_for("requests.list_requests"))

    # If the user is simply opening the page,
    # display the create form.
    return render_template("requests/create.html")


# ---------------------------------------------------------
# DISPLAY REQUEST DETAILS
# ---------------------------------------------------------

# Display the details of one specific help request.

@requests_bp.route("/requests/<int:request_id>")
def request_details(request_id):

    # Get the request from the database using its ID.
    request_data = get_request_by_id(request_id)

    # If the request does not exist, show an error message.
    if request_data is None:
        return "Help request not found.", 404

    # Send the request information to the details HTML page.
    return render_template(
        "requests/details.html",
        request=request_data
    )


# ---------------------------------------------------------
# EDIT A HELP REQUEST
# ---------------------------------------------------------

# Display the edit form for a specific help request.

@requests_bp.route("/requests/<int:request_id>/edit")
def edit_request(request_id):

    # Get the request from the database using its ID.
    request_data = get_request_by_id(request_id)

    # If the request does not exist, show an error message.
    if request_data is None:
        return "Help request not found.", 404

    # Send the request information to the edit HTML page.
    return render_template(
        "requests/edit.html",
        request=request_data
    )


# ---------------------------------------------------------
# DELETE A HELP REQUEST
# ---------------------------------------------------------

# Handle the deletion of a specific help request.

@requests_bp.route(
    "/requests/<int:request_id>/delete",
    methods=["POST"]
)
def delete_request(request_id):

    # For now, we only confirm that Flask received
    # the delete request.
    print("Delete request received for ID:", request_id)

    # Return to the list of help requests.
    return redirect(url_for("requests.list_requests"))