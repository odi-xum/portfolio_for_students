"""
Маршруты студента: панель, создание поста, история, запрос стипендии.
"""
import os

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

from models import db, User, Event, EventFile, Notification, ScholarshipRequest
from helpers import allowed_file, now_utc, BASE_UPLOAD_FOLDER


def register_student_routes(app):

    @app.route('/student/dashboard', methods=['GET'])
    @login_required
    def student_dashboard():
        if current_user.role != 'student':
            return "Доступ ограничен", 403
        total = Event.query.filter_by(student_id=current_user.id).count()
        approved = Event.query.filter_by(student_id=current_user.id, status='approved').count()
        pending = Event.query.filter_by(student_id=current_user.id, status='pending').count()
        disputed = Event.query.filter_by(student_id=current_user.id, status='disputed').count()

        can_request = False
        if approved >= 20:
            approved_events = Event.query.filter_by(student_id=current_user.id, status='approved').all()
            avg_score = sum(e.score for e in approved_events) / len(approved_events)
            can_request = avg_score >= 4.5

        return render_template('student.html', total=total, approved=approved,
                               pending=pending, disputed=disputed, can_request=can_request)

    @app.route('/student/create', methods=['GET', 'POST'])
    @login_required
    def student_create():
        if current_user.role != 'student':
            return "Доступ ограничен", 403

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            files = request.files.getlist('files')
            valid_files = [f for f in files if f and allowed_file(f.filename)]

            if not title:
                flash('Пожалуйста, заполните название мероприятия.', 'warning')
                return redirect(url_for('student_create'))
            if not valid_files:
                flash('Ошибка: Не хватает доказательств для присутствия на мероприятии! Прикрепите JPG/PNG или PDF.', 'danger')
                return redirect(url_for('student_create'))

            new_event = Event(
                student_id=current_user.id,
                title=title,
                description=description,
                status='pending',
                created_at=now_utc()
            )
            db.session.add(new_event)
            db.session.commit()

            safe_username = secure_filename(current_user.username)
            safe_title = secure_filename(title)
            event_dir_name = f"{new_event.id}_{safe_title}"
            student_folder = os.path.join(BASE_UPLOAD_FOLDER, 'students', safe_username, event_dir_name)
            os.makedirs(student_folder, exist_ok=True)

            for file in valid_files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(student_folder, filename)
                file.save(file_path)
                ext = filename.rsplit('.', 1)[1].lower()
                db.session.add(EventFile(event_id=new_event.id, file_path=file_path, file_type=ext))

            curator = User.query.filter_by(role='curator', group_name=current_user.group_name).first()
            if curator:
                db.session.add(Notification(
                    user_id=curator.id,
                    message=f"Студент {current_user.username} опубликовал новое мероприятие: '{title}'. Требуется проверка."
                ))

            db.session.commit()
            flash('Мероприятие успешно опубликовано на вашей стене и отправлено куратору.', 'success')
            return redirect(url_for('student_history'))

        return render_template('student_create.html')

    @app.route('/student/history', methods=['GET'])
    @login_required
    def student_history():
        if current_user.role != 'student':
            return "Доступ ограничен", 403
        events = Event.query.options(joinedload(Event.files)).filter_by(
            student_id=current_user.id
        ).order_by(Event.created_at.desc()).all()
        return render_template('student_history.html', events=events)

    @app.route('/student/request_scholarship', methods=['POST'])
    @login_required
    def request_scholarship():
        if current_user.role != 'student':
            return "Доступ ограничен", 403

        approved_events = Event.query.filter_by(student_id=current_user.id, status='approved').all()

        if len(approved_events) < 20:
            flash(f'Отказано: Недостаточно верифицированных достижений. У вас {len(approved_events)} из 20 необходимых.', 'danger')
            return redirect(url_for('student_dashboard'))

        avg_score = sum([e.score for e in approved_events]) / len(approved_events)
        if avg_score < 4.5:
            flash(f'Отказано: Недостаточный средний балл портфолио. Ваш показатель: {avg_score:.2f} (требуется не менее 4.50).', 'danger')
            return redirect(url_for('student_dashboard'))

        new_request = ScholarshipRequest(student_id=current_user.id, status='under_curator_review')
        db.session.add(new_request)

        curator = User.query.filter_by(role='curator', group_name=current_user.group_name).first()
        if curator:
            db.session.add(Notification(
                user_id=curator.id,
                message=f"Студент {current_user.username} выполнил нормативы портфолио и подал заявку на повышенную стипендию."
            ))

        db.session.commit()
        flash('Заявка на повышенную стипендию сформирована и отправлена куратору группы для сверки статистики.', 'success')
        return redirect(url_for('student_dashboard'))
