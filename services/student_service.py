"""
Сервис студента: статистика, проверка стипендии.
"""
from __future__ import annotations

from typing import List, Optional

from constants import EventStatus, SCHOLARSHIP_MIN_EVENTS, SCHOLARSHIP_MIN_AVG_SCORE
from models import db, User, Event, ScholarshipRequest


def get_student_event_stats(student_id: int) -> dict:
    """Статистика мероприятий студента."""
    base = Event.query.filter_by(student_id=student_id)
    total = base.count()
    approved = base.filter(Event.status == EventStatus.APPROVED).count()
    pending = base.filter(Event.status == EventStatus.PENDING).count()
    disputed = base.filter(Event.status == EventStatus.DISPUTED).count()
    return {'total': total, 'approved': approved, 'pending': pending, 'disputed': disputed}


def check_scholarship_eligibility(student_id: int) -> tuple:
    """
    Проверка возможности подать на стипендию.
    Возвращает (eligible: bool, approved_count: int, avg_score: float).
    """
    approved = Event.query.filter_by(student_id=student_id, status=EventStatus.APPROVED).all()
    count = len(approved)
    if count < SCHOLARSHIP_MIN_EVENTS:
        return False, count, 0.0
    avg = sum(e.score for e in approved) / count
    return avg >= SCHOLARSHIP_MIN_AVG_SCORE, count, avg


def get_student_approved_events(student_id: int) -> List[Event]:
    """Одобренные мероприятия студента."""
    return Event.query.filter_by(student_id=student_id, status=EventStatus.APPROVED).all()
