import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_env(env='dev'):
    """Load environment variables from .env file based on environment
    
    Args:
        env (str): Environment name ('dev' or 'prod')
    """
    env_file = f'.env.{env}'
    env_path = Path(env_file)
    
    logger.info(f"Attempting to load environment file: {env_file}")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # First try to load from current directory
    if env_path.exists():
        logger.info(f"Found environment file at: {env_path.absolute()}")
        load_dotenv(env_path, override=True)
        logger.info("Environment variables loaded successfully")
    else:
        # Try to find env file in parent directories
        parent_path = env_path.parent
        while parent_path != parent_path.parent:  # Stop at root
            parent_env_path = parent_path / env_file
            logger.debug(f"Checking path: {parent_env_path.absolute()}")
            if parent_env_path.exists():
                logger.info(f"Found environment file at: {parent_env_path.absolute()}")
                load_dotenv(parent_env_path, override=True)
                logger.info("Environment variables loaded successfully")
                break
            parent_path = parent_path.parent
        else:
            logger.warning(f"No {env_file} file found. Using system environment variables.")
    
    # Verify required environment variables
    required_vars = [
        'SECRET_KEY',
        'DB_HOST',
        'DB_USER',
        'DB_PASSWORD',
        'DB_NAME',
        'RAZORPAY_KEY_ID',
        'RAZORPAY_KEY_SECRET',
        'FRONTEND_URL',
        'PORT',
        'SENDER_EMAIL',
        'SENDER_PASSWORD'
    ]
    
    # Log all environment variables (excluding sensitive ones)
    logger.info("Current environment variables:")
    for var in required_vars:
        if var not in ['SECRET_KEY', 'DB_PASSWORD', 'RAZORPAY_KEY_SECRET', 'SENDER_PASSWORD']:
            value = os.environ.get(var)
            logger.info(f"{var}: {value}")
            if value is None:
                logger.warning(f"Missing environment variable: {var}")
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}") 