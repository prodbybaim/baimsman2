from flask import (
    Blueprint,
    request,
    jsonify,
    abort,
    render_template,
    redirect,
    url_for,
    session,
    current_app,
    flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import uuid
import os
import html

from config import DB_FILE, PAGEDIR, ADMIN_REGISTER_TOKEN, SESSION_LIFETIME_DAYS
from dbapi import TeacherAPI  # keep if you need programmatic access to users
# optionally: from dbapi import readsAPI  # for importArticles if present

bp = Blueprint("admin", __name__)

DB_PATH = Path(DB_FILE)
PAGEDIR_PATH = Path(PAGEDIR)
PAGEDIR_PATH.mkdir(parents=True, exist_ok=True)


def _get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_auth_table() -> None:
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def ensure_pages_table() -> None:
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE,
            slug TEXT,
            title TEXT,
            content TEXT,
            created TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*a, **kw):
        if session.get("admin_user"):
            return fn(*a, **kw)
        return redirect(url_for("admin.login"))

    return wrapper


def require_role(*roles):
    from functools import wraps

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            username = session.get("admin_user")
            if not username:
                return redirect(url_for("admin.login"))
            role = session.get("admin_role")
            if role is None:
                try:
                    ensure_auth_table()
                    conn = _get_conn()
                    row = conn.execute(
                        "SELECT role FROM admin_users WHERE username = ?", (username,)
                    ).fetchone()
                    conn.close()
                    role = row["role"] if row else None
                    session["admin_role"] = role
                except Exception:
                    role = None
            if role not in roles:
                return abort(401)
            return fn(*a, **kw)

        return wrapper

    return deco


@bp.route("/admin/login", methods=["GET", "POST"])
def login():
    ensure_auth_table()
    error_msg = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        conn = _get_conn()
        row = conn.execute(
            "SELECT username, password, role FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()
        if not row or not check_password_hash(row["password"], password):
            error_msg = "Invalid username or password"
        else:
            session["admin_user"] = row["username"]
            session["admin_role"] = row.get("role", "editor")
            if remember:
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(
                    days=SESSION_LIFETIME_DAYS
                )
            else:
                session.permanent = False
            return redirect(url_for("admin.panel"))

    return render_template("login.html", error=error_msg)


@bp.route("/admin/logout")
def logout():
    session.pop("admin_user", None)
    session.pop("admin_role", None)
    return redirect(url_for("admin.login"))


@bp.route("/admin/register", methods=["POST"])
def register():
    """
    Register a new admin/editor user.
    Body JSON: { username, password, role, token }
    Protected by ADMIN_REGISTER_TOKEN for creating initial admin via API.
    """
    ensure_auth_table()
    data = request.get_json(force=True) or {}
    token = data.get("token")
    if token != ADMIN_REGISTER_TOKEN:
        return jsonify({"error": "unauthorized"}), 403

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "admin").lower()
    if role not in ("admin", "editor"):
        return jsonify({"error": "invalid role"}), 400
    if not username or not password:
        return jsonify({"error": "invalid input"}), 400

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO admin_users (username, password, role, created) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, datetime.utcnow().isoformat()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "user exists"}), 409
    except Exception as e:
        conn.close()
        return jsonify({"error": "could not create user", "details": str(e)}), 400
    conn.close()
    return jsonify({"ok": True, "username": username, "role": role})


@bp.route("/admin/panel")
@login_required
def panel():
    user_role = session.get("admin_role")
    if user_role is None:
        try:
            ensure_auth_table()
            conn = _get_conn()
            row = conn.execute(
                "SELECT role FROM admin_users WHERE username = ?",
                (session.get("admin_user"),),
            ).fetchone()
            conn.close()
            user_role = row["role"] if row else "editor"
            session["admin_role"] = user_role
        except Exception:
            user_role = "editor"
    return render_template(
        "panel.html", user={"username": session.get("admin_user"), "role": user_role}
    )


# Articles management ---------------------------------------------------------

@bp.route("/admin/articles/list")
@login_required
def list_articles():
    ensure_pages_table()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, uuid, slug, title, created FROM articles ORDER BY created DESC"
    ).fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return jsonify(items)


