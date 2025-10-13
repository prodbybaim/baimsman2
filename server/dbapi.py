from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import markdown
from db import DB
from utils import _sha256, text_snippet
from config import DB_FILE

GLOBALSCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    uuid TEXT PRIMARY KEY,
    title TEXT,
    creator TEXT,
    created TEXT,
    content TEXT,
    preview TEXT,
    content_hash TEXT,
    mtime REAL,
    last_indexed TEXT
);

CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);
CREATE INDEX IF NOT EXISTS idx_articles_creator ON articles(creator);

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

CREATE TABLE IF NOT EXISTS news (
    uuid TEXT PRIMARY KEY,
    title TEXT,
    created TEXT,
    content TEXT,
    preview TEXT,
    content_hash TEXT,
    mtime REAL,
    last_indexed TEXT
);

CREATE INDEX IF NOT EXISTS idx_news_title ON news(title);
"""

ARTICLESCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    uuid TEXT PRIMARY KEY,
    title TEXT,
    creator TEXT,
    created TEXT,
    content TEXT,
    preview TEXT,
    content_hash TEXT,
    mtime REAL,
    last_indexed TEXT
);
"""

USERSCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    role TEXT
);
"""

TEACHERSCHEMA = """
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    degree TEXT,
    teaching_since TEXT,
    quote TEXT
);
"""

NEWSCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    uuid TEXT PRIMARY KEY,
    title TEXT,
    created TEXT,
    content TEXT,
    preview TEXT,
    content_hash TEXT,
    mtime REAL,
    last_indexed TEXT
);
"""
db = DB(DB_FILE)

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _row_to_dict(cursor, row) -> Dict[str, Any]:
    if row is None:
        return None # type: ignore
    return {k: row[k] for k in row.keys()}

