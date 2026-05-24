from app import create_app
from models import db, Department, Specialty, Group, User
from seed import init_test_db

app = create_app()

with app.app_context():
    init_test_db(app)
    
    depts = Department.query.all()
    print('=== Отделения ===')
    for d in depts:
        specs_in_dept = ', '.join([s.abbreviation for s in d.specialties])
        print(f'  {d.name}: {specs_in_dept}')
    
    specs = Specialty.query.all()
    print('\n=== Специальности ===')
    for s in specs:
        dept_name = s.department_rel.name if s.department_rel else '—'
        print(f'  [{s.abbreviation}] {s.name} — {s.code} → {dept_name}')
    
    groups = Group.query.all()
    print('\n=== Группы ===')
    for g in groups:
        print(f'  {g.name} | №{g.group_number or "—"} | спец: {g.specialty_name} ({g.specialty_code}) | тип: {g.budget_type} | год: {g.start_year}')
    
    print('\n=== Все пользователи ===')
    for u in User.query.all():
        fio = ' '.join([x for x in [u.last_name, u.first_name, u.patronymic] if x])
        print(f'  [{u.role:12s}] {u.username:12s} | {fio or "—":30s} | группа: {u.group_name or "—"}')
