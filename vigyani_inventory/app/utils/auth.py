from functools import wraps
from flask import request, jsonify, current_app
from authlib.jose import jwt
from authlib.jose.errors import ExpiredTokenError, BadSignatureError
import logging

logger = logging.getLogger(__name__)

def token_required(f):
    """Decorator to protect routes with JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            logger.warning("Request missing Authorization header")
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split()[1]
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'])
            return f(decoded['sub'], *args, **kwargs)

        except IndexError:
            logger.warning("Malformed Authorization header")
            return jsonify({'error': 'Invalid token format'}), 401
            
        except ExpiredTokenError:
            logger.warning("Expired token used")
            return jsonify({'error': 'Token has expired'}), 401
            
        except BadSignatureError:
            logger.warning("Invalid token signature")
            return jsonify({'error': 'Invalid token'}), 401
            
        except Exception as e:
            logger.error(f"Error processing token: {str(e)}")
            return jsonify({'error': 'Token validation failed'}), 401

    return decorated