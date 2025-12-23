import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """Base configuration."""

    # Default values or None ( will be set in init_app)
    SECRET_KEY = None
    DB_HOST = None
    DB_USER = None
    DB_PASSWORD = None
    DB_NAME = None
    PORT = 5000
    REDIS_HOST = None
    REDIS_PORT = 6379
    REDIS_USERNAME = None
    REDIS_PASSWORD = None
    AWS_ACCESS_KEY_ID = None
    AWS_SECRET_ACCESS_KEY = None
    AWS_REGION = None
    S3_UPLOAD_BUCKET = None
    S3_SUMMARY_BUCKET = None
    GOOGLE_API_KEY = None

    @classmethod
    def init_app(cls, app):
        """Initialize the application with the given configuration"""
        cls.SECRET_KEY = os.environ.get('SECRET_KEY')
        cls.DB_HOST = os.environ.get('DB_HOST')
        cls.DB_USER = os.environ.get('DB_USER')
        cls.DB_PASSWORD = os.environ.get('DB_PASSWORD')
        cls.DB_NAME = os.environ.get('DB_NAME')
        cls.PORT = os.environ.get('PORT', cls.PORT)
        cls.REDIS_HOST = os.environ.get('REDIS_HOST')
        cls.REDIS_PORT = os.environ.get('REDIS_PORT', cls.REDIS_PORT)
        cls.REDIS_USERNAME = os.environ.get('REDIS_USERNAME')
        cls.REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
        cls.AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
        cls.AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        cls.AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-2')
        cls.S3_UPLOAD_BUCKET = os.environ.get('S3_UPLOAD_BUCKET')
        cls.S3_SUMMARY_BUCKET = os.environ.get('S3_SUMMARY_BUCKET')
        cls.GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

        # Log configuration values
        logger.info("Configuration initialized with values:")
        logger.info(f"DB_HOST: {cls.DB_HOST}")
        logger.info(f"DB_USER: {cls.DB_USER}")
        logger.info(f"DB_NAME: {cls.DB_NAME}")
        logger.info(f"PORT: {cls.PORT}")
        logger.info(f"REDIS_HOST: {cls.REDIS_HOST}")
        logger.info(f"REDIS_PORT: {cls.REDIS_PORT}")
        logger.info(f"REDIS_USERNAME: {cls.REDIS_USERNAME}")

        for key in dir(cls):
            if not key.startswith('_'):
                app.config[key] = getattr(cls, key)

        required_config = [
            'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'PORT',
            'REDIS_HOST', 'REDIS_PORT', 'REDIS_USERNAME', 'REDIS_PASSWORD',
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION',
            'S3_UPLOAD_BUCKET', 'S3_SUMMARY_BUCKET', 'GOOGLE_API_KEY'
        ]
        missing_configs = [key for key in required_config if getattr(cls, key) is None]
        if missing_configs:
            logger.error(f"Missing required configuration keys: {', '.join(missing_configs)}")
            raise ValueError(f"Missing required configuration keys: {', '.join(missing_configs)}")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'dev'
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        logging.getLogger().setLevel(logging.DEBUG)

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'prod'

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}
