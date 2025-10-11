from flask import render_template


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message='Page Not Found'), 404

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('error.html', code=401, message='Unauthorized Access'), 401

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('error.html', code=400, message='Bad Request'), 400

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500, message='Internal Server Error'), 500

    @app.errorhandler(Exception)
    def handle_any(e):
        code = getattr(e, 'code', 500)
        msg = str(e) or 'Unexpected Error'
        return render_template('error.html', code=code, message=msg), code