import os
from flask import Flask
from flask_cors import CORS
from .config import config_by_name
from .api import register_routes
from .services.chat_service import start_chat_service
from .utils.env import load_env
import logging

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup logging configuration, preventing duplicate handlers"""
    root_logger = logging.getLogger()
    
    # Only setup if handlers don't already exist to prevent duplicates
    if not root_logger.handlers:
        root_logger.setLevel(logging.DEBUG)  # Set to DEBUG to see all logs
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

def create_app(config_name='dev'):
    """Application factory pattern to create Flask app instance"""
    setup_logging()
    # Load environment variables first
    load_env(config_name)

    # Log environment variables before creating app
    logger.info("Environment variables before app creation:")
    logger.info(f"DB_HOST: {os.environ.get('DB_HOST')}")
    logger.info(f"DB_USER: {os.environ.get('DB_USER')}")
    logger.info(f"DB_NAME: {os.environ.get('DB_NAME')}")
    logger.info(f"PORT: {os.environ.get('PORT')}")

    app = Flask(__name__)
    
    # Load configuration
    config = config_by_name[config_name]
    app.config.from_object(config)

    config.init_app(app)

    # Initialize CORS
    
    
    # Start the chat service
    start_chat_service(app.config['GOOGLE_API_KEY'])
    logger.info("Chat service initialized with API key.")
    
    # Register blueprints
    register_routes(app)
    
    CORS(app, resources={
        r"/*": { "origins": [ "*" ] }
    })

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
