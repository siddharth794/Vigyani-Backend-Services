import os
import logging
from flask import Flask
from flask_cors import CORS
from .config.config import config_by_name
from .api import register_routes
from .utils.env import load_env

logger = logging.getLogger(__name__)

def create_app(config_name='dev'):
    """Application factory pattern to create Flask app instance"""
    # Load environment variables first
    load_env(config_name)
    
    # Log environment variables before creating app
    logger.info("Environment variables before app creation:")
    logger.info(f"FRONTEND_URL: {os.environ.get('FRONTEND_URL')}")
    logger.info(f"DB_HOST: {os.environ.get('DB_HOST')}")
    logger.info(f"DB_USER: {os.environ.get('DB_USER')}")
    logger.info(f"DB_NAME: {os.environ.get('DB_NAME')}")
    logger.info(f"PORT: {os.environ.get('PORT')}")
    
    app = Flask(__name__)
    
    # Load configuration
    config = config_by_name[config_name]
    app.config.from_object(config)
    
    # Initialize configuration with environment variables
    config.init_app(app)
    
    # Verify configuration after initialization
    logger.info("Verifying configuration after initialization:")
    logger.info(f"DB_HOST: {app.config.get('DB_HOST')}")
    logger.info(f"DB_USER: {app.config.get('DB_USER')}")
    logger.info(f"DB_NAME: {app.config.get('DB_NAME')}")
    logger.info(f"PORT: {app.config.get('PORT')}")
    
    # Initialize extensions
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register blueprints
    register_routes(app)
    
    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return {"error": "Internal server error"}, 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f"Not found error: {str(error)}")
        return {"error": "Not found"}, 404
    
    return app
