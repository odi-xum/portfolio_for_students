"""
Генерация PDF-версии портфолио (через weasyprint).
"""
import io
from flask import render_template
from weasyprint import HTML

from models import User, Event


def generate_portfolio_pdf(username):
    """Возвращает BytesIO с PDF-портфолио студента."""
    user = User.query.filter_by(username=username, role='student').first()
    if not user:
        return None

    events = Event.query.filter_by(
        student_id=user.id, status='approved'
    ).order_by(Event.created_at.desc()).all()

    total_score = sum(e.score for e in events if e.score)
    avg = round(total_score / len(events), 2) if events else 0

    html_str = render_template('portfolio.html', student=user,
                                events=events, avg_score=avg)
    buf = io.BytesIO()
    HTML(string=html_str).write_pdf(buf)
    buf.seek(0)
    return buf
