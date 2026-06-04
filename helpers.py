"""
Вспомогательные функции — адаптировано для FastAPI.
"""
from __future__ import annotations
import hashlib, os, secrets
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import Request
from starlette.datastructures import MutableHeaders
from constants import ALLOWED_EXTENSIONS, CSRF_TOKEN_BYTES

BASE_UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'diplom'))


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(date_str: Optional[str], fmt: str = '%Y-%m-%d') -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, fmt).date()
    except (ValueError, TypeError):
        return None


def generate_abbreviation(name: str) -> str:
    skip_words = {'и', 'в', 'на', 'с', 'по', 'из', 'для', 'у', 'о', 'от', 'к', 'до',
                  'без', 'над', 'под', 'за', 'при', 'об', 'со', 'во', 'не', 'ни', 'а', 'но'}
    letters = []
    for word in name.split():
        w = word.lower().replace('(', '').replace(')', '')
        if w and w not in skip_words:
            letters.append(word[0].upper())
    return ''.join(letters)


def build_group_name(specialty_abbr: str, budget_type: Optional[str], start_year: Optional[str] = None) -> str:
    parts = [specialty_abbr]
    if budget_type == 'бюджет':
        parts.append('Б')
    elif budget_type == 'коммерция':
        parts.append('К')
    if start_year:
        parts.append(str(start_year))
    return '-'.join(parts)


def log_audit(db_session, user, action: str, details: str = None, ip: str = None):
    """Записать действие в аудит-лог. ip — необязательный."""
    from models import AuditLog
    try:
        record = AuditLog(
            user_id=user.id if hasattr(user, 'id') else None,
            username=getattr(user, 'username', user if isinstance(user, str) else '—'),
            action=action,
            details=details,
            ip_address=ip,
        )
        db_session.add(record)
        db_session.commit()
    except Exception:
        db_session.rollback()


def ensure_upload_dir() -> None:
    if not os.path.exists(BASE_UPLOAD_FOLDER):
        os.makedirs(BASE_UPLOAD_FOLDER)


# ---------------------------------------------------------------------------
# CSRF (на основе Starlette Session)
# ---------------------------------------------------------------------------
def generate_csrf_token(request: Request) -> str:
    if '_csrf_token' not in request.session:
        request.session['_csrf_token'] = secrets.token_hex(CSRF_TOKEN_BYTES)
    return request.session['_csrf_token']


def verify_csrf_token(token: str, request: Request) -> bool:
    stored = request.session.get('_csrf_token')
    if not stored or not token:
        return False
    return hashlib.sha256(token.encode()).hexdigest() == hashlib.sha256(stored.encode()).hexdigest()
