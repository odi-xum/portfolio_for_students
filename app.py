"""
Точка входа. Создаёт Flask-приложение, регистрирует маршруты.
CSRF-защита, безопасные заголовки, управление сессиями.
"""
import os
from flask import Flask, render_template, request, abort
from flask_login import LoginManager
from models import db, User
from helpers import BASE_UPLOAD_FOLDER, generate_csrf_token, verify_csrf_token
from routes import register_routes


def create_app():
    # Подавляем инфо-логи werkzeug (варнинг про dev server и логи запросов)
    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    app = Flask(__name__)

    # Конфигурация из окружения / по умолчанию
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY',
        'gruvbox-material-secure-shadow-key-1984')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
        'sqlite:///database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = BASE_UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 ч
    app.config['SESSION_PERMANENT'] = True

    db.init_app(app)

    # SQLite — WAL mode + NORMAL sync для конкурентного чтения/записи
    # Регистрируем слушатель внутри контекста приложения (Flask-SQLAlchemy 3.x)
    with app.app_context():
        from sqlalchemy import event
        @event.listens_for(db.engine, 'connect')
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA synchronous=NORMAL')
            cursor.close()

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------
    # CSRF — проверка для POST/PUT/DELETE (кроме потоковых/файловых)
    # ------------------------------------------------------------------
    @app.before_request
    def csrf_check():
        if request.method in ('POST', 'PUT', 'DELETE'):
            if request.path.startswith('/api/notifications/stream'):
                return
            if request.path.startswith('/admin/import_'):
                return
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or not verify_csrf_token(token):
                abort(400, 'CSRF-токен недействителен')

    # ------------------------------------------------------------------
    # Защитные заголовки
    # ------------------------------------------------------------------
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not request.path.startswith('/portfolio/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    register_routes(app)

    # ------------------------------------------------------------------
    # Обработчики ошибок
    # ------------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    # CSRF-токен доступен во всех шаблонах как {{ csrf_token }}
    @app.context_processor
    def inject_csrf():
        return {'csrf_token': generate_csrf_token()}

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug)
