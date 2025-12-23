from flask import Blueprint, request, jsonify, current_app
from razorpay import Client
import json
import logging
from ..utils.auth import token_required
from ..utils.db import db_transaction
from ..services.email_service import handle_email_notification
from ..models.users import User
from ..models.payment import Payments
from ..models.logs import Logs
from datetime import datetime

logger = logging.getLogger(__name__)
razorpay_bp = Blueprint('razorpay', __name__)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_razorpay_client():
    """Get Razorpay client instance"""
    logger.info(f"Getting Razorpay client with key_id: {current_app.config['RAZORPAY_KEY_ID']}")
    
    key_id = current_app.config['RAZORPAY_KEY_ID']
    key_secret = current_app.config['RAZORPAY_KEY_SECRET']

    return Client(auth=(key_id, key_secret))

@razorpay_bp.route('/create-order', methods=['POST'])
@token_required
def create_order(user_id):
    """Create a new Razorpay order"""
    try:
        data = request.get_json()
        amount = data.get('amount')
        currency = data.get('currency', 'INR')
        receipt = data.get('receipt')
        notes = data.get('notes', {})
        
        if not all([amount, receipt]):
            return jsonify({'error': 'Amount and receipt are required'}), 400

        # Validate user
        user = User.get_by_id(user_id)
        user.subscription = notes.get('tierName')
        user.save()
        logger.info(f"User subscription updated: {user.subscription}")

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Create Razorpay Order
        razorpay_client = get_razorpay_client()
        order_data = {
            'amount': amount,
            'currency': currency,
            'receipt': receipt,
            'notes': notes
        }
        
        order = razorpay_client.order.create(data=order_data)

        # log_entry = Logs(
        #     txnid=order['id'],  # Razorpay order_id
        #     status=Payments.STATUS_INITIATED,
        #     amount=amount / 100,
        #     created_at=datetime.now()
        # )
        # log_entry.save()
        
        # Store order in database
        payment = Payments(
            user_id=user_id,
            order_id=f"RZP_{user_id}_{int(datetime.now().timestamp())}",
            amount=amount / 100,    # store in rupees
            currency=currency,
            receipt=receipt,
            notes=json.dumps(notes),
            status=Payments.STATUS_CREATED,
            provider=Payments.PROVIDER_RAZORPAY,
            provider_order_id=order['id']
        )
        payment.save()

        logger.info(f"Created Razorpay order: {order['id']} for user: {1}")
        return jsonify({
            'order_id': order['id'],
            'amount': amount,
            'currency': currency,
            'key_id': current_app.config['RAZORPAY_KEY_ID']
        }), 200

    except Exception as e:
        logger.error(f"Error creating Razorpay order: {str(e)}")
        return jsonify({'error': 'Failed to create order'}), 500

def handle_payment(user, payment, success=False):
    """Handle payment success or failure"""
    if success:
        logger.info(f"Payment successful for user: {user.email}")
        handle_email_notification(user.email, user.firstname, payment.amount, success=True)
    else:
        logger.error(f"Payment failed for user: {user.email}")
        handle_email_notification(user.email, user.firstname, payment.amount, success=False)
    
    

    # Update payment status
    payment.status = Payments.STATUS_COMPLETED if success else Payments.STATUS_FAILED
    payment.updated_at = datetime.now()
    payment.save()
    logger.debug(f"Payment status updated to {payment.status} for user: {user.email}")

