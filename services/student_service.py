"""
Сервис студента: статистика мероприятий.
"""
from __future__ import annotations
from typing import List
from database import SessionLocal
from constants import EventStatus
from models import Event


def get_student_event_stats(student_id: int) -> dict:
    db = SessionLocal()
    try:
        base = db.query(Event).filter(Event.student_id == student_id)
        total = base.count()
        approved = base.filter(Event.status == EventStatus.APPROVED).count()
        pending = base.filter(Event.status == EventStatus.PENDING).count()
        rejected = base.filter(Event.status == EventStatus.REJECTED).count()
        return {'total': total, 'approved': approved, 'pending': pending, 'rejected': rejected}
    finally:
        db.close()


def get_student_approved_events(student_id: int) -> List[Event]:
    db = SessionLocal()
    try:
        return db.query(Event).filter(
            Event.student_id == student_id, Event.status == EventStatus.APPROVED
        ).all()
    finally:
        db.close()
