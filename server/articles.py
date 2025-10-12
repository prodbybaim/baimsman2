from functools import lru_cache
import markdown
from datetime import datetime, timezone

from db import DB
from config import DB_FILE, PAGEDIR, PAGESHOW, PAGEPREVIEW
from utils import slugify, text_snippet, parseMD, _sha256

from pathlib import Path

DBPages = DB(DB_FILE)

@lru_cache(maxsize=512)
def articleSlug(slug: str):
    db = DBPages.connect()
    row = db.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    if not row:
        return None
    html = markdown.markdown(row["content"], extensions=["fenced_code", "tables"])
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "content_html": html,
        "created": row["created"],
        "snippet": text_snippet(row["content"], length=PAGEPREVIEW)
    }

@lru_cache(maxsize=128)
def articlePage(page: int, q: str = ""):
    db = DBPages.connect()
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
            (PAGESHOW, offset)
        ).fetchall()
        total = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    items = []
    for r in rows:
        items.append({
            "slug": r["slug"],
            "title": r["title"],
            "created": r["created"],
            "snippet": text_snippet(r["content"], length=PAGEPREVIEW)
        })
    return {"items": items, "total": total, "page": page, "PAGESHOW": PAGESHOW}


def verfyColumn(db):
    cols = db.execute("PRAGMA table_info(articles)").fetchall()
    colnames = [c[1] for c in cols]
    wanted = {
        "uuid": "TEXT",
        "content_hash": "TEXT",
        "mtime": "REAL",
        "last_indexed": "TEXT"
    }
    for name, ctype in wanted.items():
        if name not in colnames:
            db.execute(f"ALTER TABLE articles ADD COLUMN {name} {ctype}")


def importArticles(force=False):
    DBPages.initDB(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            slug TEXT UNIQUE,
            title TEXT,
            content TEXT,
            created TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_articles_slug ON articles(slug);
        """
    )
    db = DBPages.connect()
    verfyColumn(db)

    allowed = {".md", ".markdown", ".txt", ".json"}
    files = sorted(Path(PAGEDIR).rglob("*"))
    inserted = updated = skipped = 0
    any_changed = False
    now_iso = datetime.now(timezone.utc).isoformat()

    for p in files:
        if not p.is_file() or p.suffix.lower() not in allowed:
            continue
        slug = slugify(p.stem)
        raw = p.read_text(encoding="utf-8")
        meta, body = parseMD(raw)
        if meta.get("title"):
            title = str(meta["title"]).strip()
        else:
            import re
            m = re.search(r"^#\s+(.+)$", body, flags=re.M)
            title = m.group(1).strip() if m else p.stem.replace("-", " ").replace("_", " ").title()

        created = None
        date_val = meta.get("date") or meta.get("created")
        if date_val:
            try:
                if hasattr(date_val, "isoformat"):
                    created = date_val.isoformat()
                else:
                    created = str(date_val)
            except Exception:
                created = str(date_val)
        else:
            try:
                parts = p.relative_to(PAGEDIR).parts
                if len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                    y = int(parts[0]); mth = int(parts[1]); d = int(parts[2])
                    created = datetime(y, mth, d).isoformat()
            except Exception:
                created = None
        if not created:
            created = datetime.fromtimestamp(p.stat().st_mtime).isoformat()

        uuid_val = meta.get("uuid")
        content_to_store = body
        file_mtime = p.stat().st_mtime
        content_hash = _sha256(raw)

        row = db.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
        if not row:
            db.execute(
                "INSERT INTO articles (slug, title, content, created, uuid, content_hash, mtime, last_indexed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (slug, title, content_to_store, created, uuid_val, content_hash, file_mtime, now_iso)
            )
            inserted += 1
            any_changed = True
        else:
            need_update = force
            if not need_update:
                if (row.get("content_hash") or "") != content_hash:
                    need_update = True
                elif (row.get("mtime") is None) or (float(row.get("mtime")) != float(file_mtime)):
                    need_update = True
                elif (row.get("title") or "") != (title or ""):
                    need_update = True
                elif (row.get("created") or "") != (created or ""):
                    need_update = True
                elif (row.get("uuid") or "") != (uuid_val or ""):
                    need_update = True
            if need_update:
                db.execute(
                    "UPDATE articles SET title=?, content=?, created=?, uuid=?, content_hash=?, mtime=?, last_indexed=? WHERE slug=?",
                    (title, content_to_store, created, uuid_val, content_hash, file_mtime, now_iso, slug)
                )
                updated += 1
                any_changed = True
            else:
                skipped += 1
                
    print(f"Import: {inserted} inserted, {updated} updated, {skipped} skipped.")
    db.commit()

    if any_changed:
        try:
            articleSlug.cache_clear()
            articlePage.cache_clear()
        except Exception:
            pass

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "force": bool(force)}