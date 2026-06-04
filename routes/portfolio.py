"""
Публичное портфолио (без аутентификации) — FastAPI.
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from database import get_db
from utils import render
from models import User, Event

router = APIRouter()


@router.get('/portfolio/{username}')
async def public_portfolio(request: Request, username: str):
    db = next(get_db())
    try:
        user = db.query(User).filter(
            User.username == username, User.role == 'student'
        ).first()
        if not user:
            from fastapi.responses import HTMLResponse
            return HTMLResponse('', status_code=404)
        events = db.query(Event).filter(
            Event.student_id == user.id, Event.status == 'approved'
        ).order_by(Event.created_at.desc()).all()
    finally:
        db.close()

    total_score = sum(e.score for e in events if e.score)
    avg = round(total_score / len(events), 2) if events else 0

    return render(request, 'portfolio.html', student=user, events=events, avg_score=avg)
