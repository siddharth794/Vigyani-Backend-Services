from flask import Blueprint, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check API to verify overall application health"""
    logger.debug("Health check started")
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

    logger.debug("Health check completed")
    return jsonify(health_status), 200 