@bp.route("/admin/articles/create", methods=["POST"])
@login_required
def create_article():
    """
    Create article markdown file under PAGEDIR and optionally import it into DB.
    JSON body: { title, content, created_by }
    """
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    content = data.get("content") or ""
    created_by = (data.get("created_by") or session.get("admin_user")) or "admin"
    if not title or not content:
        return jsonify({"error": "title and content required"}), 400

    now = datetime.utcnow()
    folder = PAGEDIR_PATH / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
    folder.mkdir(parents=True, exist_ok=True)

    uid = str(uuid.uuid4())
    filename = folder / f"{uid}.md"

    # safe-escape quotes for YAML front-matter
    safe_title = html.escape(title).replace('"', '\\"')
    fm = (
        f"---\n"
        f"title: \"{safe_title}\"\n"
        f"created: {now.isoformat()}\n"
        f"created_by: {created_by}\n"
        f"uuid: {uid}\n"
        f"---\n\n"
    )
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(fm)
            f.write(content)
    except Exception as e:
        return jsonify({"error": "could not write file", "details": str(e)}), 500

    # optionally import the article into DB if import function available
    imported = 0
    try:
        # prefer readsAPI.importFromDir or similar
        from dbapi import ReadsAPI

        import_func = None
        for name in ("importFromDir", "import_from_dir", "import"):
            if hasattr(ReadsAPI, name):
                import_func = getattr(ReadsAPI, name)
                break
        if import_func:
            try:
                res = import_func()
                # import_func may return int/bool; normalize
                if isinstance(res, int):
                    imported = res
                elif isinstance(res, bool):
                    imported = 1 if res else 0
            except TypeError:
                # call without args
                try:
                    res = import_func()
                    if isinstance(res, int):
                        imported = res
                    elif isinstance(res, bool):
                        imported = 1 if res else 0
                except Exception:
                    imported = 0
    except Exception:
        imported = 0

    # attempt to clear caches if present
    try:
        from functools import lru_cache

        # if you have functions cached with lru_cache, expose names and clear them
        for fn_name in ("articleSlug", "articlePage"):
            obj = globals().get(fn_name)
            if obj and hasattr(obj, "cache_clear"):
                obj.cache_clear()
    except Exception:
        pass

    return jsonify({"ok": True, "file": str(filename), "imported": imported})


@bp.route("/admin/articles/<int:article_id>", methods=["DELETE"])
@login_required
def delete_article(article_id):
    ensure_pages_table()
    conn = _get_conn()
    row = conn.execute("SELECT uuid, slug, title FROM articles WHERE id = ?", (article_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404

    conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()

    # attempt to clear caches if present
    try:
        for fn_name in ("articleSlug", "articlePage"):
            obj = globals().get(fn_name)
            if obj and hasattr(obj, "cache_clear"):
                obj.cache_clear()
    except Exception:
        pass

    return jsonify({"ok": True})


@bp.route("/admin/articles/<int:article_id>", methods=["PUT"])
@login_required
def edit_article(article_id):
    ensure_pages_table()
    data = request.get_json(force=True) or {}
    title = data.get("title")
    content = data.get("content")

    conn = _get_conn()
    row = conn.execute("SELECT id FROM articles WHERE id = ?", (article_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404

    if title:
        conn.execute("UPDATE articles SET title = ? WHERE id = ?", (title, article_id))
    if content is not None:
        conn.execute("UPDATE articles SET content = ? WHERE id = ?", (content, article_id))
    conn.commit()
    conn.close()

    try:
        for fn_name in ("articleSlug", "articlePage"):
            obj = globals().get(fn_name)
            if obj and hasattr(obj, "cache_clear"):
                obj.cache_clear()
    except Exception:
        pass

    return jsonify({"ok": True})


# Users management ------------------------------------------------------------

@bp.route("/admin/users")
@require_role("admin")
def list_users():
    ensure_auth_table()
    conn = _get_conn()
    rows = conn.execute("SELECT username, role, created FROM admin_users ORDER BY created DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@bp.route("/admin/users/<username>", methods=["PUT"])
@require_role("admin")
def update_user(username):
    ensure_auth_table()
    data = request.get_json(force=True) or {}
    role = (data.get("role") or "").lower()
    if role not in ("admin", "editor"):
        return jsonify({"error": "invalid role"}), 400

    conn = _get_conn()
    row = conn.execute("SELECT username FROM admin_users WHERE username = ?", (username,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404

    conn.execute("UPDATE admin_users SET role = ? WHERE username = ?", (role, username))
    conn.commit()
    conn.close()

    if session.get("admin_user") == username:
        session["admin_role"] = role

    return jsonify({"ok": True, "username": username, "role": role})

@bp.route("/admin/teachers/add", methods=["GET", "POST"])
@require_role("admin", "editor")
def add_teacher():
    if request.method == "GET":
        return render_template("admin/teacher_form.html")  # create this template

    # POST (form or JSON)
    data = request.get_json(silent=True) or request.form or {}
    name = (data.get("name") or "").strip()
    subject = (data.get("subject") or "").strip()
    bio = (data.get("bio") or "").strip()
    role = (data.get("role") or "teacher").strip()

    if not name:
        if request.is_json:
            return jsonify({"error": "name is required"}), 400
        flash("Name is required", "danger")
        return redirect(url_for("admin.add_teacher"))

    try:
        tid = TeacherAPI.add(name=name, subject=subject, bio=bio, role=role)
    except Exception as e:
        if request.is_json:
            return jsonify({"error": "failed to add teacher", "details": str(e)}), 500
        flash(f"Failed to add teacher: {e}", "danger")
        return redirect(url_for("admin.add_teacher"))

    # Success: JSON -> return id; Form -> redirect to teacher list or detail
    if request.is_json:
        return jsonify({"ok": True, "id": tid})
    flash("Teacher added.", "success")
    return redirect(url_for("admin.list_teachers"))


# simple listing route (optional) for admin UI
@bp.route("/admin/teachers", methods=["GET"])
@require_role("admin", "editor")
def list_teachers():
    teachers = TeacherAPI.list(offset=0, limit=1000)  # page support can be added
    return render_template("admin/teachers_list.html", teachers=teachers)