import os
from app import create_app

if __name__ == '__main__':
    # Get environment from FLASK_ENV, default to development
    env = 'prod'
    app = create_app(env)
    
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))

    host = '0.0.0.0'

    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )