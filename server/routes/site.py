from flask import Blueprint, render_template, request, abort, url_for, Response, current_app
from typing import Any, List, Dict
from pathlib import Path
from datetime import datetime
from email.utils import format_datetime
from dbapi import ReadsAPI  # keep as-is (module/class in your project)
from config import PREVIEWLIMIT, PREVIEWWORD
from utils import text_snippet

bp = Blueprint("site", __name__)

# Simple in-memory TTL cache to avoid repeated disk/DB hits on high-traffic pages.
# Key -> (timestamp_epoch, value). TTL seconds can be tuned.
_cache: Dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 5.0  # seconds


def _cache_get(key: str):
    import time
    entry = _cache.get(key)
    if not entry:
        return None
    ts, val = entry
    if time.time() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return val


def _cache_set(key: str, value: Any):
    import time
    _cache[key] = (time.time(), value)


def _get_reads_instance():
    """
    Helper that returns either an instance or the class/module providing fetch/read/etc.
    This makes the routes tolerant to both patterns.
    """
    try:
        inst = ReadsAPI()
    except Exception:
        inst = ReadsAPI
    return inst


@bp.route("/")
def home():
    q = request.args.get('q', '') or ''
    page = max(1, int(request.args.get('page',1)))
    limit = 10
    offset = (page - 1) * limit
    data = ReadsAPI.pageList(offset,limit,q)
    items = data.get("items", [])
    
    return render_template(
        "index.html",
        articles=items,
        page=page,
        total=len(items),
        q=q,
        limit=limit,
    )


@bp.route("/article/<slug>")
def read(slug: str):
    """
    Full read page. Try read(), then preview() as fallback.
    """
    r = _get_reads_instance()
    art = None
    # try common method names
    for fn in ("read", "get", "fetch_one", "get_by_uuid"):
        if hasattr(r, fn):
            try:
                art = getattr(r, fn)(slug)
                if art:
                    break
            except Exception:
                art = None

    # fallback to preview
    if not art and hasattr(r, "preview"):
        art = getattr(r, "preview")(slug)

    if not art:
        return abort(404)

    # If content stored as markdown file, ensure template gets rendered HTML if needed
    # (Assumes ReadsAPI.read returns dict with 'content' or raw markdown; adapt if otherwise.)
    return render_template("article.html", article=art)


@bp.route("/sitemap.xml")
def sitemap():
    """
    Sitemap generated from readsAPI.fetch(). Uses 'created' or 'created_at' if present.
    """
    r = _get_reads_instance()
    try:
        data = getattr(r, "fetch")(offset=0, limit=10000, query="")  # try to fetch a large batch
    except TypeError:
        data = getattr(r, "fetch")(0, 10000, "")

    items = data.get("items", []) if isinstance(data, dict) else data or []
    host = request.host_url.rstrip("/")
    urls: List[str] = []
    for rec in items:
        slug = rec.get("slug") or rec.get("uuid") or rec.get("id")
        if not slug:
            continue
        # prefer ISO timestamp fields
        lastmod = rec.get("created") or rec.get("created_at") or rec.get("mtime") or ""
        # if it's a timestamp/number, convert to RFC3339-like string
        if isinstance(lastmod, (int, float)):
            lastmod = datetime.utcfromtimestamp(float(lastmod)).isoformat() + "Z"
        urls.append(
            "  <url>\n"
            f"    <loc>{host}{url_for('site.read', slug=slug)}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            "  </url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@bp.route("/rss.xml")
def rss():
    """
    RSS feed built from latest reads.
    Uses fetch(offset=0, limit=20).
    """
    r = _get_reads_instance()
    try:
        data = getattr(r, "fetch")(offset=0, limit=20, query="")
    except TypeError:
        data = getattr(r, "fetch")(0, 20, "")

    items = data.get("items", []) if isinstance(data, dict) else data or []
    host = request.host_url.rstrip("/")
    rss_items: List[str] = []
    for rec in items:
        slug = rec.get("slug") or rec.get("uuid") or rec.get("id")
        if not slug:
            continue
        link = f"{host}{url_for('site.read', slug=slug)}"
        title = (rec.get("title") or "").strip()
        pub_iso = rec.get("created") or rec.get("created_at") or rec.get("mtime") or ""
        # try to format pubDate to RFC 2822 if possible
        pub_date = pub_iso
        try:
            if isinstance(pub_iso, (int, float)):
                pub_date = format_datetime(datetime.utcfromtimestamp(pub_iso))
            elif isinstance(pub_iso, str) and pub_iso:
                try:
                    dt = datetime.fromisoformat(pub_iso.replace("Z", "+00:00"))
                    pub_date = format_datetime(dt)
                except Exception:
                    pub_date = pub_iso
        except Exception:
            pub_date = ""

        desc = text_snippet(rec.get("content") or rec.get("preview") or "", length=300)
        rss_items.append(
            "<item>\n"
            f"  <title>{title}</title>\n"
            f"  <link>{link}</link>\n"
            f"  <guid>{link}</guid>\n"
            f"  <pubDate>{pub_date}</pubDate>\n"
            f"  <description>{desc}</description>\n"
            "</item>"
        )

    rss_xml = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        "<rss version=\"2.0\">\n<channel>\n"
        f"  <title>SMAN 2 Cikpus - Latest Articles</title>\n"
        f"  <link>{host}{url_for('site.home')}</link>\n"
        "  <description>Latest posts from SMAN 2 Cikpus</description>\n"
        + "\n  ".join(rss_items)
        + "\n</channel>\n</rss>"
    )
    return Response(rss_xml, mimetype="application/rss+xml")