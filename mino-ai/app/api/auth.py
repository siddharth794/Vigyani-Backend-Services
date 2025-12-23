from flask import Blueprint, request, jsonify

from app.services.tenant_sync import sync_update_tenant
from ..models.user import User
from ..utils.auth import create_token, token_required
from ..utils.file import get_base64_image
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import base64
import requests

from app.models import user


logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


def get_image_format(header):
    """Detect image format from file header (magic bytes)"""
    if header.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    elif header.startswith(b'\x89PNG'):
        return 'png'
    elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return 'gif'
    elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'
    else:
        return None


def validate_image(stream):
    """Validate image file type and size"""
    header = stream.read(512)
    stream.seek(0)
    format = get_image_format(header)
    if not format:
        return None
    return '.' + format


# Agentic SaaS backend base URL
# Prefer env override. When running inside Docker, localhost points to the container,
# so fall back to host.docker.internal on port 5001 (backend's mapped port).
def _get_agentic_base_url():
    env_url = os.getenv("AGENTIC_BASE_URL")
    if env_url:
        return env_url
    if os.path.exists("/.dockerenv"):
        return "http://host.docker.internal:5001/tenants/"
    return "http://0.0.0.0:5001/tenants/"

AGENTIC_BASE_URL = _get_agentic_base_url()
logger.info(f"Agentic Base URL: {AGENTIC_BASE_URL}")


