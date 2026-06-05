"""
Генерация PDF-версии портфолио (через weasyprint).
"""
import io
from sqlalchemy.orm import joinedload
from database import SessionLocal
from models import User, Event
from utils import templates


def generate_portfolio_pdf(username):
    """Возвращает BytesIO с PDF-портфолио студента."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.role == 'student').first()
        if not user:
            return None
        events = db.query(Event).options(
            joinedload(Event.files)
        ).filter(
            Event.student_id == user.id, Event.status == 'approved'
        ).order_by(Event.created_at.desc()).all()
    finally:
        db.close()

    total_score = sum(e.score for e in events if e.score)
    avg = round(total_score / len(events), 2) if events else 0

    html_str = templates.get_template('portfolio.html').render(
        request={}, student=user, events=events, avg_score=avg,
        current_user=None, flash=None
    )
    buf = io.BytesIO()
    from weasyprint import HTML
    HTML(string=html_str).write_pdf(buf)
    buf.seek(0)
    return buf
