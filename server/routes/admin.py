from flask import Blueprint, request, jsonify
from articles import importArticles, articleSlug, articlePage
from db import DB
from config import DB_FILE

bp = Blueprint('admin', __name__)

DBPages = DB(DB_FILE)

@bp.route('/admin/import')
def importPage():
    force = str(request.args.get('force', '')).lower() in ('1', 'true', 'yes')
    res = importArticles(force=force)
    return jsonify(res)

@bp.route('/admin/reset')
def resetPage():
    force = str(request.args.get('force', '')).lower() in ('1', 'true', 'yes')
    DBPages.reset()
    res = importArticles(force=force)
    try:
        articleSlug.cache_clear()
        articlePage.cache_clear()
    except Exception:
        pass
    return jsonify(res)