class ArticleAPI():
    def __init__(self, db: DB):
        self.db = db
        
        try:
            self.db.initDB(ARTICLESCHEMA)
        except Exception:
            conn = self.db.connect()
            conn.executescript(ARTICLESCHEMA)
            conn.commit()
    
    def add(self, title: str, creator: str, content: str, uuid: Optional[str] = None) -> str:
        conn = self.db.connect()
        if not uuid:
            uuid = _sha256(title + str(datetime.now(timezone.utc)))
        preview = text_snippet(content, length=200)
        content_hash = _sha256(content)
        now = _now_iso()
        mtime = None
        conn.execute(
            "INSERT OR REPLACE INTO articles (uuid, title, creator, created, content, preview, content_hash, mtime, last_indexed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid, title, creator, now, content, preview, content_hash, mtime, now),
        )
        conn.commit()
        self.clear_caches()
        return uuid

    def fetch(self, uuid: Optional[str] = None, q: Optional[str] = None, limit: int = 50, offset: int = 0) -> Any:
        conn = self.db.connect()
        if uuid:
            row = conn.execute("SELECT * FROM articles WHERE uuid = ?", (uuid,)).fetchone()
            if not row:
                return None
            d = _row_to_dict(conn, row)
            d["content_html"] = markdown.markdown(d.get("content") or "", extensions=["fenced_code", "tables"])
            return d
        if q:
            qterm = f"%{q}%"
            rows = conn.execute(
                "SELECT * FROM articles WHERE title LIKE ? OR content LIKE ? ORDER BY created DESC LIMIT ? OFFSET ?",
                (qterm, qterm, limit, offset),
            ).fetchall()
            return [_row_to_dict(conn, r) for r in rows]
        rows = conn.execute("SELECT * FROM articles ORDER BY created DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [_row_to_dict(conn, r) for r in rows]

    def update(self, uuid: str, **fields) -> bool:
        if not fields:
            return False
        allowed = {"title", "creator", "content", "preview", "created"}
        sets = []
        vals = []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return False
        vals.append(uuid)
        conn = self.db.connect()
        conn.execute(f"UPDATE articles SET {', '.join(sets)} WHERE uuid=?", tuple(vals))
        conn.commit()
        self.clear_caches()
        return True

    def delete(self, uuid: str) -> bool:
        conn = self.db.connect()
        cur = conn.execute("DELETE FROM articles WHERE uuid=?", (uuid,))
        conn.commit()
        self.clear_caches()
        return cur.rowcount > 0

    def clear_caches(self):
        try:
            self.fetch.cache_clear() # type: ignore
        except Exception:
            pass

class UserAPI():
    def add(self, username: str, password_hash: str, role: str = "viewer") -> None:
        conn = db.connect()
        conn.execute("INSERT OR REPLACE INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash, role))
        conn.commit()

    def auth(self, username: str, password_hash: str) -> bool:
        conn = db.connect()
        row = conn.execute("SELECT 1 FROM users WHERE username=? AND password_hash=?", (username, password_hash)).fetchone()
        return bool(row)

    def get(self, username: str) -> Optional[Dict[str, Any]]:
        conn = db.connect()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return _row_to_dict(conn, row)

    def list(self) -> List[Dict[str, Any]]:
        conn = db.connect()
        rows = conn.execute("SELECT username, role FROM users ORDER BY username").fetchall()
        return [_row_to_dict(conn, r) for r in rows]

class TeacherAPI():
    def add(self, name: str, degree: str, teaching_since: str, quote: str = None) -> int: # type: ignore
        conn = db.connect()
        cur = conn.execute("INSERT INTO teachers (name, degree, teaching_since, quote) VALUES (?, ?, ?, ?)", (name, degree, teaching_since, quote))
        conn.commit()
        return cur.lastrowid # type: ignore

    def get(self, teacher_id: int) -> Optional[Dict[str, Any]]:
        conn = db.connect()
        row = conn.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)).fetchone()
        return _row_to_dict(conn, row)

    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = db.connect()
        rows = conn.execute("SELECT * FROM teachers ORDER BY name LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [_row_to_dict(conn, r) for r in rows]

    def update(self, teacher_id: int, **fields) -> bool:
        allowed = {"name", "degree", "teaching_since", "quote"}
        sets = []
        vals = []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return False
        vals.append(teacher_id)
        conn = db.connect()
        conn.execute(f"UPDATE teachers SET {', '.join(sets)} WHERE id=?", tuple(vals))
        conn.commit()
        return True

class NewsAPI():
    def add(self, title: str, content: str, uuid: Optional[str] = None) -> str:
        conn = db.connect()
        if not uuid:
            uuid = _sha256(title + str(datetime.now(timezone.utc)))
        preview = text_snippet(content, length=200)
        content_hash = _sha256(content)
        now = _now_iso()
        mtime = None
        conn.execute(
            "INSERT OR REPLACE INTO news (uuid, title, created, content, preview, content_hash, mtime, last_indexed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid, title, now, content, preview, content_hash, mtime, now),
        )
        conn.commit()
        return uuid

    def fetch(self, uuid: Optional[str] = None, query: Optional[str] = None, limit: int = 50, offset: int = 0) -> Any:
        db.connect()
        offset = (page - 1) * PAGESHOW
        if q:
            qterm = f"%{q}%"
            rows = db.execute(
                "SELECT * FROM articles WHERE title LIKE ? OR content LIKE ? ORDER BY created DESC LIMIT ? OFFSET ?",
                (qterm, qterm, PAGESHOW, offset)
            ).fetchall()
            total = db.execute(
                "SELECT COUNT(*) FROM articles WHERE title LIKE ? OR content LIKE ?",
                (qterm, qterm)
            ).fetchone()[0]
        else:
            rows = db.execute(
                "SELECT * FROM articles ORDER BY created DESC LIMIT ? OFFSET ?",
                (10, offset)
            ).fetchall()
            total = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        items = []
        for r in rows:
            items.append({
                "slug": r["slug"],
                "title": r["title"],
                "created": r["created"],
                "snippet": text_snippet(r["content"])
            })
        return {"items": items, "total": total, "page": page, "PAGESHOW": 10}
        
    def update(self, uuid: str, **fields) -> bool:
        if not fields:
            return False
        allowed = {"title", "content", "preview", "created"}
        sets = []
        vals = []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return False
        vals.append(uuid)
        conn = db.connect()
        conn.execute(f"UPDATE news SET {', '.join(sets)} WHERE uuid=?", tuple(vals))
        conn.commit()
        return True
    
    def delete(self, uuid: str) -> bool:
        conn = db.connect()
        cur = conn.execute("DELETE FROM news WHERE uuid=?", (uuid,))
        conn.commit()
        return cur.rowcount > 0
