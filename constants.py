"""
Константы и enum-классы проекта.
"""
from enum import StrEnum


# ── Роли пользователей ─────────────────────────────────────────────────────

class UserRole(StrEnum):
    ADMIN = 'admin'
    STUDENT = 'student'
    CURATOR = 'curator'
    COMMISSION = 'commission'


# ── Статусы мероприятий (Event) ────────────────────────────────────────────

class EventStatus(StrEnum):
    PENDING = 'pending'      # отправлено студентом, ждёт куратора
    APPROVED = 'approved'    # одобрено
    REJECTED = 'rejected'    # окончательно отклонено комиссией
    DISPUTED = 'disputed'    # отклонено куратором → передано в комиссию


# ── Статусы заявок на стипендию ────────────────────────────────────────────

class ScholarshipStatus(StrEnum):
    UNDER_CURATOR_REVIEW = 'under_curator_review'
    UNDER_COMMISSION_REVIEW = 'under_commission_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'


# ── Загрузка файлов ────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

ALLOWED_MIME_TYPES = {
    'image/png',
    'image/jpeg',
    'image/jpg',
    'application/pdf',
}


# ── Лимиты для стипендии ───────────────────────────────────────────────────

SCHOLARSHIP_MIN_EVENTS = 20
SCHOLARSHIP_MIN_AVG_SCORE = 4.5
MAX_EVENT_SCORE = 5
MIN_EVENT_SCORE = 1


# ── CSRF ───────────────────────────────────────────────────────────────────

CSRF_TOKEN_BYTES = 32
