from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import markdown
from dbutils import DB
from utils import _sha256, text_snippet
from config import DB_FILE, PAGEDIR, PREVIEWLIMIT, PREVIEWWORD
from pathlib import Path
import uuid as uuidlib
import sqlite3
import re
from flask import g as flask_g



db: Optional[DB] = None
# ill edit this file in school

GLOBALSCHEMA = """
CREATE TABLE IF NOT EXISTS reads (
    uuid TEXT PRIMARY KEY,
    title TEXT,
    creator TEXT,
    created TEXT,
    type TEXT,
    preview TEXT,
    mtime REAL
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    role TEXT
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    teaching_since TEXT,
    quote TEXT
);
"""

class DButils:
    @staticmethod
    def connect():
        """Per-request connection stored on flask.g"""
        if not hasattr(flask_g, "_db") or flask_g._db is None:
            # detect types helps with DATE/TIMESTAMP if you use them
            conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            flask_g._db = conn
        return flask_g._db

    @staticmethod
    def init_db():
        global db
        db = DB(DB_FILE)
        conn = DButils.connect()
        conn.executescript(GLOBALSCHEMA)
        conn.commit()
        conn.close()
        
    @staticmethod
    def get_db() -> DB:
        if db is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return db


class DBService:
    @staticmethod
    def rebuild() -> bool:
        return readsAPI.importFromDir()

class readsAPI():
    @staticmethod
    def add(title: str="No Title", creator: str = "admin", content: str= "No Content.", type_: str = "article") -> str:
        now = datetime.now(timezone.utc)
        uid = str(uuidlib.uuid4())
        date_path = now.strftime("%yyyy/%m/%d")
        base = Path(PAGEDIR) / date_path
        base.mkdir(parents=True, exist_ok=True)

        fpath = base / f"{uid}.md"

        md = (
            f"---\n"
            f"date: '{now.strftime('%Y-%m-%d %H:%M:%S')}'\n"
            f"title: {title}\n"
            f"uuid: {uid}\n"
            f"creator: {creator}\n"
            f"type: {type_}\n"
            f"---\n\n"
            f"{content.strip()}\n"
        )

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(md)

        preview = text_snippet(content, 180)
        DButils.init_db()
        connection = DButils.connect()
        connection.execute(
            """
            INSERT INTO reads (uuid, title, creator, created, type, preview, mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [uid, title, creator, now.isoformat(), type_, preview, now.timestamp()],
        )
        connection.commit()
        connection.close()

        print( f"Created new read: {title} ({uid})" )
        return uid

    def preview(self, slug: str) -> Optional[Dict[str, Any]]:
        DButils.init_db()
        connection = DButils.connect()
        cursor = connection.execute(
            "SELECT uuid, title, creator, created, type, preview FROM reads WHERE uuid = ?",
            [slug]
        )
        row = cursor.fetchone()
        connection.close()
        if row:
            return {
                "uuid": row[0],
                "title": row[1],
                "creator": row[2],
                "created": row[3],
                "type": row[4],
                "preview": row[5]
            }
        return None

    def fetch(self) -> Any:
        return
    
    def update(self) -> Any:
        return 

    def delete(self) -> Any:
        return

    def clear_caches(self) -> Any:
        return
    
    @staticmethod
    def importFromDir() -> bool:
        dirPath = Path(PAGEDIR)
        if not dirPath.exists():
            return False

        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row

        # simple front-matter regex
        fmRegex = re.compile(r"^---\s*(.*?)---\s*(.*)$", re.DOTALL)

        try:
            for file in dirPath.rglob("*.md"):
                text = file.read_text(encoding="utf-8")
                meta = {
                    "uuid": file.stem,
                    "title": file.stem,
                    "creator": "imported",
                    "type": "article",
                    "date": datetime.now(timezone.utc).isoformat(),
                }

                # parse front matter if present
                m = fmRegex.match(text)
                if m:
                    front, body = m.groups()
                    for line in front.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta[k.strip()] = v.strip()
                else:
                    body = text

                preview = text_snippet(body, 180)
                now = datetime.now(timezone.utc)

                try:
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO reads
                        (uuid, title, creator, created, type, preview, mtime)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            meta["uuid"],
                            meta["title"],
                            meta["creator"],
                            meta["date"],
                            meta["type"],
                            preview,
                            now.timestamp(),
                        ],
                    )
                    print(meta)
                    print(connection.total_changes)
                except sqlite3.Error as e:
                    print(f"Failed to import {file.name}: {e}")
                    continue

            print("Inserted rows:", connection.total_changes)
            connection.commit()
        finally:
            connection.close()

        return True



        

class NewsAPI():
    def add(self) -> Any:
        return

    def preview(self, offset=0, limit=10, query: str = "") -> Any:
        return

    def update(self) -> Any:
        return

    def delete(self) -> Any:
        return

    def read(self) -> Any:
        return
    
    def clear_caches(self) -> Any:
        return

class UserAPI():
    def add(self) -> Any:
        return

    def auth(self) -> Any:
        return 

    def get(self) -> Any:
        return

    def list(self) -> Any:
        return

class TeacherAPI():
    def add(self) -> Any:
        return

    def get(self) -> Any:
        return

    def list(self) -> Any:
        return

    def update(self) -> Any:
        return
