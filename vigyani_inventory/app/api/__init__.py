from flask import Blueprint, jsonify
from .products import products_bp
# from .health import health_bp
from .razorpay import razorpay_bp
from datetime import datetime

def register_routes(app):
    """Register all API blueprints with proper microservice paths"""
    
    # Simple health check endpoint for AWS target group
    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }), 200
    
    # Register API routes with their prefixes
    # These paths should match your ALB path-based routing rules
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(razorpay_bp, url_prefix='/api/payment')
    
    # Add a catch-all route for undefined paths
    @app.route('/<path:path>')
    def catch_all(path):
        return jsonify({
            'error': 'Not Found',
            'path': path,
            'message': 'The requested endpoint does not exist in this service'
        }), 404
    
    # Register payment routes
    # register_payment_routes(app) 