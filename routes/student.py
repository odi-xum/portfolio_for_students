"""
Маршруты студента: панель, создание поста, история, запрос стипендии, ОК.
"""
import os

from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

from constants import EventStatus
from models import db, Event, EventFile, ScholarshipRequest
from helpers import allowed_file, now_utc, BASE_UPLOAD_FOLDER
from pdf_export import generate_portfolio_pdf
from services.student_service import get_student_event_stats, check_scholarship_eligibility
from services.notification_service import notify_curators_of_group
from helpers import log_audit
from services.ok_service import get_ok_stats, all_ok_completed


def register_student_routes(app):

    def _abort_if_not_student():
        if current_user.role != 'student':
            return "Доступ ограничен", 403

    @app.route('/student/dashboard', methods=['GET'])
    @login_required
    def student_dashboard():
        r = _abort_if_not_student()
        if r: return r

        stats = get_student_event_stats(current_user.id)
        eligible, _, _ = check_scholarship_eligibility(current_user.id)
        ok_stats = get_ok_stats(current_user.id)
        ok_all_done = all_ok_completed(current_user.id)

        return render_template('student.html', total=stats['total'],
                               approved=stats['approved'],
                               pending=stats['pending'],
                               disputed=stats['disputed'],
                               can_request=eligible,
                               ok_stats=ok_stats,
                               ok_all_done=ok_all_done)

    @app.route('/student/create', methods=['GET', 'POST'])
    @login_required
    def student_create():
        r = _abort_if_not_student()
        if r: return r

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category') or None
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
                category=category,
                status=EventStatus.PENDING,
                created_at=now_utc()
            )
            db.session.add(new_event)
            db.session.flush()

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

            if current_user.group_id:
                notify_curators_of_group(
                    current_user.group_id,
                    f"Студент {current_user.username} опубликовал новое мероприятие: '{title}'. Требуется проверка.",
                    url_for('event_detail', event_id=new_event.id))

            db.session.commit()
            log_audit(current_user, 'event_create', f'Создано мероприятие #{new_event.id} «{title}»')
            flash('Мероприятие успешно опубликовано на вашей стене и отправлено куратору.', 'success')
            return redirect(url_for('student_history'))

        return render_template('student_create.html')

    @app.route('/student/history', methods=['GET'])
    @login_required
    def student_history():
        r = _abort_if_not_student()
        if r: return r

        events = Event.query.options(joinedload(Event.files)).filter_by(
            student_id=current_user.id
        ).order_by(Event.created_at.desc()).all()
        return render_template('student_history.html', events=events)

    @app.route('/student/notify_ok', methods=['POST'])
    @login_required
    def student_notify_ok():
        r = _abort_if_not_student()
        if r: return r

        if all_ok_completed(current_user.id):
            if current_user.group_id:
                notify_curators_of_group(
                    current_user.group_id,
                    f"Студент {current_user.full_name} выполнил все общие компетенции (ОК-1 — ОК-9). Требуется подтверждение.")
            flash('Уведомление отправлено куратору.', 'success')
        else:
            flash('Не все общие компетенции выполнены.', 'warning')
        return redirect(url_for('student_dashboard'))

    @app.route('/student/request_scholarship', methods=['POST'])
    @login_required
    def request_scholarship():
        r = _abort_if_not_student()
        if r: return r

        eligible, count, avg = check_scholarship_eligibility(current_user.id)
        if count < 20:
            flash(f'Отказано: Недостаточно верифицированных достижений. У вас {count} из 20 необходимых.', 'danger')
            return redirect(url_for('student_dashboard'))
        if not eligible:
            flash(f'Отказано: Недостаточный средний балл портфолио. Ваш показатель: {avg:.2f} (требуется не менее 4.50).', 'danger')
            return redirect(url_for('student_dashboard'))

        new_request = ScholarshipRequest(student_id=current_user.id, status='under_curator_review')
        db.session.add(new_request)

        if current_user.group_id:
            notify_curators_of_group(
                current_user.group_id,
                f"Студент {current_user.username} выполнил нормативы портфолио и подал заявку на повышенную стипендию.")

        db.session.commit()
        flash('Заявка на повышенную стипендию сформирована и отправлена куратору группы для сверки статистики.', 'success')
        return redirect(url_for('student_dashboard'))

    @app.route('/student/portfolio_pdf')
    @login_required
    def student_portfolio_pdf():
        r = _abort_if_not_student()
        if r: return r

        buf = generate_portfolio_pdf(current_user.username)
        if not buf:
            flash('Ошибка генерации портфолио.', 'danger')
            return redirect(url_for('student_history'))
        return send_file(buf, as_attachment=True,
                         download_name=f'портфолио_{current_user.username}.pdf',
                         mimetype='application/pdf')
