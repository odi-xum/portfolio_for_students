"""
Модели данных — SQLAlchemy 2.0 (без Flask-зависимостей).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (Column, Integer, String, Text, Boolean, Date, DateTime,
                        ForeignKey)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── User ──────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = 'users'

    id:          Mapped[int]       = mapped_column(Integer, primary_key=True)
    username:    Mapped[str]       = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str]     = mapped_column(String(256), nullable=False)
    role:        Mapped[str]       = mapped_column(String(20), nullable=False)
    last_name:   Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    first_name:  Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    patronymic:  Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    group_name:  Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    group_id:    Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('groups.id'), nullable=True)

    events        = relationship('Event', back_populates='student', lazy=True, cascade='all, delete-orphan')
    notifications = relationship('Notification', back_populates='user', lazy=True, cascade='all, delete-orphan')
    curated_groups = relationship('Group', foreign_keys='Group.curator_id', back_populates='curator', lazy='select')

    def is_admin(self) -> bool:      return self.role == 'admin'
    def is_student(self) -> bool:    return self.role == 'student'
    def is_curator(self) -> bool:    return self.role == 'curator'
    def is_commission(self) -> bool: return self.role == 'commission'

    @property
    def full_name(self) -> str:
        return ' '.join(filter(None, [self.last_name, self.first_name, self.patronymic])) or self.username


# ── Event ─────────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = 'events'

    id:             Mapped[int]   = mapped_column(Integer, primary_key=True)
    student_id:     Mapped[int]   = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    title:          Mapped[str]   = mapped_column(String(150), nullable=False)
    description:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status:         Mapped[str]   = mapped_column(String(20), default='pending', nullable=False)
    category:       Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    score:          Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    curator_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    student = relationship('User', back_populates='events')
    files   = relationship('EventFile', back_populates='event', lazy=True, cascade='all, delete-orphan')

    @property
    def status_label(self) -> str:
        return {'pending': 'На проверке', 'approved': 'Одобрено',
                'rejected': 'Отклонено'}.get(self.status, self.status)

    @property
    def is_pending(self) -> bool:   return self.status == 'pending'
    @property
    def is_approved(self) -> bool:  return self.status == 'approved'
    @property
    def is_resolved(self) -> bool:  return self.status in ('approved', 'rejected')
    @property
    def is_rejected(self) -> bool:  return self.status == 'rejected'
    @property
    def category_label(self) -> str: return self.category or 'Без категории'


# ── EventFile ─────────────────────────────────────────────────────────────
class EventFile(Base):
    __tablename__ = 'event_files'
    id:        Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id:  Mapped[int] = mapped_column(Integer, ForeignKey('events.id'), nullable=False)
    file_path: Mapped[str] = mapped_column(String(300), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)

    event = relationship('Event', back_populates='files')

    @property
    def is_image(self) -> bool: return self.file_type in ('png', 'jpg', 'jpeg')


# ── Notification ──────────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = 'notifications'
    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id:    Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    message:    Mapped[str] = mapped_column(Text, nullable=False)
    link:       Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    is_read:    Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    user = relationship('User', back_populates='notifications')


# ── Department ────────────────────────────────────────────────────────────
class Department(Base):
    __tablename__ = 'departments'
    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    name:       Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    specialties = relationship('Specialty', back_populates='department_rel', lazy=True)


# ── Specialty ─────────────────────────────────────────────────────────────
class Specialty(Base):
    __tablename__ = 'specialties'
    id:            Mapped[int] = mapped_column(Integer, primary_key=True)
    name:          Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    code:          Mapped[str] = mapped_column(String(20), nullable=False)
    abbreviation:  Mapped[str] = mapped_column(String(10), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('departments.id'), nullable=True)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    department_rel = relationship('Department', back_populates='specialties')
    groups         = relationship('Group', back_populates='specialty_rel', lazy=True)


# ── Group ─────────────────────────────────────────────────────────────────
class Group(Base):
    __tablename__ = 'groups'
    id:             Mapped[int] = mapped_column(Integer, primary_key=True)
    name:           Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    group_number:   Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    specialty_id:   Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('specialties.id'), nullable=True)
    specialty_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty_code: Mapped[str] = mapped_column(String(20), nullable=False)
    budget_type:    Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    start_year:     Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    course:         Mapped[int] = mapped_column(Integer, nullable=False)
    department:     Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    form_of_study:  Mapped[str] = mapped_column(String(50), default='очная')
    start_date:     Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    end_date:       Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    curator_id:     Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    specialty_rel = relationship('Specialty', back_populates='groups')
    curator       = relationship('User', foreign_keys=[curator_id], back_populates='curated_groups', lazy=True)


# ── AuditLog ──────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = 'audit_log'
    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id:    Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    username:   Mapped[str] = mapped_column(String(50), nullable=False)
    action:     Mapped[str] = mapped_column(String(50), nullable=False)
    details:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


# ── CuratorOKOverride ─────────────────────────────────────────────────────
class CuratorOKOverride(Base):
    __tablename__ = 'curator_ok_overrides'
    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id:  Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    curator_id:  Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    ok_category: Mapped[str] = mapped_column(String(5), nullable=False)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
