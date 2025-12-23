import os
from app import create_app

if __name__ == '__main__':
    # Get environment from FLASK_ENV, default to development
    env = 'dev'
    app = create_app(env)
    
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))  # Using 5000 as default port

    # Ensure proper binding for container environments
    host = '0.0.0.0'
    
    app.run(
        host=host,
        port=port,
        debug=env == 'dev',
        use_reloader=env == 'dev',
        threaded=True  # Enable threading for better handling of concurrent requests
    )
    