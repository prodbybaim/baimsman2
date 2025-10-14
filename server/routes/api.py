from flask import Blueprint, request, jsonify, render_template
from typing import Any
from dbapi import ReadsAPI
from errors import register_error_handlers

bp = Blueprint('api', __name__)
register_error_handlers(bp)

def error(code: int, message: str): # complete
    return render_template('error.html', code=code, message=message), code

@bp.route('/api/page/add', methods=['POST']) # complete
def readsAdd():
    if not request.is_json:
        return error(400, "Invalid request: JSON body required.")

    data: dict[str, Any] = request.get_json(force=True)
    
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    creator = (data.get('creator') or 'admin')
    type_ = (data.get('type') or 'article')

    uid = ReadsAPI.add(title,creator,content,type_)
    
    if uid is None:
        return error(500, "Failed to create read: unsupported add() signature.")

    return jsonify({"status": "success", "uuid": uid})

@bp.route('/api/baca/<slug>', methods=['GET']) # complete
def readsGet(slug: str):
    r = ReadsAPI()
    for fn in ("read", "get", "fetch_one", "get_by_uuid"):
        if hasattr(r, fn):
            try:
                result = getattr(r, fn)(slug)
                if result:
                    return jsonify(result)
            except Exception:
                pass
    result = ReadsAPI.read(slug)
    preview = None
    if hasattr(r, "preview"):
        preview = getattr(r, "preview")(slug)
    if preview:
        return jsonify(preview)
    return error(404, "Bacaan tidak ditemukan.")

@bp.route('/api/page/update/<slug>', methods=['POST']) # complete
def readsUpdate(slug: str):
    if not request.is_json:
        return error(400, "Invalid request: JSON body required.")
    data: dict[str, Any] = request.get_json(force=True)
    title = data.get('title')
    content = data.get('content')
    creator = data.get('creator')
    type_ = data.get('type')

    r = ReadsAPI()
    update_fn = None
    for fn in ("update", "edit", "modify"):
        if hasattr(r, fn):
            update_fn = getattr(r, fn)
            break
    if not update_fn:
        return error(501, "Update not supported by ReadsAPI.")

    try:
        kwargs = {}
        if title is not None: kwargs['title'] = title
        if content is not None: kwargs['content'] = content
        if creator is not None: kwargs['creator'] = creator
        if type_ is not None: kwargs['type_'] = type_
        try:
            ok = update_fn(slug, **kwargs)
        except TypeError:
            ok = update_fn(slug, kwargs.get('title'), kwargs.get('content'), kwargs.get('creator'), kwargs.get('type_'))
    except Exception as e:
        return error(500, f"Failed to update read: {e}")

    if not ok:
        return error(404, "Read not found or not updated.")
    return jsonify({"status": "success"})

@bp.route('/api/page/delete/<slug>', methods=['DELETE']) # complete
def readsDelete(slug: str):
    r = ReadsAPI()
    delete_fn = None
    for fn in ("delete", "remove", "delete_by_uuid"):
        if hasattr(r, fn):
            delete_fn = getattr(r, fn)
            break
    if not delete_fn:
        return error(501, "Delete not supported by ReadsAPI.")
    try:
        ok = delete_fn(slug)
    except Exception as e:
        return error(500, f"Failed to delete read: {e}")
    if not ok:
        return error(404, "Read not found.")
    return jsonify({"status": "success"})

@bp.route('/api/page/import') # complete
def readsImport():
    res = ReadsAPI.importFromDir
    return jsonify({"status": "berhasil"})
