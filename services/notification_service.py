"""
Сервис уведомлений.
"""
from __future__ import annotations

from typing import Optional

from flask import url_for
from flask_login import current_user

from constants import UserRole
from models import db, User, Notification


def notify_user(user_id: int, message: str, link: Optional[str] = None) -> Notification:
    """Создать уведомление для одного пользователя."""
    n = Notification(user_id=user_id, message=message, link=link)
    db.session.add(n)
    return n


def notify_student(student_id: int, message: str, link: Optional[str] = None) -> Notification:
    """Уведомить студента."""
    return notify_user(student_id, message, link)


def notify_students(student_ids: list, message: str, link: Optional[str] = None) -> list:
    """Уведомить нескольких студентов."""
    return [notify_user(sid, message, link) for sid in student_ids]


def notify_curators_of_group(group_id: int, message: str, link: Optional[str] = None) -> list:
    """Уведомить всех кураторов, закреплённых за группой."""
    curators = User.query.filter(User.role == UserRole.CURATOR, User.curated_groups.any(id=group_id)).all()
    return [notify_user(c.id, message, link) for c in curators]


def notify_all_commission(message: str, link: Optional[str] = None) -> list:
    """Уведомить всех членов комиссии."""
    members = User.query.filter_by(role=UserRole.COMMISSION).all()
    return [notify_user(m.id, message, link) for m in members]
