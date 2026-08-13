# request for receiving the info submitted by HTML
# redirect for sending the user to another page after successfully creating the request
# url_for for generating url for another flask route
# render_template takes the HTML file from the template folder and sends it
# to the browser for the user to see

from flask import Blueprint, render_template, request, redirect, url_for
# to have defined functions from both files                                                                #to avoid conflict
from database import get_db_connection, get_request_by_id, update_request, delete_request, create_request as create_request_db, get_request_by_user_id, create_support, get_supports_for_request
from authentication import login_required, role_required


# Blueprint in Flask is a way to organize related routes
# into a separate section of the project.

# Create a Blueprint for all help-request routes.
# This organizes it separately from the app.py file.

requests_bp = Blueprint("requests", __name__)


# Display all help requests and allow the user to search and filter requests by category

@requests_bp.route("/requests")
def list_requests():

    # Get the search text from the URL.
    # If there is no search text, use an empty string.
    search = request.args.get("search", "").strip()

    # Get the selected category from the URL.
    # If no category was selected, show all categories.
    category = request.args.get("category", "all")

    # Open a connection with the SQLite database.
    conn = get_db_connection()

    # If the user entered a search AND selected a category,
    # apply both filters.
    if search and category != "all":

        search_pattern = f"%{search}%"

        requests = conn.execute(
            """
            SELECT * FROM requests
            WHERE
                (title LIKE ?
                OR description LIKE ?
                OR category LIKE ?)
                AND category = ?
            ORDER BY created_at DESC
            """,
            (
                search_pattern,
                search_pattern,
                search_pattern,
                category
            )
        ).fetchall()

    # If the user only entered a search.
    elif search:

        search_pattern = f"%{search}%"

        requests = conn.execute(
            """
            SELECT * FROM requests
            WHERE title LIKE ?
               OR description LIKE ?
               OR category LIKE ?
            ORDER BY created_at DESC
            """,
            (
                search_pattern,
                search_pattern,
                search_pattern
            )
        ).fetchall()

    # If the user only selected a category.
    elif category != "all":

        requests = conn.execute(
            """
            SELECT * FROM requests
            WHERE category = ?
            ORDER BY created_at DESC
            """,
            (category,)
        ).fetchall()

    # If the user did not search or filter,
    # display all requests.
    else:

        requests = conn.execute(
            """
            SELECT * FROM requests
            ORDER BY created_at DESC
            """
        ).fetchall()

    # Close the database connection.
    conn.close()

    # Send the requests, search text, and selected category
    # to the HTML page.
    return render_template(
        "requests/list.html",
        requests=requests,
        search=search,
        category=category
    )


# CREATE A HELP REQUEST


# Display the create request form and handle submitted request data.


@requests_bp.route("/requests/create", methods=["GET", "POST"])
def create_request():

    # If the user submitted the form, process the submitted data.
    if request.method == "POST":

        # Get the values entered by the user from the form.
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        category = request.form["category"]
        amount_needed = request.form["amount_needed"]

        # Make sure the title is not empty.
        if not title:
            return "Title is required.", 400

        # Make sure the description is not empty.
        if not description:
            return "Description is required.", 400

        # Convert the amount from text to a number.
        try:
            amount_needed = float(amount_needed)
        except ValueError:
            return "Amount needed must be a number.", 400

        # Make sure the amount is greater than zero.
        if amount_needed <= 0:
            return "Amount needed must be greater than 0.", 400

        # TEMPORARY:
        # We will replace this with session["user_id"]
        # when authentication is connected.
        user_id = 1

        # Save the request in the database.
        request_id = create_request_db(
            user_id,
            title,
            description,
            amount_needed,
            category
        )

        # Send the user to the details page after creating the request.
        return redirect(
            url_for(
                "requests.request_details",
                request_id=request_id
            )
        )

    # If the user is simply opening the page,
    # display the create form.
    return render_template("requests/create.html")


