from werkzeug.security import generate_password_hash, check_password_hash
from ..utils.db import db_transaction, db_connection
from datetime import datetime

class User:
    def __init__(self, id=None, username=None, email=None, password=None,
                 phone=None, firstname=None, lastname=None, image=None,
                 credit_point=0, created_at=None, updated_at=None, subscription='free', tenant_id=None):
        self.tenant_id = tenant_id
        self.id = id
        self.username = username
        self.email = email
        self._password = password  # Store hashed password
        self.phone = phone
        self.firstname = firstname
        self.lastname = lastname
        self.image = image
        self.credit_point = credit_point
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.subscription = subscription

    @property
    def password(self):
        """Prevent password from being accessed"""
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        """Set password to a hashed password"""
        self._password = generate_password_hash(password)

    def verify_password(self, password):
        """Check if the provided password matches the hash"""
        import logging
        logger = logging.getLogger(__name__)
        if not self._password:
            logger.warning(f"User {self.username} has no password hash stored")
            return False
        try:
            result = check_password_hash(self._password, password)
            logger.debug(f"Password verification for user {self.username}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error verifying password for user {self.username}: {str(e)}")
            return False

    @classmethod
    def get_by_username(cls, username):
        import logging
        logger = logging.getLogger(__name__)
        try:
            with db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM users WHERE username = %s", (username,))
                    user_data = cursor.fetchone()
                    if user_data:
                        logger.debug(f"Found user data for username: {username}")
                        return cls(**user_data)
                    else:
                        logger.debug(f"No user found for username: {username}")
        except Exception as e:
            logger.error(f"Error retrieving user by username {username}: {str(e)}")
        return None

    @classmethod
    def get_by_email(cls, email):
        import logging
        logger = logging.getLogger(__name__)
        try:
            with db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM users WHERE email = %s", (email,))
                    user_data = cursor.fetchone()
                    if user_data:
                        logger.debug(f"Found user data for email: {email}")
                        return cls(**user_data)
                    else:
                        logger.debug(f"No user found for email: {email}")
        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {str(e)}")
        return None

    @classmethod
    def get_by_id(cls, user_id):
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    return cls(**user_data)
        return None

    @classmethod
    def get_by_username_or_email(cls, identifier):
        """Get user by either username or email"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE username = %s OR email = %s
                """, (identifier, identifier))
                user_data = cursor.fetchone()
                if user_data:
                    return cls(**user_data)
        return None

    @classmethod
    def get_by_tenant_id(cls, tenant_id):
        """Get all users by tenant_id"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE tenant_id = %s", (tenant_id,))
                users_data = cursor.fetchall()
                if users_data:
                    return [cls(**user_data) for user_data in users_data]
        return []

    def save(self):
        now = datetime.now()
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                if self.id:
                    # Update existing user
                    cursor.execute("""
                        UPDATE users 
                        SET username = %s, password = %s, credit_point = %s, email = %s,
                            phone = %s, firstname = %s, lastname = %s, image = %s,
                            updated_at = %s, subscription = %s, tenant_id = %s
                        WHERE id = %s
                    """, (
                        self.username, self._password, self.credit_point, self.email,
                        self.phone, self.firstname, self.lastname, self.image,
                        now, self.subscription, self.tenant_id, self.id
                    ))
                else:
                    # Create new user
                    cursor.execute("""
                        INSERT INTO users (
                            username, password, credit_point, email,
                            phone, firstname, lastname, image,
                            created_at, updated_at, subscription, tenant_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.username, self._password, self.credit_point, self.email,
                        self.phone, self.firstname, self.lastname, self.image,
                        now, now, self.subscription, self.tenant_id
                    ))
                    self.id = cursor.lastrowid
                    self.created_at = now
                self.updated_at = now
        return self

    def update_credits(self, amount):
        now = datetime.now()
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET credit_point = credit_point + %s,
                        updated_at = %s
                    WHERE id = %s
                """, (amount, now, self.id))
                self.credit_point += amount
                self.updated_at = now
        return self

    @staticmethod
    def create_tables():
        """Create necessary tables if they don't exist"""
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        password VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        credit_point INT DEFAULT 0,
                        phone VARCHAR(10),
                        firstname VARCHAR(255),
                        lastname VARCHAR(255),
                        image MEDIUMBLOB,
                        subscription VARCHAR(50) DEFAULT 'free',
                        tenant_id VARCHAR(255),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_username (username),
                        INDEX idx_email (email),
                        INDEX idx_tenant_id (tenant_id)
                    )
                """)
