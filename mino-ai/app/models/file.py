from datetime import datetime
from ..utils.db import db_transaction, db_connection
class File:
    def __init__(self, id=None, user_id=None, file_name=None, file_path=None, 
                 job_id=None, upload_time=None, processed=False, file_size=None):
        self.id = id
        self.user_id = user_id
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size      # stored in MB
        self.job_id = job_id
        self.upload_time = upload_time or datetime.now()
        self.processed = 1 if processed else 0

    @classmethod
    def get_by_id(cls, file_id):
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_files WHERE id = %s", (file_id,))
                file_data = cursor.fetchone()
                if file_data:
                    return cls(**file_data)
        return None
    
    @classmethod
    def get_by_job_id(cls, job_id):
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_files WHERE job_id = %s", (job_id,))
                file_data = cursor.fetchone()
                if file_data:
                    return cls(**file_data)
        return None

    @classmethod
    def get_user_files(cls, user_id):
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM user_files 
                    WHERE user_id = %s 
                    ORDER BY upload_time DESC
                """, (user_id,))
                files = cursor.fetchall()
                return [cls(**file_data) for file_data in files]

    def save(self):
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                if self.id:
                    # Update existing file
                    cursor.execute("""
                        UPDATE user_files 
                        SET file_name = %s, file_path = %s, job_id = %s, processed = %s, file_size = %s
                        WHERE id = %s
                    """, (
                        self.file_name,
                        self.file_path,
                        self.job_id,
                        1 if self.processed else 0,
                        self.file_size,
                        self.id
                    ))
                else:
                    # Create new file
                    cursor.execute("""
                        INSERT INTO user_files 
                        (user_id, file_name, file_path, job_id, processed, file_size) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        self.user_id,
                        self.file_name,
                        self.file_path,
                        self.job_id,
                        1 if self.processed else 0,
                        self.file_size
                    ))
                    self.id = cursor.lastrowid
        return self

    def delete(self):
        """Delete file record from database"""
        if not self.id:
            raise ValueError("Cannot delete file without ID")
            
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_files WHERE id = %s", (self.id,))
        return True

    @staticmethod
    def create_tables():
        """Create necessary tables if they don't exist"""
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                # Create user_files table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_files (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        file_name VARCHAR(255) NOT NULL,
                        file_path VARCHAR(512) NOT NULL,
                        file_size FLOAT NOT NULL,
                        job_id VARCHAR(64) NOT NULL,
                        processed BOOL DEFAULT FALSE,
                        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        INDEX idx_user_id (user_id),
                        INDEX idx_job_id (job_id),
                    )
                """) 