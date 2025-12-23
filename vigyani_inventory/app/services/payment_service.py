import hashlib
import logging
import requests
from flask import current_app
from ..models.payment import Payment
from ..models.user import User

logger = logging.getLogger(__name__)

def generate_payment_hash(data):
    """
    Generate SHA-512 hash for PayU payment initiation.
    Hash Sequence: key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||SALT
    """
    hash_sequence = (
        f"{data['key']}|{data['txnid']}|{data['amount']}|{data['productinfo']}|"
        f"{data['firstname']}|{data['email']}|"  # Required params
        f"||||||||||"  # Optional params (udf1-udf5 and unused params)
        f"{current_app.config['PAYU_SALT']}"  # Salt at the end
    )
    return hashlib.sha512(hash_sequence.encode()).hexdigest().lower()

def generate_verification_hash(txnid):
    """Generate hash for payment verification"""
    hash_string = f"{current_app.config['PAYU_MERCHANT_KEY']}|verify_payment|{txnid}|{current_app.config['PAYU_SALT']}"
    return hashlib.sha512(hash_string.encode()).hexdigest().lower()

def verify_payment_hash(data):
    """
    Verify hash from PayU response
    Hash Sequence: SALT|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key
    """
    status = data.get('status')
    txnid = data.get('txnid')
    amount = data.get('amount')
    productinfo = data.get('productinfo')
    firstname = data.get('firstname')
    email = data.get('email')
    additional_charges = data.get('additional_charges', '')

    hash_string = (
        f"{current_app.config['PAYU_SALT']}|{status}||||||||||"
        f"{email}|{firstname}|{productinfo}|{amount}|{txnid}|"
        f"{current_app.config['PAYU_MERCHANT_KEY']}"
    )

    if additional_charges:
        hash_string = f"{hash_string}|{additional_charges}"

    calculated_hash = hashlib.sha512(hash_string.encode()).hexdigest().lower()
    return calculated_hash == data.get('hash', '').lower()

def verify_payment(txnid):
    """Verify payment status with PayU"""
    try:
        hash_value = generate_verification_hash(txnid)
        
        payload = {
            "key": current_app.config['PAYU_MERCHANT_KEY'],
            "command": "verify_payment",
            "var1": txnid,
            "hash": hash_value
        }

        response = requests.post(
            current_app.config['PAYU_VERIFY_URL'],
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if response.status_code == 200:
            payu_response = response.json()
            
            if payu_response.get('status') == 1:
                transaction = payu_response.get('transaction_details', {}).get(txnid, {})
                return {
                    "status": "success" if transaction.get('status') == 'success' else "failed",
                    "transaction": transaction
                }
            
            return {
                "status": "error",
                "message": payu_response.get('msg', 'Unknown error occurred')
            }
        
        return {
            "status": "error",
            "message": "Failed to connect to PayU services"
        }

    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return {
            "status": "error",
            "message": "Internal server error during payment verification"
        }

def process_payment_response(payment_data):
    """Process payment response from PayU"""
    try:
        if not verify_payment_hash(payment_data):
            logger.error("Payment hash verification failed")
            return False

        # Create payment record
        payment = Payment(
            txnid=payment_data.get('txnid'),
            status=payment_data.get('status'),
            amount=float(payment_data.get('amount')),
            email=payment_data.get('email'),
            payment_data=payment_data
        )
        payment.save()

        # If payment is successful, update user credits
        if payment_data.get('status') == 'success':
            user = User.get_by_email(payment_data.get('email'))
            if user:
                user.update_credits(float(payment_data.get('amount')))
                logger.info(f"Credits updated for user: {user.email}")
            else:
                logger.error(f"User not found for email: {payment_data.get('email')}")

        return True

    except Exception as e:
        logger.error(f"Error processing payment response: {str(e)}")
        return False 