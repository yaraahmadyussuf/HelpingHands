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
if __name__ == "__main__":
    app.run(debug=True)