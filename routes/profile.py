"""
Профиль пользователя + смена пароля.
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


def register_profile_routes(app):
    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            last_name = request.form.get('last_name', '').strip()
            first_name = request.form.get('first_name', '').strip()
            patronymic = request.form.get('patronymic', '').strip()
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if last_name:
                current_user.last_name = last_name
            if first_name:
                current_user.first_name = first_name
            if patronymic:
                current_user.patronymic = patronymic

            if new_pw:
                if not old_pw or not check_password_hash(current_user.password_hash, old_pw):
                    flash('Старый пароль указан неверно.', 'danger')
                    return redirect(url_for('profile'))
                if new_pw != confirm_pw:
                    flash('Новый пароль и подтверждение не совпадают.', 'danger')
                    return redirect(url_for('profile'))
                if len(new_pw) < 3:
                    flash('Новый пароль слишком короткий (мин. 3 символа).', 'danger')
                    return redirect(url_for('profile'))
                current_user.password_hash = generate_password_hash(new_pw)
                flash('Пароль успешно изменён.', 'success')

            db.session.commit()
            flash('Данные сохранены.', 'success')
            return redirect(url_for('profile'))

        return render_template('profile.html')
