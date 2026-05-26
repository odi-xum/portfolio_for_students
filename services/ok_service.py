"""
Сервис для работы с общими компетенциями (ОК-1..ОК-9).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from constants import EventStatus
from models import db, Event, CuratorOKOverride

OK_LIST = [f'OK-{i}' for i in range(1, 10)]
OK_MIN_EVENTS = 3


def get_ok_stats(student_id: int) -> List[dict]:
    """
    Статистика по каждой ОК для студента.
    Возвращает список словарей:
      {ok: str, approved: int, pending: int, has_override: bool, done: bool}
    """
    overrides = set(
        r.ok_category for r in CuratorOKOverride.query.filter_by(student_id=student_id).all()
    )
    approved = {
        c: Event.query.filter_by(
            student_id=student_id, category=c, status=EventStatus.APPROVED
        ).count()
        for c in OK_LIST
    }
    pending = {
        c: Event.query.filter_by(
            student_id=student_id, category=c, status=EventStatus.PENDING
        ).count()
        for c in OK_LIST
    }
    result = []
    for ok in OK_LIST:
        cnt = approved.get(ok, 0)
        done = cnt >= OK_MIN_EVENTS or ok in overrides
        result.append({
            'ok': ok,
            'approved': cnt,
            'pending': pending.get(ok, 0),
            'has_override': ok in overrides,
            'done': done,
        })
    return result


def all_ok_completed(student_id: int) -> bool:
    """Все ли ОК выполнены для студента."""
    return all(s['done'] for s in get_ok_stats(student_id))


def get_events_by_category(student_id: int, category: Optional[str] = None) -> List[Event]:
    """Мероприятия студента по категории. None = без категории."""
    q = Event.query.filter_by(student_id=student_id)
    if category is None:
        q = q.filter(Event.category.is_(None))
    else:
        q = q.filter(Event.category == category)
    return q.order_by(Event.created_at.desc()).all()


def toggle_override(student_id: int, curator_id: int, ok_category: str) -> bool:
    """
    Переключить оверрайд. Возвращает True если оверрайд установлен, False если снят.
    """
    existing = CuratorOKOverride.query.filter_by(
        student_id=student_id, curator_id=curator_id, ok_category=ok_category
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return False
    else:
        db.session.add(CuratorOKOverride(
            student_id=student_id, curator_id=curator_id, ok_category=ok_category
        ))
        db.session.commit()
        return True
