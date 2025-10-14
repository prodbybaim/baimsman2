from flask import Blueprint, request, jsonify, render_template
from typing import Any
from dbapi import readsAPI, DBService
from errors import register_error_handlers

bp = Blueprint('api', __name__)
register_error_handlers(bp)

def error(code: int, message: str):
    return render_template('error.html', code=code, message=message), code

@bp.route('/api/reads/add', methods=['POST'])
def readsAdd():
    if not request.is_json:
        return error(400, "Invalid request: JSON body required.")
    data: dict[str, Any] = request.get_json(force=True)
    title = data.get('title', 'No Title')
    content = data.get('content', 'No Content.')
    readsAPI().add(title=title, content=content)
    return jsonify({"status": "success"})

@bp.route('/api/reads/preview/<slug>', methods=['GET'])
def readsPreview(slug: str):
    preview = readsAPI().preview(slug)
    if not preview:
        return error(404, "Read not found.")
    return jsonify(preview)

@bp.route('/api/rebuild', methods=['GET'])
def DBRebuild():
    success = DBService().rebuild()
    if not success:
        return error(500, "Failed to rebuild data base from directory.")
    return jsonify({"status": "success"})
