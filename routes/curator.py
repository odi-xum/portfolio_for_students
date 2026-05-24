"""
Маршруты куратора: панель, заявки, журнал, оценка мероприятий.
"""
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, User, Event, Notification, Group
from export import generate_report


def register_curator_routes(app):

    @app.route('/curator/dashboard', methods=['GET'])
    @login_required
    def curator_dashboard():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        group_students = User.query.filter_by(group_name=current_user.group_name, role='student').all()
        student_ids = [s.id for s in group_students]

        pending_count = Event.query.filter(Event.student_id.in_(student_ids), Event.status == 'pending').count()
        approved_count = Event.query.filter(Event.student_id.in_(student_ids), Event.status == 'approved').count()
        disputed_count = Event.query.filter(Event.student_id.in_(student_ids), Event.status == 'disputed').count()
        rejected_count = Event.query.filter(Event.student_id.in_(student_ids), Event.status == 'rejected').count()
        total_resolved = approved_count + disputed_count + rejected_count

        return render_template('curator.html',
                               pending_count=pending_count,
                               approved_count=approved_count,
                               disputed_count=disputed_count,
                               total_resolved=total_resolved)

    @app.route('/curator/pending', methods=['GET'])
    @login_required
    def curator_pending():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        group_students = User.query.filter_by(group_name=current_user.group_name, role='student').all()
        student_ids = [s.id for s in group_students]
        events = Event.query.options(joinedload(Event.student), joinedload(Event.files)).filter(
            Event.student_id.in_(student_ids), Event.status == 'pending'
        ).order_by(Event.created_at.asc()).all()

        return render_template('curator_pending.html', events=events)

    @app.route('/curator/resolved', methods=['GET'])
    @login_required
    def curator_resolved():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        group_students = User.query.filter_by(group_name=current_user.group_name, role='student').all()
        student_ids = [s.id for s in group_students]
        events = Event.query.options(joinedload(Event.student)).filter(
            Event.student_id.in_(student_ids),
            Event.status.in_(['approved', 'disputed', 'rejected'])
        ).order_by(Event.created_at.desc()).all()

        return render_template('curator_resolved.html', events=events)

    @app.route('/curator/evaluate/<int:event_id>', methods=['POST'])
    @login_required
    def curator_evaluate(event_id):
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        event = Event.query.get_or_404(event_id)
        action = request.form.get('action')
        comment = request.form.get('comment')

        if action == 'approve':
            score = int(request.form.get('score', 5))
            event.score = score
            event.curator_comment = comment
            event.status = 'approved'
            db.session.add(Notification(
                user_id=event.student_id,
                message=f"Куратор одобрил ваше мероприятие «{event.title}» с оценкой {score}.",
                link=url_for('event_detail', event_id=event.id)
            ))
            flash(f"Мероприятие ID {event.id} успешно одобрено с оценкой {score}.", 'success')

        elif action == 'reject':
            if not comment or comment.strip() == "":
                flash("Ошибка: При отклонении поста комментарий с указанием причины обязателен!", "danger")
                return redirect(url_for('curator_pending'))

            event.curator_comment = comment
            event.status = 'disputed'

            db.session.add(Notification(
                user_id=event.student_id,
                message=f"Куратор отклонил ваше мероприятие «{event.title}». Причина: {comment}",
                link=url_for('event_detail', event_id=event.id)
            ))
            commission_members = User.query.filter_by(role='commission').all()
            for member in commission_members:
                db.session.add(Notification(
                    user_id=member.id,
                    message=f"Куратор отклонил пост студента «{event.title}». Требуется арбитражная оценка.",
                    link=url_for('event_detail', event_id=event.id)
                ))
            flash(f"Мероприятие ID {event.id} отклонено и перенаправлено в комиссию.", 'warning')

        db.session.commit()
        return redirect(url_for('curator_pending'))

    # ------------------------------------------------------------------
    #  ЭКСПОРТ В EXCEL
    # ------------------------------------------------------------------
    @app.route('/curator/export', methods=['GET', 'POST'])
    @login_required
    def curator_export():
        if current_user.role != 'curator':
            return "Доступ ограничен", 403

        group_students = User.query.filter_by(
            group_name=current_user.group_name, role='student'
        ).order_by(User.last_name).all()

        if request.method == 'POST':
            student_ids = request.form.getlist('student_ids')
            selected = [s for s in group_students if str(s.id) in student_ids] or group_students
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
            fname = f'отчёт_куратора_{current_user.group_name}.xlsx'
            return send_file(buf, as_attachment=True, download_name=fname,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        return render_template('curator_export.html', students=group_students)
