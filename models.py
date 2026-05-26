"""
Модели данных системы портфолио студентов.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

from constants import EventStatus, ScholarshipStatus, UserRole

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(50), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(256), nullable=False)
    role: str = db.Column(db.String(20), nullable=False)

    last_name: Optional[str] = db.Column(db.String(50), nullable=True)
    first_name: Optional[str] = db.Column(db.String(50), nullable=True)
    patronymic: Optional[str] = db.Column(db.String(50), nullable=True)

    group_name: Optional[str] = db.Column(db.String(20), nullable=True)
    group_id: Optional[int] = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)

    events = db.relationship('Event', backref='student', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    scholarship_requests = db.relationship('ScholarshipRequest', backref='student', lazy=True, cascade='all, delete-orphan')
    curated_groups = db.relationship('Group', foreign_keys='Group.curator_id',
                                     back_populates='curator', lazy='select')

    def is_admin(self) -> bool: return self.role == UserRole.ADMIN
    def is_student(self) -> bool: return self.role == UserRole.STUDENT
    def is_curator(self) -> bool: return self.role == UserRole.CURATOR
    def is_commission(self) -> bool: return self.role == UserRole.COMMISSION

    @property
    def full_name(self) -> str:
        return ' '.join(filter(None, [self.last_name, self.first_name, self.patronymic])) or self.username


class Event(db.Model):
    __tablename__ = 'events'

    id: int = db.Column(db.Integer, primary_key=True)
    student_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title: str = db.Column(db.String(150), nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True)
    status: str = db.Column(db.String(20), default=EventStatus.PENDING, nullable=False)
    previous_status: Optional[str] = db.Column(db.String(20), nullable=True)

    category: Optional[str] = db.Column(db.String(5), nullable=True)
    score: Optional[int] = db.Column(db.Integer, nullable=True)
    curator_comment: Optional[str] = db.Column(db.Text, nullable=True)
    commission_comment: Optional[str] = db.Column(db.Text, nullable=True)

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    commission_reviewed_at: Optional[datetime] = db.Column(db.DateTime, nullable=True)
    files = db.relationship('EventFile', backref='event', lazy=True, cascade='all, delete-orphan')

    @property
    def status_label(self) -> str:
        return {'pending':'На проверке','approved':'Одобрено','rejected':'Отклонено','disputed':'В комиссии'}.get(self.status,self.status)

    @property
    def is_pending(self) -> bool: return self.status == EventStatus.PENDING
    @property
    def is_approved(self) -> bool: return self.status == EventStatus.APPROVED
    @property
    def is_resolved(self) -> bool: return self.status in (EventStatus.APPROVED, EventStatus.REJECTED, EventStatus.DISPUTED)

    @property
    def category_label(self) -> str: return self.category if self.category else 'Без категории'


class EventFile(db.Model):
    __tablename__ = 'event_files'
    id: int = db.Column(db.Integer, primary_key=True)
    event_id: int = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    file_path: str = db.Column(db.String(300), nullable=False)
    file_type: str = db.Column(db.String(10), nullable=False)

    @property
    def is_image(self) -> bool:
        return self.file_type in ('png', 'jpg', 'jpeg')


class Notification(db.Model):
    __tablename__ = 'notifications'
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message: str = db.Column(db.Text, nullable=False)
    link: Optional[str] = db.Column(db.String(300), nullable=True)
    is_read: bool = db.Column(db.Boolean, default=False, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Department(db.Model):
    __tablename__ = 'departments'
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), unique=True, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    specialties = db.relationship('Specialty', backref='department_rel', lazy=True)


class Specialty(db.Model):
    __tablename__ = 'specialties'
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), unique=True, nullable=False)
    code: str = db.Column(db.String(20), nullable=False)
    abbreviation: str = db.Column(db.String(10), nullable=False)
    department_id: Optional[int] = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    groups = db.relationship('Group', backref='specialty_rel', lazy=True)


class Group(db.Model):
    __tablename__ = 'groups'
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(20), unique=True, nullable=False)
    group_number: Optional[str] = db.Column(db.String(10), nullable=True)
    specialty_id: Optional[int] = db.Column(db.Integer, db.ForeignKey('specialties.id'), nullable=True)
    specialty_name: str = db.Column(db.String(200), nullable=False)
    specialty_code: str = db.Column(db.String(20), nullable=False)
    budget_type: Optional[str] = db.Column(db.String(10), nullable=True)
    start_year: Optional[int] = db.Column(db.Integer, nullable=True)
    course: int = db.Column(db.Integer, nullable=False)
    department: Optional[str] = db.Column(db.String(100), nullable=True)
    form_of_study: str = db.Column(db.String(50), default='очная')
    start_date: Optional[datetime] = db.Column(db.Date, nullable=True)
    end_date: Optional[datetime] = db.Column(db.Date, nullable=True)
    curator_id: Optional[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    curator = db.relationship('User', foreign_keys=[curator_id], back_populates='curated_groups', lazy=True)


class ScholarshipRequest(db.Model):
    __tablename__ = 'scholarship_requests'
    id: int = db.Column(db.Integer, primary_key=True)
    student_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status: str = db.Column(db.String(30), default=ScholarshipStatus.UNDER_CURATOR_REVIEW, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    commission_reviewed_at: Optional[datetime] = db.Column(db.DateTime, nullable=True)


class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username: str = db.Column(db.String(50), nullable=False)
    action: str = db.Column(db.String(50), nullable=False)
    details: Optional[str] = db.Column(db.Text, nullable=True)
    ip_address: Optional[str] = db.Column(db.String(45), nullable=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CuratorOKOverride(db.Model):
    """Отметка куратора о выполнении ОК студентом."""
    __tablename__ = 'curator_ok_overrides'
    id: int = db.Column(db.Integer, primary_key=True)
    student_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    curator_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ok_category: str = db.Column(db.String(5), nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
