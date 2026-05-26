"""
Вспомогательные функции.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import date, datetime, timezone
from typing import Optional

from flask import session

from constants import ALLOWED_EXTENSIONS, CSRF_TOKEN_BYTES

# ---------------------------------------------------------------------------
# Конфигурация загрузки файлов
# ---------------------------------------------------------------------------
BASE_UPLOAD_FOLDER = os.path.abspath('./diplom')


def allowed_file(filename: str) -> bool:
    """Проверка расширения файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def now_utc() -> datetime:
    """Текущее UTC-время."""
    return datetime.now(timezone.utc)


def parse_date(date_str: Optional[str], fmt: str = '%Y-%m-%d') -> Optional[date]:
    """Безопасный парсинг даты. Возвращает date или None."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, fmt).date()
    except (ValueError, TypeError):
        return None


def generate_abbreviation(name: str) -> str:
    """
    Генерирует сокращение из первых букв значащих слов.
    Предлоги/союзы пропускаются.
    Пример: "Информационные системы и программирование" → "ИСП"
    """
    skip_words = {'и', 'в', 'на', 'с', 'по', 'из', 'для', 'у', 'о', 'от', 'к', 'до',
                  'без', 'над', 'под', 'за', 'при', 'об', 'со', 'во', 'не', 'ни', 'а', 'но'}
    letters = []
    for word in name.split():
        w = word.lower().replace('(', '').replace(')', '')
        if w and w not in skip_words:
            letters.append(word[0].upper())
    return ''.join(letters)


def build_group_name(specialty_abbr: str, budget_type: Optional[str], start_year: Optional[str] = None) -> str:
    """Формирует название группы: {сокр}-{Б/К}-{год}."""
    parts = [specialty_abbr]
    if budget_type == 'бюджет':
        parts.append('Б')
    elif budget_type == 'коммерция':
        parts.append('К')
    if start_year:
        parts.append(str(start_year))
    return '-'.join(parts)


def log_audit(user, action: str, details: str = None):
    """Записать действие пользователя в аудит-лог."""
    from models import AuditLog, db
    from flask import request
    record = AuditLog(
        user_id=user.id if hasattr(user, 'id') else None,
        username=getattr(user, 'username', user if isinstance(user, str) else '—'),
        action=action,
        details=details,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(record)
    db.session.commit()


def ensure_upload_dir() -> None:
    """Создаёт папку для загрузок, если её нет."""
    if not os.path.exists(BASE_UPLOAD_FOLDER):
        os.makedirs(BASE_UPLOAD_FOLDER)


# ---------------------------------------------------------------------------
# CSRF-защита (на основе сессии)
# ---------------------------------------------------------------------------

def generate_csrf_token() -> str:
    """Генерирует или возвращает существующий CSRF-токен из сессии."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(CSRF_TOKEN_BYTES)
    return session['_csrf_token']


def verify_csrf_token(token: str) -> bool:
    """Проверяет CSRF-токен."""
    stored = session.get('_csrf_token')
    if not stored or not token:
        return False
    return hashlib.sha256(token.encode()).hexdigest() == hashlib.sha256(stored.encode()).hexdigest()
