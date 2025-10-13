import sqlite3
from flask import g as flask_g
from pathlib import Path

class DB:
    def __init__(self, dbFile):
        self.dbFile = str(dbFile)

    def connect(self):
        """Per-request connection stored on flask.g"""
        if not hasattr(flask_g, "_db") or flask_g._db is None:
            # detect types helps with DATE/TIMESTAMP if you use them
            conn = sqlite3.connect(self.dbFile, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30)
            conn.row_factory = sqlite3.Row
            # safe pragmas for better concurrency and FK support
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            flask_g._db = conn
        return flask_g._db

    def get_conn(self):
        """Independent connection not bound to request context (for background tasks)."""
        conn = sqlite3.connect(self.dbFile, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def close(self, exception=None):
        db = getattr(flask_g, "_db", None)
        if db is not None:
            try:
                db.close()
            finally:
                flask_g._db = None

    def initDB(self, script=None):
        """Initialize schema from SQL text or path to SQL file."""
        if not script:
            return
        if isinstance(script, (str,)) and Path(script).exists():
            script = Path(script).read_text(encoding="utf-8")
        db = self.connect()
        db.executescript(script)
        db.commit()

    def reset(self):
        """Drop all user objects (tables, indexes, triggers, views) except sqlite_*."""
        db = self.connect()
        cur = db.cursor()
        cur.execute("""
            SELECT type, name FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
        """)
        rows = cur.fetchall()
        # mapping SQL types to DROP statements
        for obj in rows:
            objType = obj[0].lower()
            objName = obj[1]
            # escape double-quotes in identifier
            safe_name = objName.replace('"', '""')
            if objType == "table":
                cur.execute(f'DROP TABLE IF EXISTS "{safe_name}"')
            elif objType == "index":
                cur.execute(f'DROP INDEX IF EXISTS "{safe_name}"')
            elif objType == "view":
                cur.execute(f'DROP VIEW IF EXISTS "{safe_name}"')
            elif objType == "trigger":
                cur.execute(f'DROP TRIGGER IF EXISTS "{safe_name}"')
            else:
                # fallback: try generic DROP if a new type appears
                try:
                    cur.execute(f'DROP {objType.upper()} IF EXISTS "{safe_name}"')
                except Exception:
                    pass
        db.commit()

    def init_app(self, app):
        """Register teardown handler on a Flask app instance."""
        app.teardown_appcontext(self.close)
