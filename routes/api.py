"""
API-эндпоинты и маршруты уведомлений.
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

from models import db, User, Event, Notification


def register_api_routes(app):

    # ==================================================================
    #  ОБЩИЕ МАРШРУТЫ
    # ==================================================================
    @app.route('/event/<int:event_id>')
    @login_required
    def event_detail(event_id):
        event = Event.query.options(joinedload(Event.student), joinedload(Event.files)).get_or_404(event_id)
        if current_user.role == 'student' and event.student_id != current_user.id:
            return "Доступ ограничен", 403
        if current_user.role == 'curator' and event.student.group_name != current_user.group_name:
            return "Доступ ограничен", 403
        if current_user.role not in ('student', 'curator', 'commission', 'admin'):
            return "Доступ ограничен", 403
        return render_template('event_detail.html', event=event)

    @app.route('/diplom/<path:filename>')
    @login_required
    def serve_diplom_files(filename):
        from helpers import BASE_UPLOAD_FOLDER
        from flask import send_from_directory
        return send_from_directory(BASE_UPLOAD_FOLDER, filename)

    # ==================================================================
    #  УВЕДОМЛЕНИЯ
    # ==================================================================
    @app.route('/notifications')
    @login_required
    def notifications():
        notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return render_template('notifications.html', notifications=notifs, unread_count=unread)

    @app.route('/notifications/mark_read/<int:notif_id>', methods=['POST'])
    @login_required
    def mark_notification_read(notif_id):
        notif = Notification.query.get_or_404(notif_id)
        if notif.user_id != current_user.id:
            return "Доступ ограничен", 403
        notif.is_read = True
        db.session.commit()
        return redirect(url_for('notifications'))

    @app.route('/notifications/mark_all_read', methods=['POST'])
    @login_required
    def mark_all_notifications_read():
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        flash('Все уведомления отмечены как прочитанные.', 'success')
        return redirect(url_for('notifications'))

    @app.route('/api/notifications/count')
    @login_required
    def api_notification_count():
        count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return jsonify({'unread': count})

    # ==================================================================
    #  API КУРАТОРА
    # ==================================================================
    @app.route('/curator/api/events', methods=['GET'])
    @login_required
    def curator_api_events():
        if current_user.role != 'curator':
            return jsonify({'error': 'Доступ ограничен'}), 403

        group_students = User.query.filter_by(group_name=current_user.group_name, role='student').all()
        student_ids = [s.id for s in group_students]
        scope = request.args.get('scope', 'pending')
        q = request.args.get('q', '').strip()

        if scope == 'resolved':
            query = Event.query.options(joinedload(Event.student)).filter(
                Event.student_id.in_(student_ids),
                Event.status.in_(['approved', 'disputed', 'rejected'])
            )
        else:
            query = Event.query.options(joinedload(Event.student)).filter(
                Event.student_id.in_(student_ids),
                Event.status == 'pending'
            )

        if q:
            like = f'%{q}%'
            query = query.filter(or_(Event.title.ilike(like), Event.description.ilike(like)))

        events = query.order_by(Event.created_at.desc()).all()
        result = []
        for e in events:
            result.append({
                'id': e.id,
                'title': e.title,
                'description': e.description or '',
                'status': e.status,
                'score': e.score,
                'curator_comment': e.curator_comment or '',
                'commission_comment': e.commission_comment or '',
                'created_at': e.created_at.strftime('%d.%m.%Y %H:%M') if e.created_at else '',
                'student': e.student.username if e.student else 'Удален'
            })
        return jsonify({'events': result, 'scope': scope})

    # ==================================================================
    #  API СТУДЕНТА
    # ==================================================================
    @app.route('/student/api/events', methods=['GET'])
    @login_required
    def student_api_events():
        if current_user.role != 'student':
            return jsonify({'error': 'Доступ ограничен'}), 403

        q = request.args.get('q', '').strip()
        query = Event.query.options(joinedload(Event.files)).filter_by(student_id=current_user.id)
        if q:
            like = f'%{q}%'
            query = query.filter(or_(Event.title.ilike(like), Event.description.ilike(like)))

        events = query.order_by(Event.created_at.desc()).all()
        result = []
        for e in events:
            result.append({
                'id': e.id,
                'title': e.title,
                'description': e.description or '',
                'status': e.status,
                'score': e.score,
                'curator_comment': e.curator_comment or '',
                'commission_comment': e.commission_comment or '',
                'created_at': e.created_at.strftime('%d.%m.%Y %H:%M') if e.created_at else '',
                'files': [{'path': f.file_path, 'type': f.file_type} for f in e.files]
            })
        return jsonify({'events': result})
