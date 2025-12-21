"""
run.py

The entry point for the Resonate Flask application.

This script initializes the app using the factory pattern and starts the
development server.

Usage:
    Run manually via terminal: `python run.py`
    The server will start at http://127.0.0.1:5000/

"""

from app import create_app

# Create app instance
app = create_app()

# Standard Flask Run Block
if __name__ == "__main__":

    # Run the Flask development server

    # debug=True: Enables auto-reload on code changes and detailed error pages

    app.run(host="127.0.0.1", port=5000, debug=True)
