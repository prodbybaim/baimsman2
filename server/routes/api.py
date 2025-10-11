from flask import Blueprint, request, jsonify, abort
from articles import articlePage, articleSlug

bp = Blueprint('api', __name__)

@bp.route('/api/article')
def getArticle():
    page = max(1, int(request.args.get('page', 1)))
    q = request.args.get('q', '').strip()
    data = articlePage(page, q)
    return jsonify(data)

@bp.route('/api/article/<slug>')
def slugArticle(slug):
    art = articleSlug(slug)
    if not art:
        return abort(404)
    return jsonify(art)