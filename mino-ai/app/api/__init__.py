from flask import jsonify
from .auth import auth_bp
from .files import files_bp
from .health import health_bp
from .chat import chat_bp

def register_routes(app):
    """Register all API blueprints"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(health_bp)
    try:
        from .speech import speech_api
        app.register_blueprint(speech_api, url_prefix='/api/speech')
    except Exception as e:
        import logging
        logging.error(f"❌ Failed to load speech_api: {e}")

    # Add a catch-all route for undefined paths
    @app.route('/<path:path>')
    def catch_all(path):
        return jsonify({
            'error': 'Not Found',
            'path': path,
            'message': 'The requested endpoint does not exist in this service'
        }), 404

    