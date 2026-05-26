"""
Маршруты куратора: панель, заявки, журнал, оценка мероприятий.
"""
from flask import abort, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

from constants import EventStatus
from models import db, User, Event
from export import generate_report
from services.curator_service import (
    get_curator_dashboard_stats,
    get_curator_students,
    get_curator_events,
)
from services.notification_service import notify_user, notify_all_commission
from helpers import log_audit
from services.ok_service import get_ok_stats, toggle_override, OK_LIST


def register_curator_routes(app):

    @app.route('/curator/dashboard', methods=['GET'])
    @login_required
    def curator_dashboard():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        stats = get_curator_dashboard_stats(current_user)
        groups = current_user.curated_groups
        students = get_curator_students(current_user)

        return render_template('curator.html',
                               pending_count=stats['pending'],
                               approved_count=stats['approved'],
                               disputed_count=stats['disputed'],
                               total_resolved=stats['total_resolved'],
                               groups=groups,
                               students=students)

    @app.route('/curator/pending', methods=['GET'])
    @login_required
    def curator_pending():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        events = get_curator_events(current_user, EventStatus.PENDING)
        return render_template('curator_pending.html', events=events)

    @app.route('/curator/resolved', methods=['GET'])
    @login_required
    def curator_resolved():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        events = get_curator_events(current_user, 'resolved')
        return render_template('curator_resolved.html', events=events)

    @app.route('/curator/evaluate/<int:event_id>', methods=['POST'])
    @login_required
    def curator_evaluate(event_id):
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        event = db.get_or_404(Event, event_id)
        action = request.form.get('action')
        comment = request.form.get('comment')

        if action == 'approve':
            score = int(request.form.get('score', 5))
            event.score = score
            event.curator_comment = comment
            event.status = EventStatus.APPROVED
            notify_user(event.student_id,
                        f"Куратор одобрил ваше мероприятие «{event.title}» с оценкой {score}.",
                        url_for('event_detail', event_id=event.id))
            log_audit(current_user, 'event_approve', f'Одобрено мероприятие #{event.id} «{event.title}» студента {event.student_id}, оценка {score}')
            flash(f"Мероприятие ID {event.id} успешно одобрено с оценкой {score}.", 'success')

        elif action == 'reject':
            if not comment or comment.strip() == "":
                flash("Ошибка: При отклонении поста комментарий с указанием причины обязателен!", "danger")
                return redirect(url_for('curator_pending'))

            event.curator_comment = comment
            event.status = EventStatus.DISPUTED

            notify_user(event.student_id,
                        f"Куратор отклонил ваше мероприятие «{event.title}». Причина: {comment}",
                        url_for('event_detail', event_id=event.id))
            notify_all_commission(
                f"Куратор отклонил пост студента «{event.title}». Требуется арбитражная оценка.",
                url_for('event_detail', event_id=event.id))
            log_audit(current_user, 'event_reject', f'Отклонено мероприятие #{event.id} «{event.title}» студента {event.student_id}')
            flash(f"Мероприятие ID {event.id} отклонено и перенаправлено в комиссию.", 'warning')

        db.session.commit()
        return redirect(url_for('curator_pending'))

    @app.route('/curator/export', methods=['GET', 'POST'])
    @login_required
    def curator_export():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        groups = current_user.curated_groups
        group_ids = [g.id for g in groups]
        all_students = User.query.filter(
            User.role == 'student',
            User.group_id.in_(group_ids)
        ).order_by(User.last_name).all()

        if request.method == 'POST':
            student_ids = request.form.getlist('student_ids')
            selected_group_id = request.form.get('group_id')
            base_students = all_students
            if selected_group_id:
                base_students = [s for s in all_students if str(s.group_id) == selected_group_id]
            selected = [s for s in base_students if str(s.id) in student_ids] or base_students
            include_charts = 'include_charts' in request.form
            include_details = 'include_details' in request.form
            status_filter = request.form.get('status_filter', 'all')
            date_from = request.form.get('date_from') or None
            date_to = request.form.get('date_to') or None

            buf = generate_report(
                students=selected,
                include_charts=include_charts,
                include_details=include_details,
                status_filter=status_filter,
                date_from=date_from,
                date_to=date_to,
            )
            group_label = selected_group_id or 'все_группы'
            fname = f'отчёт_куратора_{group_label}.xlsx'
            return send_file(buf, as_attachment=True, download_name=fname,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        return render_template('curator_export.html', students=all_students, groups=groups)

    # ------------------------------------------------------------------
    #  OK — просмотр компетенций студента
    # ------------------------------------------------------------------
    @app.route('/curator/student_ok/<int:student_id>', methods=['GET'])
    @login_required
    def curator_student_ok(student_id):
        if current_user.role != 'curator':
            abort(403)

        student = db.get_or_404(User, student_id)
        if student.role != 'student':
            abort(404)

        # Проверяем, что студент из группы куратора
        curator_gids = [g.id for g in current_user.curated_groups]
        if student.group_id not in curator_gids:
            abort(403)

        ok_stats = get_ok_stats(student_id)
        current_category = request.args.get('category')

        if current_category == 'none':
            events = Event.query.filter(
                Event.student_id == student_id, Event.category.is_(None)
            ).order_by(Event.created_at.desc()).all()
        elif current_category:
            events = Event.query.filter_by(
                student_id=student_id, category=current_category
            ).order_by(Event.created_at.desc()).all()
        else:
            events = Event.query.filter_by(student_id=student_id).order_by(
                Event.created_at.desc()
            ).all()

        return render_template('curator_student_ok.html',
                               student=student, ok_stats=ok_stats,
                               ok_list=OK_LIST,
                               current_category=current_category,
                               events=events)

    @app.route('/curator/toggle_ok/<int:student_id>/<ok_category>', methods=['POST'])
    @login_required
    def curator_toggle_ok(student_id, ok_category):
        if current_user.role != 'curator':
            abort(403)

        if ok_category not in OK_LIST:
            flash(f'Некорректная категория: {ok_category}', 'danger')
            return redirect(url_for('curator_dashboard'))

        added = toggle_override(student_id, current_user.id, ok_category)
        label = 'засчитана' if added else 'отменена'
        log_audit(current_user, f'ok_{"override" if added else "undo"}',
                  f'{label.capitalize()} {ok_category} для студента #{student_id}')
        flash(f'Категория {ok_category} {label} для студента.', 'success' if added else 'warning')
        return redirect(url_for('curator_student_ok', student_id=student_id))
