from flask import Blueprint, request, jsonify, current_app, send_from_directory, send_file
from ..services.file_service import process_file_upload, get_file_summary, delete_file_from_s3, get_transcript_pdf, save_edited_file
from ..models.file import File
from ..utils.auth import token_required
import logging
import boto3
from io import BytesIO

logger = logging.getLogger(__name__)
files_bp = Blueprint('files', __name__)
s3_client = boto3.client('s3')

@files_bp.route('/upload', methods=['POST'])
@token_required
def upload_file(current_user_id):
    """Handle file upload"""
    try:
        file = request.files.get('file')
        if not file:
            logger.warning("File not provided in request")
            return jsonify({'error': 'No file provided'}), 400

        result = process_file_upload(file, current_user_id)
        return jsonify(result), 200

    except ValueError as e:
        logger.warning(f"Validation error during file upload: {str(e)}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        return jsonify({'error': 'File upload failed'}), 500

@files_bp.route('/', methods=['GET'])
@token_required
def get_user_files(current_user_id):
    """Get all files for a user"""
    try:
        files = File.get_user_files(current_user_id)
        if not files:
            return jsonify({'message': 'No files found for this user'}), 404

        file_list = [{
            'id': file.id,
            'file_name': file.file_name,
            'file_path': file.file_path,
            'upload_time': file.upload_time.isoformat(),
            'processed': file.processed
        } for file in files]

        return jsonify({'files': file_list}), 200

    except Exception as e:
        logger.error(f"Error fetching user files: {str(e)}")
        return jsonify({'error': 'Failed to fetch files'}), 500

@files_bp.route('/summary', methods=['GET', 'POST'])
@token_required
def get_file_summary_endpoint(current_user_id):
    if request.method == 'GET':
        """Get summary for a file"""
        try:
            file_id = request.args.get('file_id')
            if not file_id:
                logger.warning("File ID is required for summary request")
                return jsonify({'error': 'File ID is required'}), 400

            # Verify file belongs to user
            file = File.get_by_id(file_id)
            if not file or file.user_id != current_user_id:
                return jsonify({'error': 'File not found'}), 404

            # Get summary using file path from service
            summary = get_file_summary(file.file_path)
            if not summary:
                return jsonify({'error': 'Failed to get file summary'}), 400
            
            return jsonify(summary), 200

        except Exception as e:
            logger.error(f"Error processing summary request: {str(e)}")
            return jsonify({'error': 'An unexpected error occurred'}), 500

    elif request.method == 'POST':
        """Save the edited summary of a file"""
        try:
            data = request.get_json()
            file_id = data.get('file_id')
            if not file_id:
                logger.warning("File ID is required for summary request")
                return jsonify({'error': 'File ID is required'}), 400
            
            # Verify file belongs to user
            file = File.get_by_id(file_id)
            if not file or file.user_id != current_user_id:
                return jsonify({'error': 'File not found'}), 404
            
            # Get the edited summary from the request
            edited_summary = data.get('summary')
            if not edited_summary:
                return jsonify({'error': 'Summary is required'}), 400

            # Update the summary in the database
            response = save_edited_file(file.file_path, edited_summary)
            if response:
                return jsonify({'message': 'Summary updated successfully'}), 200

        except Exception as e:
            logger.error(f"Error saving edited summary: {str(e)}")
            return jsonify({'error': 'Failed to save edited summary'}), 500

@files_bp.route('/download', methods=['GET'])
@token_required
def download_file(current_user_id):
    """Download the file transcript as PDF"""
    try:
        file_id = request.args.get('file_id')
        if not file_id:
            logger.warning("File ID is required for download")
            return jsonify({'error': 'File ID is required'}), 400
        
        # Generate PDF
        pdf_bytes, file_name = get_transcript_pdf(file_id, current_user_id)
        file_name = file_name.split('.')[0]
        # file_name = file_name + '.pdf'
        logger.info(f"File name: {file_name}")
        
        if not pdf_bytes:
            logger.error(f"Failed to generate PDF for file {file_id}: {file_name}")
            return jsonify({'error': file_name}), 400
            
        # Log the size of the PDF for debugging
        logger.info(f"Generated PDF size: {len(pdf_bytes)} bytes")
        
        try:
            # Save PDF temporarily for verification
            temp_path = f"/tmp/transcript_{file_id}.pdf"
            with open(temp_path, 'wb') as f:
                f.write(pdf_bytes)
            logger.info(f"PDF saved temporarily at {temp_path} for verification")
            
            # Send file from the temporary location
            response = send_file(
                temp_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"{file_name}_transcript.pdf"
            )
            
            # Add headers to prevent caching
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            return jsonify({'error': 'Failed to send PDF'}), 500
        
    except Exception as e:
        logger.error(f"Error processing download request: {str(e)}")
        return jsonify({'error': 'Failed to process download request'}), 500

@files_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_file(current_user_id):
    """Delete a file"""
    try:
        file_id = request.args.get('file_id')
        if not file_id:
            logger.warning("File ID is required for deletion")
            return jsonify({'error': 'File ID is required'}), 400

        # Verify file belongs to user
        file = File.get_by_id(file_id)
        if not file or file.user_id != current_user_id:
            return jsonify({'error': 'File not found'}), 404
        
        # Delete file from S3 and database
        delete_file_from_s3(file.file_path)
        file.delete()
        
        return jsonify({'message': 'File deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return jsonify({'error': 'Failed to delete file'}), 500