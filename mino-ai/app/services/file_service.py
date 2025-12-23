import os
import math
import hashlib
import logging
import json
from datetime import datetime
from flask import current_app
from boto3.s3.transfer import TransferConfig
import boto3
import redis
from ..models.file import File
from ..models.user import User
from ..config import Config
import markdown
from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = None

def get_s3_client():
    """Get or create S3 client"""
    global s3_client
    if s3_client is None:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=current_app.config['AWS_REGION'],
            endpoint_url=f"https://s3.{current_app.config['AWS_REGION']}.amazonaws.com"
        )
    return s3_client

def calculate_file_size_mb(file):
    """Calculate file size in MB"""
    file.seek(0, 2)  # Seek to end of file
    size_in_bytes = file.tell()  # Get current position (file size)
    file.seek(0)  # Reset file pointer to beginning
    return math.ceil(size_in_bytes / (1024 * 1024))  # Convert bytes to MB and round up

def generate_job_id(file_name, user_id):
    """Generate unique job ID for file upload"""
    upload_timestamp = datetime.now().isoformat()
    unique_data = f"{file_name}-{user_id}-{upload_timestamp}"
    return hashlib.sha256(unique_data.encode()).hexdigest()

def progress_callback(bytes_transferred, total_bytes, user_id):
    """Callback for upload progress"""
    try:
        percentage = (bytes_transferred / total_bytes) * 50
        message = json.dumps({
            'user_id': user_id,
            'progress': percentage
        })
        redis_client = redis.Redis(
            host=current_app.config['REDIS_HOST'],
            port=current_app.config['REDIS_PORT'],
            decode_responses=True,
            username=current_app.config['REDIS_USERNAME'],
            password=current_app.config['REDIS_PASSWORD']
        )
        redis_client.publish(f'progress-channel', message)
        logger.debug(f"Upload Progress for user {user_id}: {percentage:.2f}%")

    except Exception as e:
        logger.error(f"Error in progress callback: {str(e)}")

