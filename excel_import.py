"""
Импорт студентов из Excel-файла.
"""
import io
from werkzeug.security import generate_password_hash
from openpyxl import load_workbook
from models import db, User, Group


def import_students_from_excel(file_storage):
    """
    Читает .xlsx, создаёт студентов. Возвращает (imported, skipped, errors).
    Ожидаемые колонки: Фамилия, Имя, Отчество, Группа, Логин, Пароль.
    """
    imported = 0
    skipped = 0
    errors = []

    wb = load_workbook(file_storage, read_only=True)
    ws = wb.active
    if ws is None:
        return 0, 0, ['Файл не содержит листов']

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return 0, 0, ['Файл пуст']

    # Определяем индексы колонок по заголовку
    col_map = {}
    for i, h in enumerate(header):
        if h is None:
            continue
        h_lower = str(h).strip().lower()
        if 'фамили' in h_lower:
            col_map['last'] = i
        elif 'имя' in h_lower and 'отчеств' not in h_lower:
            col_map['first'] = i
        elif 'отчеств' in h_lower:
            col_map['patr'] = i
        elif 'групп' in h_lower:
            col_map['group'] = i
        elif 'логин' in h_lower:
            col_map['login'] = i
        elif 'парол' in h_lower:
            col_map['password'] = i

    if 'login' not in col_map:
        return 0, 0, ['Не найдена колонка "Логин". Заголовки: ' + ', '.join(str(h) for h in header if h)]

    for row_idx, row in enumerate(rows_iter, 2):
        try:
            login = _val(row, col_map.get('login'))
            if not login:
                skipped += 1
                continue
            if User.query.filter_by(username=str(login)).first():
                skipped += 1
                continue

            group_name = _val(row, col_map.get('group'))
            group_id = None
            if group_name:
                grp = Group.query.filter_by(name=group_name).first()
                if grp:
                    group_id = grp.id

            db.session.add(User(
                username=str(login),
                password_hash=generate_password_hash(_val(row, col_map.get('password'), '111')),
                role='student',
                last_name=_val(row, col_map.get('last')),
                first_name=_val(row, col_map.get('first')),
                patronymic=_val(row, col_map.get('patr')),
                group_name=group_name,
                group_id=group_id,
            ))
            imported += 1
        except Exception as e:
            errors.append(f'Строка {row_idx}: {e}')
            skipped += 1

    db.session.commit()
    return imported, skipped, errors


def _val(row, idx, default=None):
    """Безопасное чтение ячейки."""
    if idx is None or idx >= len(row):
        return default
    v = row[idx]
    if v is None:
        return default
    return str(v).strip()
