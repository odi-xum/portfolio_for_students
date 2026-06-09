"""
Сервис уведомлений.
Принимает db: Session от вызывающей стороны.
"""
from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from models import User, Notification
from constants import UserRole


def notify_user(db: Session, user_id: int, message: str, link: Optional[str] = None) -> Notification:
    n = Notification(user_id=user_id, message=message, link=link)
    db.add(n)
    db.commit()
    return n


def notify_student(db: Session, student_id: int, message: str, link: Optional[str] = None) -> Notification:
    return notify_user(db, student_id, message, link)


def notify_students(db: Session, student_ids: list, message: str, link: Optional[str] = None) -> list:
    return [notify_user(db, sid, message, link) for sid in student_ids]


def notify_curators_of_group(db: Session, group_id: int, message: str, link: Optional[str] = None) -> list:
    curators = db.query(User).filter(
        User.role == UserRole.CURATOR, User.curated_groups.any(id=group_id)
    ).all()
    return [notify_user(db, c.id, message, link) for c in curators]
