from flask import Blueprint, request, jsonify, current_app
from ..utils.auth import token_required
from ..services.chat_service import chat_service
from ..services.file_service import get_file_summary

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/upload', methods=['POST'])
@token_required
def upload_file(user_id):
    """Initializing file context to llm"""
    data = request.get_json()
    file_id = data.get('fileId')
    file_path = data.get('filePath')
    
    if not file_path :
        return jsonify({ 'error': 'Missing required field: filePath' }), 400

    file_summary = get_file_summary(file_path)
    chat_service.initialize_context(file_id, file_summary)
    return jsonify({ 'message': 'File context initialized successfully' }), 200

@chat_bp.route('/query', methods=['GET'])
def query_file():
    """Query about a specific file"""
    file_id = request.args.get('file_id')
    prompt = request.args.get('query')
    
    if not file_id or not prompt:
        return jsonify({ 'error': 'Missing required fields: file_id and query' }), 400
    
    try:
        response = chat_service.get_response(file_id, prompt)
        if response is None:
            return jsonify({ 'error': 'File not found or not processed' }), 404
            
        return jsonify({ 'response': response }), 200

    except Exception as e:
        return jsonify({ 'error': f'Error processing query: {str(e)}' }), 500

@chat_bp.route('/clear-context', methods=['DELETE'])
def clear_context():
    """Clear the context for a specific file"""
    try:
        file_id = request.args.get('file_id')
        chat_service.clear_context(file_id)
        return jsonify({ 'message': 'Context cleared successfully' }), 200

    except Exception as e:
        return jsonify({ 'error': f'Error clearing context: {str(e)}' }), 500 