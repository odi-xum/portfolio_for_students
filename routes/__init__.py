"""
Регистрация всех групп маршрутов в приложении Flask.
"""
from .auth import register_auth_routes
from .admin import register_admin_routes
from .student import register_student_routes
from .curator import register_curator_routes
from .commission import register_commission_routes
from .api import register_api_routes


def register_routes(app):
    """Вызывается из app.py после создания Flask-приложения."""
    register_auth_routes(app)
    register_admin_routes(app)
    register_student_routes(app)
    register_curator_routes(app)
    register_commission_routes(app)
    register_api_routes(app)
