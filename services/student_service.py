"""
Сервис студента: статистика мероприятий.
Принимает db: Session от вызывающей стороны (роута).
"""
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from constants import EventStatus
from models import Event


def get_student_event_stats(db: Session, student_id: int) -> dict:
    base = db.query(Event).filter(Event.student_id == student_id)
    total = base.count()
    approved = base.filter(Event.status == EventStatus.APPROVED).count()
    pending = base.filter(Event.status == EventStatus.PENDING).count()
    rejected = base.filter(Event.status == EventStatus.REJECTED).count()
    return {'total': total, 'approved': approved, 'pending': pending, 'rejected': rejected}


def get_student_approved_events(db: Session, student_id: int) -> List[Event]:
    return db.query(Event).filter(
        Event.student_id == student_id, Event.status == EventStatus.APPROVED
    ).all()
