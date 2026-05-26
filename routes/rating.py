"""
Рейтинг студентов по группе.
"""
from flask import render_template
from flask_login import login_required, current_user

from constants import EventStatus, UserRole
from models import db, User, Event, Group


def register_rating_routes(app):
    @app.route('/rating')
    @login_required
    def rating():
        if current_user.role not in (UserRole.STUDENT, UserRole.CURATOR):
            return "Доступ ограничен", 403

        if current_user.is_curator():
            group_ids = [g.id for g in current_user.curated_groups]
            students = User.query.filter(
                User.role == UserRole.STUDENT,
                User.group_id.in_(group_ids)
            ).order_by(User.last_name).all()
            group = None
        else:
            students = User.query.filter_by(
                role=UserRole.STUDENT, group_name=current_user.group_name
            ).order_by(User.last_name).all()
            group = Group.query.filter_by(name=current_user.group_name).first()

        rows = []
        for s in students:
            total = Event.query.filter_by(student_id=s.id).count()
            approved = Event.query.filter_by(student_id=s.id, status=EventStatus.APPROVED).count()
            scored = Event.query.filter(
                Event.student_id == s.id, Event.status == EventStatus.APPROVED,
                Event.score.isnot(None)
            ).all()
            avg = round(sum(e.score for e in scored) / len(scored), 2) if scored else 0
            rows.append({
                'student': s, 'total': total, 'approved': approved,
                'avg_score': avg,
                'can_scholarship': approved >= 20 and avg >= 4.5,
            })
        rows.sort(key=lambda r: r['avg_score'], reverse=True)
        for i, r in enumerate(rows, 1):
            r['place'] = i
        return render_template('rating.html', rows=rows, group=group)
