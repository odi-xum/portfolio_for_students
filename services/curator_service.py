"""
Сервис куратора: поиск студентов, агрегация статистики.
"""
from __future__ import annotations

from typing import List

from sqlalchemy.orm import joinedload

from constants import EventStatus
from models import db, User, Event


def _group_ids_from_user(user: User) -> List[int]:
    return [g.id for g in user.curated_groups]


def get_curator_students(user: User) -> List[User]:
    gids = _group_ids_from_user(user)
    if not gids:
        return []
    return User.query.filter(
        User.role == 'student',
        User.group_id.in_(gids)
    ).all()


def get_curator_student_ids(user: User) -> List[int]:
    return [s.id for s in get_curator_students(user)]


def get_curator_dashboard_stats(user: User) -> dict:
    ids = get_curator_student_ids(user)
    if not ids:
        return {'pending': 0, 'approved': 0, 'disputed': 0, 'rejected': 0, 'total_resolved': 0}
    base = Event.query.filter(Event.student_id.in_(ids))
    pending = base.filter(Event.status == EventStatus.PENDING).count()
    approved = base.filter(Event.status == EventStatus.APPROVED).count()
    disputed = base.filter(Event.status == EventStatus.DISPUTED).count()
    rejected = base.filter(Event.status == EventStatus.REJECTED).count()
    return {
        'pending': pending, 'approved': approved, 'disputed': disputed,
        'rejected': rejected, 'total_resolved': approved + disputed + rejected,
    }


def get_curator_events(user: User, status_filter: str = EventStatus.PENDING) -> List[Event]:
    ids = get_curator_student_ids(user)
    if not ids:
        return []
    q = Event.query.options(joinedload(Event.student), joinedload(Event.files)).filter(
        Event.student_id.in_(ids)
    )
    if status_filter == 'resolved':
        q = q.filter(Event.status.in_([EventStatus.APPROVED, EventStatus.DISPUTED, EventStatus.REJECTED]))
    else:
        q = q.filter(Event.status == status_filter)
    return q.order_by(Event.created_at.desc()).all()