def create_tenant_for_user(name, domain=None, plan=None):
    payload = {
        "name": name,
        "domain": domain,
        "plan": plan
    }
    try:
        response = requests.post(AGENTIC_BASE_URL, json=payload)
        if response.status_code == 201:
            tenant_data = response.json()
            # expected response must contain tenant_id
            return tenant_data['tenant_id']
        else:
            logger.error(f"Failed to create tenant: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception while creating tenant: {str(e)}")
        return None


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Register a new user"""
    logger.info("Received signup request")
    try:
        data = request.get_json()

        # Required fields
        username = data.get('username')
        encoded_password = data.get('password')
        try:
            password = base64.b64decode(encoded_password).decode('utf-8')
        except Exception as e:
            logger.error(
                f"Failed to decode base64 password during signup: {str(e)}")
            return jsonify({'error': 'Invalid password format'}), 400
        email = data.get('email')
        logger.info(f"Decoded password: {password}")
        logger.info(f"Encoded password: {encoded_password}")

        # Optional fields
        phone = data.get('phone')
        firstname = data.get('firstname')
        lastname = data.get('lastname')

        if not username or not password or not email:
            logger.warning("Signup attempt with missing required credentials")
            return jsonify({'error': 'Username, password and email are required'}), 400

        # Check if user already exists
        if User.get_by_username(username):
            logger.warning(
                f"Signup attempt with existing username: {username}")
            return jsonify({'error': 'Username already exists'}), 409

        if User.get_by_email(email):
            logger.warning(f"Signup attempt with existing email: {email}")
            return jsonify({'error': 'Email already exists'}), 409
        # Create tenant for the new user
        tenant_id = create_tenant_for_user(username)
        if not tenant_id:
            return jsonify({'error': 'Failed to create tenant'}), 500

        # Create new user with initial credits
        user = User(
            username=username,
            email=email,
            phone=phone,
            firstname=firstname,
            lastname=lastname,
            credit_point=100,  # Initial credits
            tenant_id=tenant_id
        )
        user.password = password  # This will hash the password
        user.save()

        logger.info(f"User registered successfully: {username}")
        return jsonify({'message': 'User registered successfully'}), 201

    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        encoded_password = data.get('password')
        
        logger.info(f"Login attempt - username: {username}, email: {email}")
        
        try:
            password = base64.b64decode(encoded_password).decode('utf-8')
            logger.debug(f"Password decoded successfully (length: {len(password)})")
        except Exception as e:
            logger.error(
                f"Failed to decode base64 password during login: {str(e)}")
            return jsonify({'error': 'Invalid password format'}), 400

        if not username and not email:
            logger.warning("Login attempt without username or email")
            return jsonify({'error': 'Username or email is required'}), 400

        user = User.get_by_username(username) if username else None
        if not user and email:
            user = User.get_by_email(email)
        
        if not user:
            logger.warning(f"User not found - username: {username}, email: {email}")
            return jsonify({'error': 'Invalid username or password'}), 401
        
        logger.info(f"User found: {user.username} (id: {user.id})")
        
        password_valid = user.verify_password(password)
        logger.debug(f"Password verification result: {password_valid}")
        
        if not password_valid:
            logger.warning(f"Invalid password for user: {username or email}")
            return jsonify({'error': 'Invalid username or password'}), 401

        token = create_token(user.id)
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'firstname': user.firstname,
                'lastname': user.lastname,
                'credit_point': user.credit_point,
                'image': get_base64_image(user.image),
                'tenant_id': user.tenant_id,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/profile/image', methods=['POST'])
@token_required
def upload_profile_image(current_user_id):
    """Upload profile picture"""
    try:
        if 'image' not in request.files:
            logger.error("No image file in request")
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No selected file'}), 400

        # Log file details
        logger.info(
            f"Received file: {file.filename}, Content-Type: {file.content_type}")

        # Read file data once
        image_data = file.read()

        # Check file size (200KB limit)
        file_size = len(image_data)
        logger.info(f"File size: {file_size} bytes")

        if file_size > 200 * 1024:  # 200KB in bytes
            logger.error(f"File size ({file_size} bytes) exceeds limit")
            return jsonify({'error': 'File size exceeds 200KB limit'}), 400

        # Validate image format using the read data
        format = get_image_format(image_data)
        if not format:
            logger.error(f"Invalid image format for file: {file.filename}")
            return jsonify({'error': 'Invalid image format'}), 400

        # Get user
        user = User.get_by_id(current_user_id)
        if not user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'error': 'User not found'}), 404

        # Save image to user profile
        user.image = image_data
        user.save()

        # Verify the image was saved
        updated_user = User.get_by_id(current_user_id)
        if not updated_user.image:
            logger.error("Image not saved in database")
            return jsonify({'error': 'Failed to save image'}), 500

        # Return the saved image in the response
        return jsonify({
            'message': 'Profile image updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                # Include the base64 image
                'image': get_base64_image(user.image)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error uploading profile image: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@auth_bp.route('/profile', methods=['GET', 'PUT'])
@token_required
def user_profile(current_user_id):
    """Get or update user profile"""
    try:
        user = User.get_by_id(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if request.method == 'GET':
            return jsonify({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'firstname': user.firstname,
                'lastname': user.lastname,
                'credit_point': user.credit_point,
                'image': get_base64_image(user.image),
                'tenant_id': user.tenant_id,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }), 200
        
        elif request.method == 'PUT':
            data = request.get_json()

            # Update fields if provided
            if 'email' in data:
                user.email = data['email']
            if 'phone' in data:
                user.phone = data['phone']
            if 'firstname' in data:
                user.firstname = data['firstname']
            if 'lastname' in data:
                user.lastname = data['lastname']
            if 'image' in data:
                user.image = data['image']
            if 'password' in data:
                user.password = data['password']

            user.save()
            # Sync tenant update - use getattr to safely access attributes that may not exist
            sync_update_tenant(
                tenant_id=user.tenant_id,
                name=user.username,
                domain=getattr(user, 'domain', None),
                plan=getattr(user, 'plan', None) or getattr(user, 'subscription', None),
            )

            return jsonify({
                'message': 'Profile updated successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'firstname': user.firstname,
                    'lastname': user.lastname,
                    'phone': user.phone,
                    'credit_point': user.credit_point,
                    'image': get_base64_image(user.image),
                    'tenant_id': user.tenant_id,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                }
            }), 200

    except Exception as e:
        logger.error(f"Error in user_profile: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@auth_bp.route('/me', methods=['PUT'])
@token_required
def update_user_profile(current_user_id):
    """Update user profile"""
    try:
        user = User.get_by_id(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        # Update fields if provided
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'firstname' in data:
            user.firstname = data['firstname']
        if 'lastname' in data:
            user.lastname = data['lastname']
        if 'image' in data:
            user.image = data['image']
        if 'password' in data:
            user.password = data['password']

        user.save()
        # Sync tenant update - use getattr to safely access attributes that may not exist
        sync_update_tenant(
            tenant_id=user.tenant_id,
            name=user.username,
            domain=getattr(user, 'domain', None),
            plan=getattr(user, 'plan', None) or getattr(user, 'subscription', None),
        )

        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'firstname': user.firstname,
                'lastname': user.lastname,
                'phone': user.phone,
                'credit_point': user.credit_point,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }
        }), 200

    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@auth_bp.route('/sync/tenant-updated', methods=['POST'])
def tenant_updated():
    data = request.get_json()
    tenant_id = data["tenant_id"]
    name = data.get("name")
    domain = data.get("domain")
    plan = data.get("plan")

    users = User.get_by_tenant_id(tenant_id)
    if not users:
        return jsonify({"error": "User not found"}), 404

    for user in users:
        if name:
            user.username = name
        if domain:
            user.domain = domain
        if plan:
            user.subscription = plan  # map plan to subscription field
        user.save()

    return jsonify({"message": f"{len(users)} user(s) updated from tenant"}), 200


@auth_bp.route('/sync/tenant', methods=['POST'])
def sync_tenant_to_users():
    data = request.get_json()
    tenant_id = data.get("tenant_id")

    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    users = User.get_by_tenant_id(tenant_id)  # this returns a list
    if not users:
        return jsonify({"error": "No users found for tenant"}), 404

    for user in users:
        if data.get("name"):
            user.username = data["name"]
        if data.get("plan"):
            user.subscription = data["plan"]  # map plan to subscription field
        user.save()
        logger.info(f"User {user.id} synced from tenant {tenant_id}")

    return jsonify({"message": f"{len(users)} user(s) synced"}), 200
