import base64
import os
import logging
import boto3
from flask import current_app
from ..models.file import File

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

def get_base64_image(image_data_or_path):
    """Convert image to base64 string
    Args:
        image_data_or_path: Either a file path string or binary image data
    """
    try:
        if not image_data_or_path:
            return None
            
        # If input is binary data
        if isinstance(image_data_or_path, bytes):
            image_data = image_data_or_path
            # Detect mime type from binary data
            import imghdr
            format = imghdr.what(None, image_data)
            if not format:
                logger.error("Could not determine image format from binary data")
                return None
            mime_type = f'image/{format if format != "jpeg" else "jpg"}'
        else:
            # Handle file paths (S3 or local)
            image_path = image_data_or_path
            
            # Handle S3 paths
            if image_path.startswith('s3://'):
                # Parse bucket and key from s3 path
                path_parts = image_path.replace('s3://', '').split('/')
                bucket = path_parts[0]
                key = '/'.join(path_parts[1:])
                
                # Get file from S3
                s3 = get_s3_client()
                response = s3.get_object(Bucket=bucket, Key=key)
                image_data = response['Body'].read()
            else:
                # Handle local files
                full_path = os.path.join(current_app.root_path, image_path)
                if not os.path.exists(full_path):
                    logger.warning(f"Image file not found: {full_path}")
                    return None
                    
                with open(full_path, 'rb') as image_file:
                    image_data = image_file.read()

            # Get file extension for mime type
            ext = os.path.splitext(image_path)[1].lower()
            if ext.startswith('.'):
                ext = ext[1:]
                
            # Map extension to mime type
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')

        # Convert to base64
        base64_encoded = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_encoded}"
        
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return None 
    
def get_file_info_from_job_id(job_id):
    try:
        file = File.get_by_job_id(job_id)
        if not file:
            logger.error(f"No file found with job_id: {job_id}")
            return None
            
        return {
            'file_name': file.file_name,
            'user_id': file.user_id,
            'file_path': file.file_path
        }
        
    except Exception as e:
        logger.error(f"Error getting file info from job_id: {str(e)}")
        return None