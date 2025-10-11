import sqlite3
from flask import g


class DB:
    def __init__(self, dbFile):
        self.dbFile = str(dbFile)


    def connect(self):
        if not hasattr(g, "_db") or g._db is None:
            g._db = sqlite3.connect(self.dbFile)
            g._db.row_factory = sqlite3.Row
        return g._db


    def close(self, exception=None):
        db = getattr(g, "_db", None)
        if db is not None:
            db.close()
            g._db = None


    def initDB(self, script=None):
        if not script:
            return
        db = self.connect()
        db.executescript(script)
        db.commit()


    def reset(self):
        db = self.connect()
        cur = db.cursor()
        cur.execute("""
        SELECT type, name FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
        """)
        for obj in cur.fetchall():
            objType = obj[0].upper()
            objName = obj[1]
        # safe identifier interpolation
            cur.execute(f"DROP {objType} IF EXISTS \"{objName}\"")
        db.commit()