"""
Проверка содержимого БД.
"""
from app import create_app
from models import db, Department, Specialty, Group, User, Event, Notification, ScholarshipRequest

app = create_app()

with app.app_context():
    depts = Department.query.all()
    print(f'=== Отделения ({len(depts)}) ===')
    for d in depts:
        specs_in = ', '.join([s.abbreviation for s in d.specialties])
        print(f'  {d.name}: {specs_in}')

    specs = Specialty.query.all()
    print(f'\n=== Специальности ({len(specs)}) ===')
    for s in specs:
        dn = s.department_rel.name if s.department_rel else '—'
        print(f'  [{s.abbreviation}] {s.name} — {s.code} → {dn}')

    groups = Group.query.all()
    print(f'\n=== Группы ({len(groups)}) ===')
    for g in groups:
        print(f'  {g.name} | №{g.group_number or "—"} | {g.specialty_name} ({g.specialty_code}) | {g.budget_type or "—"} | {g.start_year or "—"}')

    print(f'\n=== Пользователи ===')
    for u in User.query.all():
        fio = ' '.join(filter(None, [u.last_name, u.first_name, u.patronymic]))
        print(f'  [{u.role:12s}] {u.username:12s} | {fio or "—":30s} | гр: {u.group_name or "—"}')

    print(f'\n=== Мероприятия: {Event.query.count()} ===')
    print(f'  одобрено:   {Event.query.filter_by(status="approved").count()}')
    print(f'  на проверке: {Event.query.filter_by(status="pending").count()}')
    print(f'  в комиссии: {Event.query.filter_by(status="disputed").count()}')
    print(f'  отклонено:  {Event.query.filter_by(status="rejected").count()}')

    print(f'\n=== Уведомления: {Notification.query.count()} ===')
    print(f'  непрочитанных: {Notification.query.filter_by(is_read=False).count()}')

    print(f'\n=== Заявки на стипендию: {ScholarshipRequest.query.count()} ===')
