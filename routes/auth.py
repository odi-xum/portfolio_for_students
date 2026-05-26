"""
Маршруты аутентификации: логин / логаут.
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import User
from helpers import log_audit


def register_auth_routes(app):
    @app.route('/', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for(f'{current_user.role}_dashboard'))
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                log_audit(user, 'login', f'Вход в систему')
                return redirect(url_for(f'{user.role}_dashboard'))
            log_audit(username, 'login_failed', f'Неудачная попытка входа')
            flash('Неверный логин или пароль. Попробуйте еще раз.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        log_audit(current_user, 'logout', 'Выход из системы')
        logout_user()
        return redirect(url_for('login'))
