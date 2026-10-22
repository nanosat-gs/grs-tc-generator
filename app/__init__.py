import os

from flask import Flask
from app.database.factories.database_manager import DatabaseManager
from app.routes.web_routes import web_bp

DEV_SECRET_KEY = 'dev-secret-key-change-in-production'

def create_app():
    """Application Factory Pattern to create and configure the Flask app."""
    app = Flask(__name__)

    # Configuration
    # The secret comes from the environment; the fallback is for development only.
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or DEV_SECRET_KEY

    # Initialize Database
    # Force PostgreSQL usage as requested
    DatabaseManager.init_db(db_type='postgresql')

    # Register Blueprints
    app.register_blueprint(web_bp)

    # Teardown context: Close DB session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        # We need to be careful here. DatabaseManager.get_session() creates a NEW session.
        # Ideally, we should close the session that was used in the request.
        # However, since we are using a scoped_session pattern implicitly via the Manager (likely),
        # or creating new sessions per request in routes, we might not need this global teardown 
        # if routes handle their own closing (which they do in the current web_routes.py).
        
        # But to be safe and follow the pattern if DatabaseManager uses scoped_session:
        try:
            # This might create a session just to close it if none existed, but it's safe.
            DatabaseManager.get_session().close()
        except Exception:
            pass

    return app