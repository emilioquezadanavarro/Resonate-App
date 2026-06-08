"""
app/__init__.py

Implements the Flask Application Factory Pattern.

This file allows us to create and configure the Flask app instance dynamically,
keeping the global namespace clean and preventing circular import errors.

Responsibilities:
1. Initialize the Flask application.
2. Load environment variables (API Keys).
3. Configure the database URI from DATABASE_URL env var, falling back to SQLite for local dev.
4. Initialize extensions (db.init_app).

"""
from flask import Flask
import os
from .database import db
from dotenv import load_dotenv
from .routes import main

# Load .env file (For API keys!)
load_dotenv()

def create_app():

    # Initialize Flask
    app = Flask(__name__)

    # Configure Database
    database_url = os.environ.get('DATABASE_URL')

    # If DATABASE_URL is set, use it, otherwise use the SQLite database
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    
    # Otherwise use the SQLite database
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, '../resonate.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'a_very_secret_key_for_flashing_messages'

    # Link the database and the app.
    db.init_app(app)

    # Register the Blueprint
    app.register_blueprint(main)

    return app
