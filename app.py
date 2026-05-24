"""
Точка входа. Создаёт Flask-приложение, регистрирует маршруты,
инициализирует БД и запускает dev-сервер.
"""
import os

from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from models import db, User
from helpers import BASE_UPLOAD_FOLDER
from routes import register_routes
from seed import init_test_db


def create_app():
    """Фабрика приложения."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'gruvbox-material-secure-shadow-key-1984'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = BASE_UPLOAD_FOLDER

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    register_routes(app)

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        init_test_db(app)
    app.run(debug=True)