@razorpay_bp.route('/verify-payment', methods=['POST'])
@token_required
def verify_payment(user_id):
    """Verify Razorpay payment and update user credits"""
    # Fetch existing user's details
    user = User.get_by_id(user_id)
    payment = Payments.get_latest_by_user_id(user_id)
    
    try:
        data = request.get_json()
        logger.debug("=== Starting Payment Verification ===")
        logger.debug(f"Received request data: {json.dumps(data, indent=2)}")

        # Extract payment details
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        expected_amount = data.get('amount')  # Amount from frontend for double verification
        
        if not razorpay_payment_id:
            logger.warning("Payment ID missing in request - payment may not have completed (possibly due to Razorpay gateway error)")

            # Try to get payment by order ID
            if not payment and razorpay_order_id:
                payment = Payments.get_by_provider_order_id(razorpay_order_id)

            # Log the failure in Logs table
            payment_log = Logs(
                txnid=razorpay_order_id or f"FAIL_{user_id}_{int(datetime.now().timestamp())}",
                status=Payments.STATUS_FAILED,
                amount=payment.amount if payment else float(expected_amount or 0) / 100,
                created_at=datetime.now()
            )
            payment_log.save()

            if payment:
                handle_payment(user, payment, success=False)
            else:
                logger.warning("No payment object found to mark as failed")

            return jsonify({
                'error': 'Payment verification failed',
                'message': 'Payment ID is missing. This usually happens when the payment gateway encounters an error (e.g., 502 Bad Gateway) and the payment does not complete.',
                'status': 'failed'
            }), 400



        # Initialize Razorpay client
        razorpay_client = get_razorpay_client()
        logger.debug("Razorpay client initialized")

        try:
            # Create initial payment log entry with processing status
            payment_log = Logs.get_log_by_txnid(razorpay_order_id)

            if payment_log:
                logger.debug("Existing log found. Updating status to pending.")
                payment_log.status = Payments.STATUS_PENDING
                payment_log.amount = float(expected_amount)/100 if expected_amount else 0
            else:
                logger.debug("Creating new log for transaction.")
                payment_log = Logs(
                    txnid=razorpay_order_id or f"FAIL_{user_id}_{int(datetime.now().timestamp())}",
                    status=Payments.STATUS_PENDING,
                    amount=float(expected_amount)/100 if expected_amount else 0,
                    created_at=datetime.now()
                )
            payment_log.save()

            # Fetch payment details from Razorpay
            logger.debug(f"Fetching payment details for ID: {razorpay_payment_id}")
            payment_details = razorpay_client.payment.fetch(razorpay_payment_id)
            logger.debug(f"Razorpay payment details: {json.dumps(payment_details, indent=2)}")
            
            if not payment_details:
                payment_log.status = Payments.STATUS_FAILED
                payment_log.save()
                logger.error("No payment details returned from Razorpay")
                return jsonify({'error': 'Payment details not found'}), 404

            # Extract payment information
            razorpay_amount = int(payment_details.get('amount', 0))
            razorpay_status = payment_details.get('status')
            razorpay_order_id = payment_details.get('order_id')
            razorpay_currency = payment_details.get('currency', 'INR')

            logger.debug(f"""
            Payment Details from Razorpay:
            - Amount: {razorpay_amount}
            - Status: {razorpay_status}
            - Order ID: {razorpay_order_id}
            - Currency: {razorpay_currency}
            - Signature: {razorpay_signature}
            """)

            # Verify payment status
            if razorpay_status not in ['captured', 'authorized']:
                payment_log.status = Payments.STATUS_FAILED
                # payment_log.payment_data = json.dumps({
                #     **json.loads(payment_log.payment_data),
                #     "razorpay_status": razorpay_status,
                #     "error": f"Payment not completed. Status: {razorpay_status}"
                # })
                payment_log.save()
                logger.error(f"Payment not completed. Status: {razorpay_status}")
                return jsonify({'error': f'Payment not completed. Status: {razorpay_status}'}), 400

            # Verify amount if provided
            if expected_amount and int(expected_amount) != razorpay_amount:
                payment_log.status = Payments.STATUS_FAILED
                # payment_log.payment_data = json.dumps({
                #     **json.loads(payment_log.payment_data),
                #     "error": f"Amount mismatch. Expected: {expected_amount}, Received: {razorpay_amount}"
                # })
                payment_log.save()
                logger.error(f"Amount mismatch. Expected: {expected_amount}, Received: {razorpay_amount}")
                return jsonify({'error': 'Amount mismatch'}), 400

            # Find payment record using payment ID first
            payment = Payments.get_by_provider_payment_id(razorpay_payment_id)
            
            # If not found and we have order ID, try that
            if not payment and razorpay_order_id:
                payment = Payments.get_by_provider_order_id(razorpay_order_id)
                logger.debug(f"Looking up payment by Razorpay order ID: {razorpay_order_id}")

            credits = data.get('credits')
            logger.debug(f"Calculated credits: {credits} for amount: {razorpay_amount}")

            subscription = data.get('subscription')
            user.subscription = subscription
            user.save()
            logger.info(f"User subscription updated: {user.subscription}")

            # Update payment status and details
            logger.debug("Updating payment record with verification details")
            payment.provider_payment_id = razorpay_payment_id
            payment.provider_signature = razorpay_signature
            payment.notes = json.dumps({
                **json.loads(payment.notes or '{}'),
                'verification_data': payment_details,
                'credits': credits
            })
            handle_payment(user, payment, success=True)
            logger.debug("Payment record updated successfully")

            # Update payment log with success status
            payment_log.status = payment.status
            payment_log.amount = payment.amount
            # payment_log.payment_data = json.dumps({
            #     "order_id": payment.order_id,
            #     "payment_id": payment.provider_payment_id,
            #     "signature": payment.provider_signature,
            #     "notes": json.loads(payment.notes or '{}'),
            #     "currency": payment.currency,
            #     "status": "completed"
            # })
            payment_log.save()
            logger.debug("Payment Logs updated with success status")

            # Update user credits
            logger.debug(f"Updating credits for user ID: {user_id}")
            previous_credits = user.credit_point
            user.update_credits(credits)
            logger.debug(f"Credits updated: {previous_credits} -> {user.credit_point}")

            logger.info(f"Payment verification successful. Credits added: {credits}")
            logger.debug("=== Payment Verification Completed ===")
            
            return jsonify({
                'status': 'success',
                'credits_added': credits,
                'total_credits': user.credit_point
            }), 200

        except Exception as e:
            # Update payment log with error status
            if payment_log:
                payment_log.status = "incomplete"
                # payment_log.payment_data = json.dumps({
                #     **json.loads(payment_log.payment_data),
                #     "error": str(e)
                # })
                payment_log.save()
            handle_payment(user, payment, success=False)
            logger.error(f"Error processing payment details: {str(e)}")
            logger.debug("Full error details:", exc_info=True)
            return jsonify({'error': 'Failed to process payment details'}), 400

    except Exception as e:
        # Update payment log with error status if it exists
        if 'payment_log' in locals():
            payment_log.status = "incomplete"
            # payment_log.payment_data = json.dumps({
            #     **json.loads(payment_log.payment_data),
            #     "error": str(e)
            # })
            payment_log.save()
        if payment:
            payment.status = Payments.STATUS_PENDING
            payment.save()
        else:
            logger.warning("No payment object found to mark as pending after exception")

        
        logger.error(f"Payment verification failed: {str(e)}")
        logger.debug("Full error details:", exc_info=True)
        return jsonify({'error': str(e)}), 400

@razorpay_bp.route('/history', methods=['GET'])
@token_required
def get_payment_history(user_id):
    """Get user's payment history"""
    try:
        with db_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, provider_order_id, amount, currency, 
                           status, created_at, updated_at,notes
                    FROM payments
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                payments = cursor.fetchall()
        
        user = User.get_by_id(user_id)

        return jsonify({
            'payments': [{
                'id': p['id'],
                'order_id': p['provider_order_id'].split('_')[-1],
                'amount': p['amount'],
                'currency': p['currency'],
                'status': p['status'],
                'created_at': p['created_at'].isoformat(),
                'updated_at': p['updated_at'].isoformat() if p['updated_at'] else None,
                'plan': json.loads(p['notes']) if p.get('notes') else {},
                'join_date': user.created_at.isoformat() if user else None,
                'remaining_credits': user.credit_point if user else 0
            } for p in payments]
        }), 200

    except Exception as e:
        logger.error(f"Error fetching payment history: {str(e)}")
        return jsonify({'error': 'Failed to fetch payment history'}), 500 