# Display the details of one specific help request.
@requests_bp.route("/requests/<int:request_id>")
def request_details(request_id):

    # Get the request from the database using its ID.
    request_data = get_request_by_id(request_id)

    # If the request does not exist, show an error message.
    if request_data is None:
        return "Help request not found.", 404

    # Get the donors who offered to help with this request.
    supporters = get_supports_for_request(request_id)

    # Send the request and supporters to the HTML page.
    return render_template(
        "requests/details.html",
        request=request_data,
        supporters=supporters
    )

# Allow a donor to offer help for a specific request.
@requests_bp.route(
    "/requests/<int:request_id>/support",
    methods=["POST"]
)
def support_request(request_id):

    # Check that the request exists.
    request_data = get_request_by_id(request_id)

    if request_data is None:
        return "Help request not found.", 404

    # TEMPORARY:
    # We will replace this with session["user_id"]
    # when authentication is connected.
    donor_id = 2

    # Get the optional message from the donor.
    message = request.form.get("message", "").strip()

    # Create the support record in the database.
    support_id = create_support(
        request_id,
        donor_id,
        message
    )

    # If the donor already supported this request.
    if support_id is None:
        return "You have already offered to help with this request.", 400

    # Return to the request details page.
    return redirect(
        url_for(
            "requests.request_details",
            request_id=request_id
        )
    )

# Display all help requests created by the current user.
@requests_bp.route("/my-requests")
def my_requests():

    # TEMPORARY:
    # We will replace this with session["user_id"]
    # when authentication is connected.
    user_id = 1

    # Get all requests created by this user.
    requests = get_request_by_user_id(user_id)

    # Send the user's requests to the HTML page.
    return render_template(
        "requests/my_requests.html",
        requests=requests
    )



# Display the edit form for a specific help request.


@requests_bp.route("/requests/<int:request_id>/edit", methods=["GET", "POST"])
# the useer has to be logged in to edit

@login_required
@role_required("requester")

def edit_request(request_id):

    # Get the request from the database using its ID.
    request_data = get_request_by_id(request_id)

    # If the request does not exist, show an error message.
    if request_data is None:
        return "Help request not found.", 404

    # If the user submitted the edit form.
    if request.method == "POST":

        # Get the updated values from the HTML form.
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        amount_needed = request.form["amount_needed"]

        # Make sure the amount is greater than zero.
        if float(amount_needed) <= 0:
            return "Amount needed must be greater than 0.", 400

        # For now, use the request owner's ID.
        # We will replace this with session["user_id"]
        # when authentication is connected.

        session["user_id"]

        # Update the request in the database.
        updated = update_request(
            request_id,
            user_id,
            title=title,
            description=description,
            category=category,
            amount_needed=float(amount_needed)
        )

        # If the update was not successful.
        if not updated:
            return "You are not allowed to edit this request.", 403

        # Return to the request details page after saving.
        return redirect(
            url_for(
                "requests.request_details",
                request_id=request_id
            )
        )

    # If the user is simply opening the page,
    # display the edit form.
    return render_template(
        "requests/edit.html",
        request=request_data
    )




# Handle the deletion of a specific help request.

@requests_bp.route(
    "/requests/<int:request_id>/delete",
    methods=["POST"]
)
def delete_request_route(request_id):

    # Get the request from the database.
    request_data = get_request_by_id(request_id)

    # If the request does not exist, show an error.
    if request_data is None:
        return "Help request not found.", 404

    # For now, use the request owner's ID.
    # We will replace this with session["user_id"]
    # when authentication is connected.
    user_id = request_data["user_id"]

    # Delete the request from the database.
    deleted = delete_request(
        request_id,
        user_id
    )

    # If the request could not be deleted.
    if not deleted:
        return "You are not allowed to delete this request.", 403

    # Return to the requests list after deletion.
    return redirect(
        url_for("requests.list_requests")
    )