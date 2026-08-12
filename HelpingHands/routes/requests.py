#request for recieving the info submitted by HTML
# redirect for sending the user to another page after successfully creating the request
# url_for for generating url for another flask route
#render_template takes the HTML file from the template folder and send it to the browser for the  user to see
from flask import Blueprint, render_template, request, redirect, url_for
from database import get_db_connection, get_request_by_id

# Blueprint in Flask is a way to organize related routes into a separate section of your project.
# Create a Blueprint for all help-request routes organizes it separatley from the app.py file

requests_bp = Blueprint("requests", __name__)

# Display the list of help requests
# this route runs when the user requests or visits

@requests_bp.route("/requests")
def list_requests():

    # open a connection with the SQlite database

    conn = get_db_connection()
    #get all help requests from the request table the newest requests are displayed first with created_at

    requests = conn.execute(
        "SELECT * FROM requests ORDER BY created_at DESC"
    ).fetchall()

# closes the database connection after retrieving the data
    conn.close()
#sends the requests data to the HTML page that later uses the variable "requests" to display their help request 
    return render_template(
        "requests/list.html",
        requests=requests
    )
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

        # For now, print the submitted data so we can test that Flask receives it.
        print("Title:", title)
        print("Description:", description)
        print("Category:", category)
        print("Amount Needed:", amount_needed)

        # Return to the requests page after receiving the data.
        return redirect(url_for("requests.list_requests"))

    # If the user is simply opening the page, display the create form.
    return render_template("requests/create.html")

# Display the details of one specific help request.
@requests_bp.route("/requests/<int:request_id>")
def request_details(request_id):

    # Get the request from the database using its ID.
    request = get_request_by_id(request_id)

    # If the request does not exist, show an error message.
    if request is None:
        return "Help request not found.", 404

    # Send the request information to the details HTML page.
    return render_template(
        "requests/details.html",
        request=request
    )

# Display the edit form for a specific help request.
@requests_bp.route("/requests/<int:request_id>/edit")
def edit_request(request_id):

    # Get the request from the database using its ID.
    request = get_request_by_id(request_id)

    # If the request does not exist, show an error message.
    if request is None:
        return "Help request not found.", 404

    # Send the request information to the edit HTML page.
    return render_template(
        "requests/edit.html",
        request=request
    )


