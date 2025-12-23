from datetime import datetime
from ..utils.db import db_transaction, db_connection

class Payments:
    # Payment status constants
    STATUS_INITIATED = 'initiated'
    STATUS_CREATED = 'created'
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    # Payment provider constants
    PROVIDER_RAZORPAY = 'razorpay'
    PROVIDER_PAYU = 'payu'

    def __init__(self, id=None, user_id=None, order_id=None, payment_id=None, amount=None,
                 currency=None, receipt=None, notes=None, status=None,
                 provider=None, provider_payment_id=None, provider_order_id=None,
                 provider_signature=None, created_at=None, updated_at=None):
        self.id = id
        self.user_id = user_id
        self.order_id = order_id  # Our internal order ID
        self.payment_id = payment_id  # Our internal payment ID
        self.amount = amount
        self.currency = currency
        self.receipt = receipt
        self.notes = notes
        self.status = status or self.STATUS_INITIATED
        self.provider = provider
        self.provider_payment_id = provider_payment_id  # razorpay_payment_id or mihpayid
        self.provider_order_id = provider_order_id  # razorpay_order_id or txnid
        self.provider_signature = provider_signature  # For signature verification
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def save(self):
        """Save payment to database"""
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                if self.id:
                    # Update existing payment
                    cursor.execute("""
                        UPDATE payments 
                        SET user_id = %s, order_id = %s,
                            amount = %s, currency = %s, receipt = %s,
                            notes = %s, status = %s, provider = %s,
                            provider_payment_id = %s, provider_order_id = %s,
                            provider_signature = %s, updated_at = %s
                        WHERE id = %s
                    """, (
                        self.user_id, self.order_id,
                        self.amount, self.currency, self.receipt,
                        self.notes, self.status, self.provider,
                        self.provider_payment_id, self.provider_order_id,
                        self.provider_signature, datetime.now(),
                        self.id
                    ))
                else:
                    # Create new payment
                    cursor.execute("""
                        INSERT INTO payments (
                            user_id, order_id, amount,
                            currency, receipt, notes, status, provider,
                            provider_payment_id, provider_order_id,
                            provider_signature, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.user_id, self.order_id,
                        self.amount, self.currency, self.receipt,
                        self.notes, self.status, self.provider,
                        self.provider_payment_id, self.provider_order_id,
                        self.provider_signature, self.created_at, self.updated_at
                    ))
                    self.id = cursor.lastrowid
        return self

    @classmethod
    def get_by_id(cls, payment_id):
        """Get payment by ID"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
                payment_data = cursor.fetchone()
                if payment_data:
                    return cls(**payment_data)
        return None

    @classmethod
    def get_latest_by_user_id(cls, user_id):
        """Fetch the latest payment details for a user"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM payments WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (user_id,)
                )
                payment = cursor.fetchone()
                return cls(**payment) if payment else None

    @classmethod
    def get_by_order_id(cls, order_id):
        """Get payment by order ID"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM payments 
                    WHERE order_id = %s
                """, (order_id,))
                payment_data = cursor.fetchone()
                if payment_data:
                    return cls(**payment_data)
        return None

    @classmethod
    def get_by_provider_order_id(cls, provider_order_id):
        """Get payment by provider's order ID"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM payments WHERE provider_order_id = %s", (provider_order_id,))
                payment_data = cursor.fetchone()
                if payment_data:
                    return cls(**payment_data)
        return None

    @classmethod
    def get_by_provider_payment_id(cls, provider_payment_id):
        """Get payment by Razorpay payment ID"""
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM payments WHERE provider_payment_id = %s", (provider_payment_id,))
                payment_data = cursor.fetchone()
                if payment_data:
                    return cls(**payment_data)
        return None

    @classmethod
    def get_user_payments(cls, user_id, status=None, provider=None, limit=10):
        """Get all payments for a user with optional filters"""
        query = "SELECT * FROM payments WHERE user_id = %s"
        params = [user_id]

        if status:
            query += " AND status = %s"
            params.append(status)
        if provider:
            query += " AND provider = %s"
            params.append(provider)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                payments = cursor.fetchall()
                return [cls(**payment) for payment in payments]

    @staticmethod
    def create_tables():
        """Create necessary tables if they don't exist"""
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        order_id VARCHAR(255) NOT NULL UNIQUE,
                        amount INT NOT NULL,
                        currency VARCHAR(10) NOT NULL,
                        receipt VARCHAR(255),
                        notes TEXT,
                        status VARCHAR(50) NOT NULL,
                        provider VARCHAR(50) NOT NULL,
                        provider_payment_id VARCHAR(255),
                        provider_order_id VARCHAR(255),
                        provider_signature VARCHAR(512),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_user_id (user_id),
                        INDEX idx_order_id (order_id),
                        INDEX idx_provider_order_id (provider_order_id),
                        INDEX idx_status (status),
                        INDEX idx_provider (provider),
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """) 