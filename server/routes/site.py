from flask import Blueprint, render_template, request, abort, url_for, Response, redirect
from articles import articlePage, articleSlug
from db import DB
from config import DB_FILE
from datetime import datetime

bp = Blueprint('site', __name__)


DBPages = DB(DB_FILE)


@bp.route('/')
def home():
    page = max(1, int(request.args.get('page', 1)))
    q = request.args.get('q', '').strip()
    data = articlePage(page, q)
    return render_template('index.html', articles=data['items'], page=page, total=data['total'], q=q)


@bp.route('/article/<slug>')
def read(slug):
    art = articleSlug(slug)
    if not art:
        return abort(404)
    return render_template('article.html', article=art)


@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Simple contact form: stores messages to the articles DB in a `messages` table.
    This avoids external services and keeps user data local.
    """
    DBPages.initDB(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            message TEXT,
            created TEXT
        );
        """
    )
    db = DBPages.connect()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        message = (request.form.get('message') or '').strip()
        if not message:
            return render_template('contact.html', error='Message is required', success=False, form={'name': name, 'email': email, 'message': message})
        created = datetime.utcnow().isoformat() + 'Z'
        db.execute("INSERT INTO messages (name, email, message, created) VALUES (?, ?, ?, ?)", (name, email, message, created))
        db.commit()
        return render_template('contact.html', success=True)
    return render_template('contact.html')


@bp.route('/sitemap.xml')
def sitemap():
    """Generate a simple sitemap of all articles (using created as lastmod)."""
    db = DBPages.connect()
    rows = db.execute("SELECT slug, created FROM articles ORDER BY created DESC").fetchall()
    host = request.host_url.rstrip('/')
    urls = []
    for r in rows:
        lastmod = r['created'] or ''
        urls.append(f"  <url>\n    <loc>{host}{url_for('site.read', slug=r['slug'])}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>")
    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n{ '\n'.join(urls) }\n</urlset>"
    return Response(xml, mimetype='application/xml')


@bp.route('/rss.xml')
def rss():
    """Simple RSS feed for latest articles."""
    db = DBPages.connect()
    rows = db.execute("SELECT slug, title, content, created FROM articles ORDER BY created DESC LIMIT 20").fetchall()
    host = request.host_url.rstrip('/')
    items = []
    for r in rows:
        link = f"{host}{url_for('site.read', slug=r['slug'])}"
        title = (r['title'] or '')
        pubDate = r['created'] or ''
        # snippet safe (strip tags): reuse simple util
        from utils import text_snippet
        desc = text_snippet(r['content'] or '', length=300)
        items.append(f"<item>\n  <title>{title}</title>\n  <link>{link}</link>\n  <guid>{link}</guid>\n  <pubDate>{pubDate}</pubDate>\n  <description>{desc}</description>\n</item>")
    rss_xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<rss version=\"2.0\">\n<channel>\n  <title>SMAN 2 Cikpus - Latest Articles</title>\n  <link>{host}{url_for('site.home')}</link>\n  <description>Latest posts from SMAN 2 Cikpus</description>\n  { '\n  '.join(items) }\n</channel>\n</rss>"
    return Response(rss_xml, mimetype='application/rss+xml')