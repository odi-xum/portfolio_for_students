"""
Константы и enum-классы проекта.
"""
from enum import StrEnum


# ── Роли пользователей ─────────────────────────────────────────────────────

class UserRole(StrEnum):
    ADMIN = 'admin'
    STUDENT = 'student'
    CURATOR = 'curator'


# ── Статусы мероприятий (Event) ────────────────────────────────────────────

class EventStatus(StrEnum):
    PENDING = 'pending'      # отправлено студентом, ждёт куратора
    APPROVED = 'approved'    # одобрено куратором
    REJECTED = 'rejected'    # отклонено куратором


# ── Загрузка файлов ────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

ALLOWED_MIME_TYPES = {
    'image/png',
    'image/jpeg',
    'image/jpg',
    'application/pdf',
}


# ── Оценки ─────────────────────────────────────────────────────────────────

MAX_EVENT_SCORE = 5
MIN_EVENT_SCORE = 1


# ── CSRF ───────────────────────────────────────────────────────────────────

CSRF_TOKEN_BYTES = 32
