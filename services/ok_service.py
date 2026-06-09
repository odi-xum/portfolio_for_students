"""
Сервис для работы с общими компетенциями (ОК-1..ОК-9).
Принимает db: Session от вызывающей стороны.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from constants import EventStatus
from models import Event, CuratorOKOverride

OK_LIST = [f'OK-{i}' for i in range(1, 10)]
OK_MIN_EVENTS = 3


def get_ok_stats(db: Session, student_id: int) -> List[dict]:
    overrides = set(
        r.ok_category for r in db.query(CuratorOKOverride).filter(
            CuratorOKOverride.student_id == student_id
        ).all()
    )
    approved = {c: db.query(Event).filter(
        Event.student_id == student_id, Event.category == c, Event.status == EventStatus.APPROVED
    ).count() for c in OK_LIST}
    pending = {c: db.query(Event).filter(
        Event.student_id == student_id, Event.category == c, Event.status == EventStatus.PENDING
    ).count() for c in OK_LIST}
    result = []
    for ok in OK_LIST:
        cnt = approved.get(ok, 0)
        done = cnt >= OK_MIN_EVENTS or ok in overrides
        result.append({'ok': ok, 'approved': cnt, 'pending': pending.get(ok, 0),
                       'has_override': ok in overrides, 'done': done})
    return result


def all_ok_completed(db: Session, student_id: int) -> bool:
    return all(s['done'] for s in get_ok_stats(db, student_id))


def get_events_by_category(db: Session, student_id: int, category: Optional[str] = None) -> List[Event]:
    q = db.query(Event).filter(Event.student_id == student_id)
    if category is None:
        q = q.filter(Event.category.is_(None))
    else:
        q = q.filter(Event.category == category)
    return q.order_by(Event.created_at.desc()).all()


def toggle_override(db: Session, student_id: int, curator_id: int, ok_category: str) -> bool:
    existing = db.query(CuratorOKOverride).filter(
        CuratorOKOverride.student_id == student_id,
        CuratorOKOverride.curator_id == curator_id,
        CuratorOKOverride.ok_category == ok_category
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return False
    else:
        db.add(CuratorOKOverride(student_id=student_id, curator_id=curator_id, ok_category=ok_category))
        db.commit()
        return True
