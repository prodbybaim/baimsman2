from flask import Flask
from config import ROOT
from routes.admin import bp as admin_bp
from routes.api import bp as api_bp
from routes.site import bp as site_bp
from errors import register_error_handlers


def create_app():
    app = Flask(__name__, static_folder=str(ROOT / 'web/static'), template_folder=str(ROOT / 'web/templates'))
    app.config['JSON_SORT_KEYS'] = False

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(site_bp)

    register_error_handlers(app)

    return app