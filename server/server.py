# server.py
import re, sqlite3, hashlib, markdown
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, g, render_template, request, jsonify, abort

ROOT = Path(__file__).parent
USERDATA = Path("/var/lib/sman2cikpus")
DB_FILE = USERDATA / "articles.db"
PAGEDIR = USERDATA / "articles"
PAGESHOW = 10
PAGEPREVIEW = 200

app = Flask(__name__, static_folder=str(ROOT / "static"), template_folder=str(ROOT / "templates"))
app.config["JSON_SORT_KEYS"] = False

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

    def initSchema(self):
        db = self.connect()
        db.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                slug TEXT UNIQUE,
                title TEXT,
                content TEXT,
                created TEXT
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_articles_slug ON articles(slug)")
        db.commit()
    
    def reset(self):
        if Path(self.dbFile).exists():
            Path(self.dbFile).unlink()  # delete DB file
        # clear any lingering connection in g
        if hasattr(g, "_db"):
            g._db = None
        self.initSchema()

DBase = DB(DB_FILE)

@app.teardown_appcontext
def close_db(exception=None):
    DBase.close(exception)

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:200]

def text_snippet(md: str, length=PAGEPREVIEW):
    # remove markdown syntax quickly
    txt = re.sub(r"```.*?```", "", md, flags=re.S)
    txt = re.sub(r"`.+?`", "", txt)
    txt = re.sub(r"!\[.*?\]\(.*?\)", "", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", txt)
    txt = re.sub(r"[#>*\-]{1,3}", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:length] + ("…" if len(txt) > length else "")

def parseMD(raw):
    """Return (meta_dict, body). meta_dict may be empty."""
    fm_regex = r"^---\s*\n(.*?)\n---\s*\n?"
    m = re.match(fm_regex, raw, flags=re.S)
    if not m:
        return {}, raw
    fm_text = m.group(1)

    # try PyYAML first (if installed)
    try:
        import yaml
        meta = yaml.safe_load(fm_text) or {}
    except Exception:
        # tiny fallback parser for simple key: value lines
        meta = {}
        for line in fm_text.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            meta[k] = v
    body = raw[m.end():]
    return meta, body

def verfyColumn(db):
    """Ensure optional columns exist in articles table (SQLite)."""
    cols = db.execute("PRAGMA table_info(articles)").fetchall()
    colnames = [c[1] for c in cols]
    # columns we want
    wanted = {
        "uuid": "TEXT",
        "content_hash": "TEXT",
        "mtime": "REAL",
        "last_indexed": "TEXT"
    }
    for name, ctype in wanted.items():
        if name not in colnames:
            db.execute(f"ALTER TABLE articles ADD COLUMN {name} {ctype}")

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def importArticles(force=False):
    DBase.initSchema()
    db = DBase.connect()
    verfyColumn(db)  # adds uuid, content_hash, mtime, last_indexed if missing

    allowed = {".md", ".markdown", ".txt", ".json"}
    files = sorted(PAGEDIR.rglob("*"))
    inserted = 0
    updated = 0
    skipped = 0
    any_changed = False
    now_iso = datetime.now(timezone.utc).isoformat()

    for p in files:
        if not p.is_file() or p.suffix.lower() not in allowed:
            continue

        relative = p.relative_to(PAGEDIR)
        parts = relative.parts

        slug = slugify(p.stem)

        raw = p.read_text(encoding="utf-8")
        meta, body = parseMD(raw)

        # title preference: frontmatter 'title' -> first H1 -> filename
        if meta.get("title"):
            title = str(meta["title"]).strip()
        else:
            m = re.search(r"^#\s+(.+)$", body, flags=re.M)
            title = m.group(1).strip() if m else p.stem.replace("-", " ").replace("_", " ").title()

        # created preference: frontmatter 'date' -> folder YYYY/MM/DD -> file mtime
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
        elif len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
            try:
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

        # fetch existing row if any
        row = db.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
        if not row:
            # insert new
            db.execute(
                "INSERT INTO articles (slug, title, content, created, uuid, content_hash, mtime, last_indexed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (slug, title, content_to_store, created, uuid_val, content_hash, file_mtime, now_iso)
            )
            inserted += 1
            any_changed = True
        else:
            # decide if update needed
            need_update = force
            # compare important fields (handle None)
            if not need_update:
                # content change
                if (row["content_hash"] or "") != content_hash:
                    need_update = True
                # mtime change (filesystem-level)
                elif (row["mtime"] is None) or (float(row["mtime"]) != float(file_mtime)):
                    need_update = True
                # title changed in frontmatter or H1
                elif (row["title"] or "") != (title or ""):
                    need_update = True
                # created/date changed
                elif (row["created"] or "") != (created or ""):
                    need_update = True
                # uuid changed
                elif (row["uuid"] or "") != (uuid_val or ""):
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

    db.commit()

    # clear caches only if any change happened
    if any_changed:
        try:
            articleSlug.cache_clear()
            articlePage.cache_clear()
        except Exception:
            # lru_cache exists, but be defensive
            pass

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "force": bool(force)}

# Caching
@lru_cache(maxsize=512)
def articleSlug(slug: str):
    db = DBase.connect()
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
        "snippet": text_snippet(row["content"])
    }

@lru_cache(maxsize=128)
def articlePage(page: int, q: str = ""):
    db = DBase.connect()
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
            "snippet": text_snippet(r["content"])
        })
    return {"items": items, "total": total, "page": page, "PAGESHOW": PAGESHOW}

# ---------------- routes ----------------
@app.route("/admin/import")
def importPage():
    force = str(request.args.get("force", "")).lower() in ("1", "true", "yes")
    inserted = importArticles(force=force)
    return jsonify({"inserted": inserted, "force": force})

@app.route("/admin/reset")
def resetPage():
    force = str(request.args.get("force", "")).lower() in ("1", "true", "yes")
    DBase.reset()
    inserted = importArticles(force=force)
    return jsonify({"inserted": inserted, "force": force})

@app.route("/api/article")
def getArticle():
    page = max(1, int(request.args.get("page", 1)))
    q = request.args.get("q", "").strip()
    data = articlePage(page, q)
    return jsonify(data)

@app.route("/api/article/<slug>")
def slugArticle(slug):
    art = articleSlug(slug)
    if not art:
        return abort(404)
    return jsonify(art)

@app.route("/")
def home():
    page = max(1, int(request.args.get("page", 1)))
    q = request.args.get("q", "").strip()
    data = articlePage(page, q)
    return render_template("index.html", articles=data["items"], page=page, total=data["total"], q=q)

@app.route("/article/<slug>")
def read(slug):
    art = articleSlug(slug)
    if not art:
        return abort(404)
    return render_template("article.html", article=art)

# static files served automatically by Flask via app.static_folder

if __name__ == "__main__":
    # always reindex on startup (force=True)
    with app.app_context():
        inserted = importArticles(force=True)
        print(f"Indexed articles: {inserted}")
    app.run(host="0.0.0.0", port=5000, debug=True)