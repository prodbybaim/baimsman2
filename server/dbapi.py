from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import markdown
from dbutils import DB
from utils import _sha256, text_snippet
from config import DB_FILE, PAGEDIR, PREVIEWLIMIT, PREVIEWWORD
from pathlib import Path
import uuid as uuidlib
import sqlite3

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
    degree TEXT,
    teaching_since TEXT,
    quote TEXT
);
"""

db = DB(DB_FILE)

class readsAPI():
    @staticmethod
    def add(title: str="No Title", creator: str = "admin", content: str= "No Content.", type_: str = "article") -> str:
        now = datetime.now(timezone.utc)
        uid = str(uuidlib.uuid4())
        date_path = now.strftime("%y/%m/%d")
        base = Path(PAGEDIR) / date_path
        base.mkdir(parents=True, exist_ok=True)

        fpath = base / f"{uid}.md"

        # Markdown front-matter
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
        connection = db.connect()
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

    def fetch(self) -> Any:
        return
    
    def update(self) -> Any:
        return 

    def delete(self) -> Any:
        return

    def clear_caches(self) -> Any:
        return

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
