"""
Рейтинг студентов — FastAPI.
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session, joinedload

from database import get_db
from utils import render
from dependencies import require_user
from models import User, Event, Group
from constants import EventStatus, UserRole

router = APIRouter()


@router.get('/rating')
async def rating(request: Request, user: User = Depends(require_user)):
    db = next(get_db())
    try:
        if user.is_curator():
            group_ids = [g.id for g in user.curated_groups]
            students = db.query(User).filter(
                User.role == UserRole.STUDENT, User.group_id.in_(group_ids)
            ).order_by(User.last_name).all()
            group = None
        else:
            students = db.query(User).filter(
                User.role == UserRole.STUDENT, User.group_name == user.group_name
            ).order_by(User.last_name).all()
            group = db.query(Group).filter(Group.name == user.group_name).first()

        rows = []
        for s in students:
            total = db.query(Event).filter(Event.student_id == s.id).count()
            approved = db.query(Event).filter(
                Event.student_id == s.id, Event.status == EventStatus.APPROVED
            ).count()
            scored = db.query(Event).filter(
                Event.student_id == s.id, Event.status == EventStatus.APPROVED,
                Event.score.isnot(None)
            ).all()
            avg = round(sum(e.score for e in scored) / len(scored), 2) if scored else 0
            rows.append({'student': s, 'total': total, 'approved': approved, 'avg_score': avg})
    finally:
        db.close()

    rows.sort(key=lambda r: r['avg_score'], reverse=True)
    for i, r in enumerate(rows, 1):
        r['place'] = i

    return render(request, 'rating.html', rows=rows, group=group)
