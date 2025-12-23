import pymysql
import logging
from contextlib import contextmanager
from flask import current_app, g
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self._connection = None

    def get_connection(self):
        """Get a database connection."""
        if self._connection is None or not self._connection.open:
            try:
                # Get configuration from current_app
                config = current_app.config
                
                # Log the configuration being used
                logger.info("Attempting database connection with configuration:")
                logger.info(f"Host: {config.get('DB_HOST')}")
                logger.info(f"User: {config.get('DB_USER')}")
                logger.info(f"Database: {config.get('DB_NAME')}")
                
                # Verify required configuration
                required_config = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
                missing_config = [key for key in required_config if not config.get(key)]
                if missing_config:
                    raise ValueError(f"Missing required database configuration: {', '.join(missing_config)}")
                
                self._connection = pymysql.connect(
                    host=config['DB_HOST'],
                    user=config['DB_USER'],
                    password=config['DB_PASSWORD'],
                    db=config['DB_NAME'],
                    charset='utf8mb4',
                    cursorclass=DictCursor,
                    autocommit=False,
                    connect_timeout=5
                )
                logger.info(f"Successfully connected to database at {config['DB_HOST']}")
            except Exception as e:
                logger.error(f"Error connecting to database: {str(e)}")
                logger.error(f"Connection attempted with host: {config.get('DB_HOST')}, "
                           f"user: {config.get('DB_USER')}, "
                           f"database: {config.get('DB_NAME')}")
                raise

        return self._connection

    def release_connection(self):
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.debug("Closed database connection")

db_manager = DatabaseManager()

@contextmanager
def db_transaction():
    """Context manager for database transactions"""
    conn = None
    try:
        conn = db_manager.get_connection()
        yield conn
        conn.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {str(e)}")
        raise
    finally:
        db_manager.release_connection()

@contextmanager
def db_connection():
    """Context manager for database connections (without transaction)"""
    try:
        conn = db_manager.get_connection()
        yield conn
    finally:
        db_manager.release_connection() 