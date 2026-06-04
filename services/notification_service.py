"""
Сервис уведомлений.
"""
from __future__ import annotations
from typing import Optional
from database import SessionLocal
from models import User, Notification
from constants import UserRole


def notify_user(user_id: int, message: str, link: Optional[str] = None) -> Notification:
    db = SessionLocal()
    try:
        n = Notification(user_id=user_id, message=message, link=link)
        db.add(n); db.commit()
        return n
    finally:
        db.close()


def notify_student(student_id: int, message: str, link: Optional[str] = None) -> Notification:
    return notify_user(student_id, message, link)


def notify_students(student_ids: list, message: str, link: Optional[str] = None) -> list:
    return [notify_user(sid, message, link) for sid in student_ids]


def notify_curators_of_group(group_id: int, message: str, link: Optional[str] = None) -> list:
    db = SessionLocal()
    try:
        curators = db.query(User).filter(
            User.role == UserRole.CURATOR, User.curated_groups.any(id=group_id)
        ).all()
    finally:
        db.close()
    return [notify_user(c.id, message, link) for c in curators]
