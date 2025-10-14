import sqlite3
from flask import g as flask_g
from pathlib import Path
from config import DB_FILE

class DB:
    def __init__(self, dbFile):
        self.dbFile = str(dbFile)

    

    def init_app(self, app):
        """Register teardown handler on a Flask app instance."""
        app.teardown_appcontext(self.close)
