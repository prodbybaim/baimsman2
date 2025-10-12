from flask import Flask
from config import ROOT, SESSION_LIFETIME_DAYS
import os
from datetime import timedelta
from routes.admin import bp as admin_bp
from routes.api import bp as api_bp
from routes.site import bp as site_bp
from errors import register_error_handlers
from articles import importArticles
    

def create_app():
    app = Flask(__name__, static_folder=str(ROOT / 'web/static'), template_folder=str(ROOT / 'web/templates'))
    app.config['JSON_SORT_KEYS'] = False
    # secret key for session signing - override with env var in production
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    # set default permanent session lifetime
    app.permanent_session_lifetime = timedelta(days=SESSION_LIFETIME_DAYS)

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(site_bp)

    register_error_handlers(app)

    # importArticles needs a Flask application context because DB.connect()
    # uses `flask.g`. Run it inside app.app_context().
    try:
        with app.app_context():
            importArticles()
    except Exception:
        # don't prevent app startup on non-fatal import errors; surface if needed
        pass
    
    return app