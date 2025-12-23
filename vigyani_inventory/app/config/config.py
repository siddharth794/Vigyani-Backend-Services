import os
import logging
# from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Base configuration."""
    # Default values or None (will be set in init_app)
    SECRET_KEY = None
    PORT = 5000  # Default port
    RAZORPAY_KEY_ID = None
    RAZORPAY_KEY_SECRET = None
    DB_HOST = None
    DB_USER = None
    DB_PASSWORD = None
    DB_NAME = None
    FRONTEND_URL = None
    PAYMENT_SUCCESS_URL = None
    PAYMENT_FAILURE_URL = None
    SENDER_EMAIL = None
    SENDER_PASSWORD = None

    @classmethod
    def init_app(cls, app):
        """Initialize configuration with environment variables."""
        # Read environment variables
        cls.SECRET_KEY = os.environ.get('SECRET_KEY')
        cls.PORT = int(os.environ.get('PORT', cls.PORT))
        cls.RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
        cls.RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
        cls.DB_HOST = os.environ.get('DB_HOST')
        cls.DB_USER = os.environ.get('DB_USER')
        cls.DB_PASSWORD = os.environ.get('DB_PASSWORD')
        cls.DB_NAME = os.environ.get('DB_NAME')
        cls.FRONTEND_URL = os.environ.get('FRONTEND_URL')
        cls.SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
        cls.SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
        
        # Set derived URLs
        cls.PAYMENT_SUCCESS_URL = f"{cls.FRONTEND_URL}/payment_response" if cls.FRONTEND_URL else None
        cls.PAYMENT_FAILURE_URL = f"{cls.FRONTEND_URL}/payment_response" if cls.FRONTEND_URL else None

        # Log configuration values
        logger.info("Configuration initialized with values:")
        logger.info(f"DB_HOST: {cls.DB_HOST}")
        logger.info(f"DB_USER: {cls.DB_USER}")
        logger.info(f"DB_NAME: {cls.DB_NAME}")
        logger.info(f"PORT: {cls.PORT}")

        # Update app config with class variables
        for key in dir(cls):
            if not key.startswith('_'):
                app.config[key] = getattr(cls, key)

        # Validate required configurations
        required_configs = ['SECRET_KEY', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        missing_configs = [key for key in required_configs if getattr(cls, key) is None]
        if missing_configs:
            logger.error(f"Missing required configurations: {', '.join(missing_configs)}")
            raise ValueError(f"Missing required configurations: {', '.join(missing_configs)}")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'dev'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'prod'

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}