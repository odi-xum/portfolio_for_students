"""
conftest.py — фикстуры для тестов.
Каждый тест — свежее приложение с in-memory БД.
"""
from __future__ import annotations

import sys
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

sys.path.insert(0, '')

from constants import UserRole
from models import db, User, Event, Group, Specialty, Department
from helpers import generate_csrf_token, verify_csrf_token


TEST_PASSWORD = '111'
TEST_PASSWORD_HASH = generate_password_hash(TEST_PASSWORD)


@pytest.fixture(scope='function')
def app() -> Generator[Flask, None, None]:
    import os as _os
    _base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    app = Flask(__name__,
                template_folder=_os.path.join(_base, 'templates'),
                static_folder=_os.path.join(_base, 'static'))
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SERVER_NAME'] = 'test.local'

    db.init_app(app)

    # CSRF
    @app.before_request
    def csrf_check():
        from flask import request, abort, session
        if request.method in ('POST', 'PUT', 'DELETE'):
            if request.path.startswith('/api/notifications/stream'):
                return
            if request.path.startswith('/admin/import_'):
                return
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or not verify_csrf_token(token):
                abort(400, 'CSRF-токен недействителен')

    # LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # CSRF-токен доступен в шаблонах
    @app.context_processor
    def inject_csrf():
        return {'csrf_token': generate_csrf_token()}

    # Безопасные заголовки
    @app.after_request
    def security_headers(response):
        from flask import request
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not request.path.startswith('/portfolio/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    # Обработчики ошибок
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('500.html'), 500

    # Маршруты
    from routes import register_routes
    register_routes(app)

    with app.app_context():
        db.create_all()
        _seed_test_data()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app: Flask) -> FlaskClient:
    return app.test_client()


# ── Аутентифицированные клиенты ───────────────────────────────────────

def _login(client: FlaskClient, username: str):
    """Выполняет вход через тестовый клиент, передавая CSRF-токен."""
    with client:
        resp = client.get('/')
        csrf_token = ''
        with client.session_transaction() as sess:
            csrf_token = sess.get('_csrf_token', '')
        client.post('/', data={
            'username': username,
            'password': TEST_PASSWORD,
            '_csrf_token': csrf_token,
        })


@pytest.fixture(scope='function')
def admin_client(app, client):
    _login(client, 'admin')
    return client


@pytest.fixture(scope='function')
def student_client(app, client):
    _login(client, 'student1')
    return client


@pytest.fixture(scope='function')
def curator_client(app, client):
    _login(client, 'cur1')
    return client


# ── Seed-данные ───────────────────────────────────────────────────────

def _seed_test_data():
    db.session.add(Department(id=1, name='ИТ-отделение'))
    db.session.add(Specialty(id=1, name='Информационные системы и программирование',
                             code='09.02.07', abbreviation='ИСП', department_id=1))
    db.session.add(Group(id=1, name='ИСП-Б-2022', specialty_id=1,
                         specialty_name='Информационные системы и программирование',
                         specialty_code='09.02.07', budget_type='бюджет',
                         start_year=2022, course=4, department='ИТ-отделение',
                         curator_id=3))
    db.session.flush()

    db.session.add_all([
        User(id=1, username='admin', password_hash=TEST_PASSWORD_HASH,
             role=UserRole.ADMIN, last_name='Админ', first_name='А'),
        User(id=3, username='cur1', password_hash=TEST_PASSWORD_HASH,
             role=UserRole.CURATOR, last_name='Куратор', first_name='Кур',
             group_name='ИСП-Б-2022', group_id=1),
        User(id=4, username='student1', password_hash=TEST_PASSWORD_HASH,
             role=UserRole.STUDENT, last_name='Студентов', first_name='Студент',
             group_name='ИСП-Б-2022', group_id=1),
        User(id=5, username='student2', password_hash=TEST_PASSWORD_HASH,
             role=UserRole.STUDENT, last_name='Второв', first_name='Второй',
             group_name='ИСП-Б-2022', group_id=1),
        User(id=6, username='orphan_student', password_hash=TEST_PASSWORD_HASH,
             role=UserRole.STUDENT, last_name='Сирота', first_name='С',
             group_name=None, group_id=None),
    ])
    db.session.flush()

    db.session.add_all([
        Event(id=1, student_id=4, title='Олимпиада по Python',
              status='approved', score=5, category='OK-1'),
        Event(id=2, student_id=4, title='Хакатон',
              status='pending', score=None, category='OK-2'),
        Event(id=3, student_id=4, title='Конкурс',
              status='rejected', score=None),
        Event(id=4, student_id=5, title='Стажировка',
              status='approved', score=4),
        Event(id=5, student_id=6, title='Курсы',
              status='approved', score=5),
    ])
    db.session.commit()
