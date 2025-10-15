import json
import random
from datetime import datetime

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from db.database import init_db  # Import your DB initializer

db = SQLAlchemy()

def create_app():
    """Application factory function"""
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object("config.Config")

    # Initialize database
    db.init_app(app)
    with app.app_context():
        init_db()  # Ensure tables are created at startup

    # Enable CORS
    CORS(app)

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    # Optional: simple health check route
    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    return app
