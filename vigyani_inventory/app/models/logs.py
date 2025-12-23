from ..utils.db import db_transaction, db_connection

class Logs:
    def __init__(self, id=None, txnid=None,status=None,amount = None,
                   created_at=None):
        self.id = id
        self.txnid = txnid
        self.status = status
        self.amount = float(amount) if amount is not None else 0
        self.created_at = created_at
    

    def save(self):
        """Insert or update payment log based on txnid"""
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO payment_logs (txnid, status, amount, created_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        amount = VALUES(amount),
                        created_at = VALUES(created_at)
                """, (
                    self.txnid,
                    self.status,
                    self.amount,
                    self.created_at
                ))
        return self


    @classmethod
    def get_all_logs(cls):
        """Get all payment logs"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""SELECT * FROM payment_logs""")
                logs = cursor.fetchall()
                return [cls(**log) for log in logs]
    
    # @classmethod
    # def get_log_by_email(cls,email):
    #     """Get payment logs through email id"""
    #     with db_connection() as conn:
    #         with conn.cursor() as cursor:
    #             cursor.execute("""SELECT * FROM payment_logs WHERE email = %s""",(email,))
    #             logs = cursor.fetchall()
    #             return [cls(**log) for log in logs]

    @classmethod
    def get_log_by_status(cls,status):
        """Get Payment logs through status"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""SELECT * FROM payment_logs WHERE status = %s""",(status,))
                logs = cursor.fetchall()
                return [cls(**log) for log in logs]
            
    @classmethod
    def get_log_by_txnid(cls,txnid):
        """Get Payment log of a particular transaction id"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""SELECT * FROM payment_logs WHERE txnid = %s""",(txnid,))
                log = cursor.fetchone()
                return cls(**log) if log else None
    @staticmethod
    def create_tables():
        """Create necessary tables if they don't exist"""
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payment_logs (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        txnid VARCHAR(255) UNIQUE NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                """)
                        