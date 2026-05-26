"""
Публичное портфолио студента.
Доступно без аутентификации по /portfolio/<username>.
"""
from flask import render_template, abort
from models import User, Event


def register_portfolio_routes(app):
    @app.route('/portfolio/<username>')
    def public_portfolio(username):
        user = User.query.filter_by(username=username, role='student').first()
        if not user:
            abort(404)
        events = Event.query.filter_by(
            student_id=user.id, status='approved'
        ).order_by(Event.created_at.desc()).all()
        total_score = sum(e.score for e in events if e.score)
        avg = round(total_score / len(events), 2) if events else 0
        return render_template('portfolio.html', student=user,
                               events=events, avg_score=avg)
