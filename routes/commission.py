"""
Маршруты комиссии: панель, споры, стипендии, архив, пересмотр.
"""
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, Event, Notification, ScholarshipRequest, User, Group
from helpers import now_utc
from export import generate_report


def register_commission_routes(app):

    @app.route('/commission/dashboard')
    @login_required
    def commission_dashboard():
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        active_disputes = Event.query.filter_by(status='disputed').count()
        active_scholarships = ScholarshipRequest.query.filter(
            ScholarshipRequest.status.in_(['under_commission_review', 'under_curator_review'])
        ).count()
        resolved_events_count = Event.query.filter(
            Event.status.in_(['approved', 'rejected']),
            Event.commission_reviewed_at.isnot(None)
        ).count()
        resolved_scholarships_count = ScholarshipRequest.query.filter(
            ScholarshipRequest.status.in_(['approved', 'rejected']),
            ScholarshipRequest.commission_reviewed_at.isnot(None)
        ).count()

        return render_template('commission.html',
                               active_disputes=active_disputes,
                               active_scholarships=active_scholarships,
                               resolved_events_count=resolved_events_count,
                               resolved_scholarships_count=resolved_scholarships_count)

    @app.route('/commission/disputes')
    @login_required
    def commission_disputes():
        if current_user.role != 'commission':
            return "Доступ ограничен", 403
        disputed_events = Event.query.options(joinedload(Event.student)).filter_by(
            status='disputed'
        ).order_by(Event.created_at.asc()).all()
        return render_template('commission_disputes.html', disputed_events=disputed_events)

    @app.route('/commission/scholarships')
    @login_required
    def commission_scholarships():
        if current_user.role != 'commission':
            return "Доступ ограничен", 403
        scholarship_requests = ScholarshipRequest.query.options(
            joinedload(ScholarshipRequest.student)
        ).filter(
            ScholarshipRequest.status.in_(['under_commission_review', 'under_curator_review'])
        ).order_by(ScholarshipRequest.created_at.asc()).all()
        return render_template('commission_scholarships.html', scholarship_requests=scholarship_requests)

    @app.route('/commission/archive')
    @login_required
    def commission_archive():
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        resolved_events = Event.query.options(joinedload(Event.student)).filter(
            Event.status.in_(['approved', 'rejected']),
            Event.commission_reviewed_at.isnot(None)
        ).order_by(Event.commission_reviewed_at.desc()).all()

        resolved_scholarships = ScholarshipRequest.query.options(
            joinedload(ScholarshipRequest.student)
        ).filter(
            ScholarshipRequest.status.in_(['approved', 'rejected']),
            ScholarshipRequest.commission_reviewed_at.isnot(None)
        ).order_by(ScholarshipRequest.commission_reviewed_at.desc()).all()

        return render_template('commission_archive.html',
                               resolved_events=resolved_events,
                               resolved_scholarships=resolved_scholarships)

    @app.route('/commission/resolve_dispute/<int:event_id>', methods=['POST'])
    @login_required
    def resolve_dispute(event_id):
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        event = Event.query.get_or_404(event_id)
        decision = request.form.get('decision')
        comment = request.form.get('commission_comment')

        event.previous_status = event.status
        event.commission_comment = comment
        event.commission_reviewed_at = now_utc()

        if decision == 'confirm_reject':
            event.status = 'rejected'
            db.session.add(Notification(
                user_id=event.student_id,
                message=f"Комиссия подтвердила отклонение вашего мероприятия «{event.title}».",
                link=url_for('event_detail', event_id=event.id)
            ))
            flash(f'Пост ID {event.id} окончательно отклонен комиссией.', 'danger')
        elif decision == 'overrule_approve':
            event.status = 'approved'
            event.score = 5 if not event.score else event.score
            db.session.add(Notification(
                user_id=event.student_id,
                message=f"Комиссия одобрила ваше мероприятие «{event.title}» поверх решения куратора.",
                link=url_for('event_detail', event_id=event.id)
            ))
            flash(f'Решение куратора отменено. Пост ID {event.id} успешно одобрен комиссией.', 'success')

        db.session.commit()
        return redirect(url_for('commission_disputes'))

    @app.route('/commission/scholarship_decision/<int:req_id>', methods=['POST'])
    @login_required
    def scholarship_decision(req_id):
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        req = ScholarshipRequest.query.get_or_404(req_id)
        decision = request.form.get('decision')
        req.commission_reviewed_at = now_utc()

        if decision == 'approve':
            req.status = 'approved'
            db.session.add(Notification(
                user_id=req.student_id,
                message=f"Поздравляем! Комиссия назначила вам повышенную стипендию.",
                link=url_for('commission_scholarships')
            ))
            flash('Повышенная стипендия успешно назначена.', 'success')
        elif decision == 'reject':
            req.status = 'rejected'
            db.session.add(Notification(
                user_id=req.student_id,
                message=f"Комиссия отклонила вашу заявку на повышенную стипендию.",
                link=url_for('commission_scholarships')
            ))
            flash('В назначении стипендии отказано.', 'danger')

        db.session.commit()
        return redirect(url_for('commission_scholarships'))

    @app.route('/commission/reconsider_event/<int:event_id>', methods=['POST'])
    @login_required
    def reconsider_event(event_id):
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        event = Event.query.get_or_404(event_id)
        event.status = 'disputed'
        event.commission_reviewed_at = None
        event.commission_comment = f"[Отправлено на пересмотр] {event.commission_comment or ''}"

        db.session.add(Notification(
            user_id=event.student_id,
            message=f"Решение комиссии по вашему мероприятию «{event.title}» отправлено на пересмотр.",
            link=url_for('event_detail', event_id=event.id)
        ))
        db.session.commit()
        flash(f'Решение по посту ID {event.id} отменено. Запись возвращена в активный арбитраж.', 'warning')
        return redirect(url_for('commission_disputes'))

    @app.route('/commission/reconsider_scholarship/<int:req_id>', methods=['POST'])
    @login_required
    def reconsider_scholarship(req_id):
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        req = ScholarshipRequest.query.get_or_404(req_id)
        req.status = 'under_commission_review'
        req.commission_reviewed_at = None

        db.session.add(Notification(
            user_id=req.student_id,
            message=f"Решение по вашей заявке на стипендию отправлено на пересмотр."
        ))
        db.session.commit()
        flash(f'Решение по стипендии ID {req.id} отменено. Заявка возвращена на этап рассмотрения.', 'warning')
        return redirect(url_for('commission_scholarships'))

    # ------------------------------------------------------------------
    #  ЭКСПОРТ В EXCEL
    # ------------------------------------------------------------------
    @app.route('/commission/export', methods=['GET', 'POST'])
    @login_required
    def commission_export():
        if current_user.role != 'commission':
            return "Доступ ограничен", 403

        groups = Group.query.order_by(Group.name).all()
        all_students = User.query.filter_by(role='student').order_by(User.last_name).all()

        if request.method == 'POST':
            group_ids = request.form.getlist('group_ids')
            student_ids = request.form.getlist('student_ids')

            if student_ids:
                selected = [u for u in all_students if str(u.id) in student_ids]
            elif group_ids:
                selected = [u for u in all_students if str(u.group_id) in group_ids]
            else:
                selected = all_students

            if not selected:
                flash('Не выбрано ни одного студента.', 'warning')
                return redirect(url_for('commission_export'))

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
            fname = f'отчёт_комиссии.xlsx'
            return send_file(buf, as_attachment=True, download_name=fname,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        return render_template('commission_export.html', students=all_students, groups=groups)
