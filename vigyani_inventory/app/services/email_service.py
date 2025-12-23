from flask import current_app
from email.message import EmailMessage
import ssl
import smtplib
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sender_email = current_app.config['SENDER_EMAIL']
        self.sender_password = current_app.config['SENDER_PASSWORD']
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587  # Using TLS port instead of SSL
        # Get the directory where this file is located
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def send_email(self, receiver_email, receiver_name, amount, success=False):
        try:
            email = EmailMessage()
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            email['from'] = self.sender_email
            email['to'] = receiver_email

            # Use os.path.join for proper path handling
            file_path = os.path.join(self.base_dir, 'docs')
            if success:
                email['subject'] = "Payment Confirmation - Your Transaction was Successful"
                file_path = os.path.join(file_path, 'success.txt')
            else:
                file_path = os.path.join(file_path, 'failure.txt')
                email['subject'] = "Payment Failed - Action Required"

            logger.info(f"Reading email template from: {file_path}")
            with open(file_path, 'r') as file:
                text = file.read()
            text = text.format(receiver_name=receiver_name, amount=amount, current_date=current_date)
            email.set_content(text)

            # Create SMTP session with TLS
            logger.info(f"Attempting to send email to {receiver_email}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
                smtp.starttls()  # Enable TLS
                smtp.login(self.sender_email, self.sender_password)
                smtp.sendmail(self.sender_email, receiver_email, email.as_string())
                logger.info(f"Email sent successfully to {receiver_email}")
            return True

        except FileNotFoundError as e:
            logger.error(f"Email template file not found: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {receiver_email}: {str(e)}")
            return False

def handle_email_notification(email, name, amount, success=False):
    email_service = EmailService()
    try:
        return email_service.send_email(email, name, amount, success)
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {email}: {str(e)}")
        return False