def upload_file_to_s3(file, bucket_name, file_path, user_id):
    """Upload file to S3 with progress tracking"""
    logger.info(f"Starting S3 upload to bucket: {bucket_name}, file: {file_path}")
    
    try:
        config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )
        
        file_size = os.fstat(file.fileno()).st_size
        logger.debug(f"File size: {file_size} bytes")

        s3 = get_s3_client()
        s3.upload_fileobj(
            file,
            bucket_name,
            file_path,
            Config=config,
            # Callback=lambda bytes_transferred: progress_callback(bytes_transferred, file_size, user_id)
        )
        
        logger.info(f"Successfully uploaded file to S3: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise

def process_file_upload(file, user_id):
    """Process file upload including credit check and database updates"""
    try:
        # Calculate file size and check credits
        file_size = calculate_file_size_mb(file)
        user = User.get_by_id(user_id)
        
        if not user:
            raise ValueError("User not found")
            
        if user.credit_point < file_size:
            raise ValueError("Insufficient credit points")

        # Generate file path and job ID
        file_name = file.filename
        job_id = generate_job_id(file_name, user_id)
        extension = os.path.splitext(file_name)[1]
        file_path = f"uploads/{user_id}/{job_id}{extension}"
        
        # Upload file to S3
        bucket_name = current_app.config['S3_UPLOAD_BUCKET']
        upload_file_to_s3(file, bucket_name, file_path, user_id)
        
        # Create file record
        file_record = File(
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            job_id=job_id,
            file_size=file_size,
            processed=True
        )
        file_record.save()
        
        # Update user credits
        user.update_credits(-file_size)
        
        return {
            'message': 'File uploaded successfully',
            'file_id': file_record.id,
            'file_name': file_name,
            'file_path': file_path,
            'file_size': file_size,
            'credit_used': file_size,
            'credit_remaining': user.credit_point,
            'upload_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        raise

def get_file_summary(file_path):
    """Get summary for a file from S3"""
    try:
        if not file_path.endswith(('.mp3', '.mp4', '.wav')):
            logger.error("File ID must end with .mp3 or .mp4 or .wav")
            return None

        # Create summary file path similar to old implementation
        summary_file_id = file_path.rsplit('.', 1)[0] + '_summary.json'
        
        bucket_name = current_app.config['S3_SUMMARY_BUCKET']
        logger.info(f"Fetching summary file for key: {summary_file_id}")
        
        s3 = get_s3_client()
        file_obj = s3.get_object(Bucket=bucket_name, Key=summary_file_id)
        summary_json = json.loads(file_obj['Body'].read().decode('utf-8'))
        
        return summary_json

    except Exception as e:
        logger.error(f"Error getting file summary: {str(e)}")
        return None
    
def save_edited_file(file_path, edited_content):
    """Save edited content to a file in S3"""
    try:
        bucket_name = current_app.config['S3_SUMMARY_BUCKET']
        summary_file_id = file_path.rsplit('.', 1)[0] + '_summary.json'
        
        s3 = get_s3_client()
        s3.put_object(
            Bucket=bucket_name,
            Key=summary_file_id,
            Body=json.dumps({'summary': edited_content}).encode('utf-8'),
            ContentType='application/json'
        )
        
        logger.info(f"Successfully saved edited file to S3: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving edited file to S3: {str(e)}")
        return False
    
def delete_file_from_s3(file_path):
    """Delete a file from S3"""
    try:
        bucket_name = current_app.config['S3_UPLOAD_BUCKET']
        logger.info(f"Deleting file from S3: {file_path}")
        
        s3 = get_s3_client()
        s3.delete_object(
            Bucket=bucket_name,
            Key=file_path
        )
        
        logger.info(f"Successfully deleted file from S3: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting file from S3: {str(e)}")
        return False

def markdown_to_pdf(markdown_text):
    """Convert markdown text to PDF and return bytes"""
    try:
        logger.info("Starting markdown to PDF conversion")
        
        # Convert markdown to HTML
        html = markdown.markdown(markdown_text)
        logger.debug(f"Generated HTML length: {len(html)} characters")
        
        # Add some basic styling
        css = CSS(string='''
            body { 
                font-family: Arial, sans-serif;
                margin: 2cm;
                line-height: 1.6;
            }
            h1, h2, h3 { color: #2c5282; }
            code { 
                background: #f7fafc;
                padding: 2px 4px;
                border-radius: 4px;
            }
            pre { 
                background: #f7fafc;
                padding: 1em;
                border-radius: 8px;
                overflow-x: auto;
            }
        ''')
        
        # Wrap HTML in proper structure
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        logger.debug("Generating PDF...")
        # Generate PDF in memory
        pdf_bytes = HTML(string=full_html).write_pdf(
            stylesheets=[css]
        )
        logger.info(f"Successfully generated PDF of size {len(pdf_bytes)} bytes")
        
        # Verify PDF starts with PDF magic number
        if not pdf_bytes.startswith(b'%PDF'):
            logger.error("Generated file does not appear to be a valid PDF")
            return None
            
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error converting markdown to PDF: {str(e)}")
        return None

# def store_pdf_in_s3(pdf_path, user_id, original_file_id):
#     """Store PDF in S3 and return the file path"""
#     try:
#         # Generate a unique path for the PDF
#         pdf_file_path = f"transcripts/{user_id}/{original_file_id}_transcript.pdf"
#         bucket_name = current_app.config['S3_UPLOAD_BUCKET']
        
#         # Upload PDF to S3
#         with open(pdf_path, 'rb') as pdf_file:
#             s3_client.upload_fileobj(
#                 pdf_file,
#                 bucket_name,
#                 pdf_file_path
#             )
        
#         # Clean up temporary file
#         os.unlink(pdf_path)
#         return pdf_file_path
        
#     except Exception as e:
#         logger.error(f"Error storing PDF in S3: {str(e)}")
#         if pdf_path and os.path.exists(pdf_path):
#             os.unlink(pdf_path)
#         return None

def get_transcript_pdf(file_id, user_id):
    """Get transcript PDF for a file"""
    try:
        # Get the file record
        file = File.get_by_id(file_id)
        if not file or file.user_id != user_id:
            logger.error(f"File not found or access denied. File ID: {file_id}, User ID: {user_id}")
            return None, "File not found"
            
        # Get the summary
        summary = get_file_summary(file.file_path)
        if not summary:
            logger.error(f"No summary found for file {file_id}")
            return None, "Summary not found"
            
        logger.info(f"Got summary of length {len(str(summary))} characters")
        
        # Convert summary to PDF
        pdf_bytes = markdown_to_pdf(str(summary['summary']))
        if not pdf_bytes:
            logger.error("PDF generation failed")
            return None, "Failed to convert summary to PDF"
            
        return pdf_bytes, file.file_name
            
    except Exception as e:
        logger.error(f"Error generating transcript PDF: {str(e)}")
        return None, str(e)