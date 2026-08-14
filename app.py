from flask import Flask, render_template

from authentication import auth_bp
from requests import requests_bp
from admin import admin_bp

# Create the Flask application
app = Flask(__name__)

# Secret key is needed for Flask sessions
# TODO (team): move this to an environment variable before deploying anywhere real
app.secret_key = "helping-hands-secret-key"

# Register the Blueprints - each one owns its own set of routes
app.register_blueprint(auth_bp)
app.register_blueprint(requests_bp)
app.register_blueprint(admin_bp)


# Custom 404 page - keeps the "page not found" screen in the same style
# as the rest of the site instead of Flask's default plain error page.
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# Run the application
if __name__ == "__main__":
    app.run(debug=True)
