from flask import Blueprint, request, jsonify, abort, render_template, redirect, url_for, session, current_app
from articles import importArticles, articleSlug, articlePage
from server.dbutils import DB
from config import DB_FILE, DB_AUTH_FILE, PAGEDIR, ADMIN_REGISTER_TOKEN, SESSION_LIFETIME_DAYS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import os

bp = Blueprint('admin', __name__)

DBPages = DB(DB_FILE)
DBAuth = DB(DB_AUTH_FILE)


def ensure_auth_table():
    DBAuth.initDB(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created TEXT
        );
        """
    )


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*a, **kw):
        if session.get('admin_user'):
            return fn(*a, **kw)
        return redirect(url_for('admin.login'))

    return wrapper


def require_role(*roles):
    """Decorator: allow only users whose role is in `roles`.
    Ensures user is logged in and checks session DB for role if missing.
    """
    from functools import wraps

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            username = session.get('admin_user')
            if not username:
                return redirect(url_for('admin.login'))
            role = session.get('admin_role')
            if role is None:
                # attempt to read role from DB and cache in session
                try:
                    db = DBAuth.connect()
                    row = db.execute('SELECT role FROM users WHERE username = ?', (username,)).fetchone()
                    role = row['role'] if row else None
                    session['admin_role'] = role
                except Exception:
                    role = None
            if role not in roles:
                return abort(401)
            return fn(*a, **kw)

        return wrapper

    return deco


@bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    ensure_auth_table()
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        db = DBAuth.connect()
        row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if not row:
            error = 'Invalid username or password'
        else:
            if check_password_hash(row['password'], password):
                session['admin_user'] = username
                # cache role in session
                session['admin_role'] = row.get('role', 'editor') if row else 'editor'
                if remember:
                    session.permanent = True
                    current_app.permanent_session_lifetime = timedelta(days=SESSION_LIFETIME_DAYS)
                else:
                    session.permanent = False
                return redirect(url_for('admin.panel'))
            else:
                error = 'Invalid username or password'

    return render_template('login.html', error=error)


@bp.route('/admin/logout')
def logout():
    session.pop('admin_user', None)
    return redirect(url_for('admin.login'))


@bp.route('/admin/register', methods=['POST'])
def register():
    """Register a new admin user. Protected by ADMIN_REGISTER_TOKEN.
    Body JSON: { username, password, token }
    """
    ensure_auth_table()
    data = request.get_json(force=True) or {}
    token = data.get('token')
    if token != ADMIN_REGISTER_TOKEN:
        return jsonify({'error': 'unauthorized'}), 403
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = (data.get('role') or 'admin').lower()
    if role not in ('admin', 'editor'):
        return jsonify({'error': 'invalid role'}), 400
    if not username or not password:
        return jsonify({'error': 'invalid input'}), 400

    # only allow creating admin via the token route; editors can be created by admins later
    if role == 'admin' and token != ADMIN_REGISTER_TOKEN:
        return jsonify({'error': 'unauthorized for admin role'}), 403

    db = DBAuth.connect()
    try:
        db.execute('INSERT INTO users (username, password, role, created) VALUES (?, ?, ?, ?)',
                   (username, generate_password_hash(password), role, datetime.utcnow().isoformat()))
        db.commit()
    except Exception as e:
        return jsonify({'error': 'could not create user', 'details': str(e)}), 400
    return jsonify({'ok': True, 'username': username, 'role': role})


@bp.route('/admin/panel')
@login_required
def panel():
    # simple control panel UI
    # read role from session or DB
    user_role = session.get('admin_role')
    if user_role is None:
        try:
            db = DBAuth.connect()
            row = db.execute('SELECT role FROM users WHERE username = ?', (session.get('admin_user'),)).fetchone()
            user_role = row['role'] if row else 'editor'
            session['admin_role'] = user_role
        except Exception:
            user_role = 'editor'
    return render_template('panel.html', user={'username': session.get('admin_user'), 'role': user_role})


# Article management APIs
@bp.route('/admin/articles/list')
@login_required
def list_articles():
    db = DBPages.connect()
    rows = db.execute('SELECT id, slug, title, created FROM articles ORDER BY created DESC').fetchall()
    items = [dict(r) for r in rows]
    return jsonify(items)


@bp.route('/admin/users')
@require_role('admin')
def list_users():
    ensure_auth_table()
    db = DBAuth.connect()
    rows = db.execute('SELECT id, username, role, created FROM users ORDER BY created DESC').fetchall()
    items = [dict(r) for r in rows]
    return jsonify(items)


@bp.route('/admin/users/<username>', methods=['PUT'])
@require_role('admin')
def update_user(username):
    ensure_auth_table()
    data = request.get_json(force=True) or {}
    role = (data.get('role') or '').lower()
    if role not in ('admin', 'editor'):
        return jsonify({'error': 'invalid role'}), 400
    db = DBAuth.connect()
    row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404
    db.execute('UPDATE users SET role = ? WHERE username = ?', (role, username))
    db.commit()
    # clear session role for changed user if it's the current session
    if session.get('admin_user') == username:
        session['admin_role'] = role
    return jsonify({'ok': True, 'username': username, 'role': role})


@bp.route('/admin/articles/create', methods=['POST'])
@login_required
def create_article():
    """Create an article file under PAGEDIR with a UUID filename and YAML front matter.
    Expects JSON: { title, content, created_by }
    """
    data = request.get_json(force=True) or {}
    title = (data.get('title') or '').strip()
    content = data.get('content') or ''
    created_by = (data.get('created_by') or session.get('admin_user'))
    if not title or not content:
        return jsonify({'error': 'title and content required'}), 400

    # create folder structure by date
    now = datetime.utcnow()
    folder = Path(PAGEDIR) / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
    folder.mkdir(parents=True, exist_ok=True)

    uid = str(uuid.uuid4())
    filename = folder / f"{uid}.md"
    fm = f"---\ntitle: \"{title.replace('"', '\\"')}\"\ncreated: {now.isoformat()}\ncreated_by: {created_by}\n---\n\n"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(fm)
            f.write(content)
    except Exception as e:
        return jsonify({'error': 'could not write file', 'details': str(e)}), 500

    # after creating file, run importArticles to pick it up
    res = importArticles(force=True)
    try:
        articleSlug.cache_clear()
        articlePage.cache_clear()
    except Exception:
        pass

    return jsonify({'ok': True, 'file': str(filename), 'imported': res})


@bp.route('/admin/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_article(article_id):
    db = DBPages.connect()
    row = db.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404
    db.execute('DELETE FROM articles WHERE id = ?', (article_id,))
    db.commit()
    try:
        articleSlug.cache_clear()
        articlePage.cache_clear()
    except Exception:
        pass
    return jsonify({'ok': True})


@bp.route('/admin/articles/<int:article_id>', methods=['PUT'])
@login_required
def edit_article(article_id):
    data = request.get_json(force=True) or {}
    title = data.get('title')
    content = data.get('content')
    db = DBPages.connect()
    row = db.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404
    if title:
        db.execute('UPDATE articles SET title = ? WHERE id = ?', (title, article_id))
    if content is not None:
        db.execute('UPDATE articles SET content = ? WHERE id = ?', (content, article_id))
    db.commit()
    try:
        articleSlug.cache_clear()
        articlePage.cache_clear()
    except Exception:
        pass
    return jsonify({'ok': True})