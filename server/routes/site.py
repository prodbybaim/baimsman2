from flask import Blueprint, render_template, request, abort
from articles import articlePage, articleSlug

bp = Blueprint('site', __name__)

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