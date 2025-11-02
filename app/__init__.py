import os
from datetime import datetime

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='tensorflow')

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from db.database import init_db  # Import your DB initializer

db = SQLAlchemy()

def create_app():
    """Application factory function"""
    app = Flask(__name__)

    # Load configuration from config.py
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///DocAI.db')

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
