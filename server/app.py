from flask import Flask
from config import ROOT, SESSION_LIFETIME_DAYS, DB_FILE
import os
from datetime import timedelta
from routes.admin import bp as admin_bp
from routes.api import bp as api_bp
from routes.site import bp as site_bp
from errors import register_error_handlers
from dbutils import DB
from dbapi import GLOBALSCHEMA, init_db

def create_app():
    db = DB(DB_FILE)
    app = Flask(__name__, static_folder=str(ROOT / 'web/static'), template_folder=str(ROOT / 'web/templates'))
    app.config['JSON_SORT_KEYS'] = False
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    app.permanent_session_lifetime = timedelta(days=SESSION_LIFETIME_DAYS)

    #app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    #app.register_blueprint(site_bp)

    register_error_handlers(app)
    
    with app.app_context():
        init_db()
            
    return app