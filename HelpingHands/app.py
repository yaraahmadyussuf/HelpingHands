from flask import Flask
from routes.requests import requests_bp

# Create the Flask application
app = Flask(__name__)

# Register the requests Blueprint
app.register_blueprint(requests_bp)

# Run the application
if __name__ == "__main__":
    app.run(debug=True)