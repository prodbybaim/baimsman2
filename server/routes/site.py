from flask import Blueprint, render_template, request, abort, url_for, Response
from datetime import datetime
from dbapi import NewsAPI
from dbutils import DB
from config import DB_FILE
from utils import text_snippet

bp = Blueprint('site', __name__)
pagedb = NewsAPI()
dbutils = DB(DB_FILE)

@bp.route('/')
def home():
    page = max(1, int(request.args.get('page', 1)))
    q = request.args.get('q', '').strip()
    data = pagedb.preview(offset=(page*10)-10, query=q, limit=10)
    return render_template(
        'index.html',
        articles=data['items'],
        page=page,
        total=data['total'],
        q=q
    )


@bp.route('/article/<slug>')
def read(slug):
    art = pagedb.fetch(uuid=slug)
    if not art:
        return abort(404)
    return render_template('article.html', article=art)


"""@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    Simple contact form stored as messages via content_api.

    pagedb.connect().executescript(
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            message TEXT,
            created TEXT
        );
    )

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        message = (request.form.get('message') or '').strip()
        if not message:
            return render_template(
                'contact.html',
                error='Message is required',
                success=False,
                form={'name': name, 'email': email, 'message': message}
            )
        created = datetime.utcnow().isoformat() + 'Z'
        db.connect().execute(
            "INSERT INTO messages (name, email, message, created) VALUES (?, ?, ?, ?)",
            (name, email, message, created)
        )
        db.connect().commit()
        return render_template('contact.html', success=True)
    return render_template('contact.html')"""


@bp.route('/sitemap.xml')
def sitemap():
    """Generate sitemap using articles from content_api."""
    rows = pagedb.fetch_all()
    host = request.host_url.rstrip('/')
    urls = []
    for r in rows:
        lastmod = r.get('created_at', '')
        slug = r.get('slug') or r.get('uuid')
        urls.append(f"  <url>\n    <loc>{host}{url_for('site.read', slug=slug)}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>")
    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n{ '\n'.join(urls) }\n</urlset>"
    return Response(xml, mimetype='application/xml')


@bp.route('/rss.xml')
def rss():
    """RSS feed built from content_api.article."""
    rows = article.fetch_latest(limit=20)
    host = request.host_url.rstrip('/')
    items = []
    for r in rows:
        slug = r.get('slug') or r.get('uuid')
        link = f"{host}{url_for('site.read', slug=slug)}"
        title = (r.get('title') or '')
        pubDate = r.get('created_at') or ''
        desc = text_snippet(r.get('content') or '', length=300)
        items.append(f"<item>\n  <title>{title}</title>\n  <link>{link}</link>\n  <guid>{link}</guid>\n  <pubDate>{pubDate}</pubDate>\n  <description>{desc}</description>\n</item>")
    rss_xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<rss version=\"2.0\">\n<channel>\n  <title>SMAN 2 Cikpus - Latest Articles</title>\n  <link>{host}{url_for('site.home')}</link>\n  <description>Latest posts from SMAN 2 Cikpus</description>\n  { '\n  '.join(items) }\n</channel>\n</rss>"
    return Response(rss_xml, mimetype='application/rss+xml')
