import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Load .env before suppressing TF noise, so env vars are available immediately
load_dotenv(find_dotenv(usecwd=False), override=False)

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import warnings
import logging

# Suppress ALL TensorFlow & Keras deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module='tensorflow')
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", module='tf_keras')
logging.getLogger("tensorflow").setLevel(logging.ERROR)

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from db.database import init_db  # Import your DB initializer

db = SQLAlchemy()

def create_app():
    """Application factory function"""
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-insecure-fallback')

    # Load configuration from database.py single source of truth
    from db.database import DB_URI
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI

    # Initialize database
    db.init_app(app)
    with app.app_context():
        init_db()  # Ensure tables are created at startup

    # Enable CORS
    CORS(app)

    # Initialize Swagger
    from flasgger import Swagger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,  # all in
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "DocAI Backend API",
            "description": "API endpoints for DocAI LLM integration and semantic search pipeline",
            "version": "1.0.0"
        }
    }
    Swagger(app, config=swagger_config, template=swagger_template)

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    # Optional: simple health check route
    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    return app

