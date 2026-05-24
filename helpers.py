"""
Вспомогательные функции.
"""
import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Конфигурация загрузки файлов
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
BASE_UPLOAD_FOLDER = os.path.abspath('./diplom')


def allowed_file(filename):
    """Проверка расширения файла."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def now_utc():
    """Текущее UTC-время (datetime.now(timezone.utc))."""
    return datetime.now(timezone.utc)


def parse_date(date_str, fmt='%Y-%m-%d'):
    """Безопасный парсинг даты. Возвращает date или None."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, fmt).date()
    except (ValueError, TypeError):
        return None


def generate_abbreviation(name):
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


def build_group_name(specialty_abbr, budget_type, start_year=None):
    """Формирует название группы: {сокр}-{Б/К}-{год}."""
    parts = [specialty_abbr]
    if budget_type == 'бюджет':
        parts.append('Б')
    elif budget_type == 'коммерция':
        parts.append('К')
    if start_year:
        parts.append(str(start_year))
    return '-'.join(parts)


def ensure_upload_dir():
    """Создаёт папку для загрузок, если её нет."""
    if not os.path.exists(BASE_UPLOAD_FOLDER):
        os.makedirs(BASE_UPLOAD_FOLDER)
