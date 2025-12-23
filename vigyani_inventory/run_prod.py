import os
from app import create_app

if __name__ == '__main__':
    # Force production environment
    env = 'prod'
    app = create_app(env)
    
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))  # Using 5000 as default port

    # Ensure proper binding for container environments
    host = '0.0.0.0'
    
    app.run(
        host=host,
        port=port,
        debug=False,  # Always False in production
        use_reloader=False,  # Always False in production
        threaded=True  # Enable threading for better handling of concurrent requests
    )
    