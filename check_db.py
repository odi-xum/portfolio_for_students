"""
Просмотр содержимого БД (для отладки).
"""
from database import SessionLocal
from models import Department, Specialty, Group, User, Event, AuditLog


def check_db():
    db = SessionLocal()
    try:
        print('\n=== ОТДЕЛЕНИЯ ===')
        for d in db.query(Department).all():
            print(f'  #{d.id} {d.name}')

        print('\n=== СПЕЦИАЛЬНОСТИ ===')
        for s in db.query(Specialty).all():
            dept = s.department_rel.name if s.department_rel else '—'
            print(f'  #{s.id} {s.name} ({s.code}) — {dept}')

        print('\n=== ГРУППЫ ===')
        for g in db.query(Group).all():
            cur = g.curator.username if g.curator else '—'
            print(f'  #{g.id} {g.name} — курс {g.course}, куратор {cur}')

        print('\n=== ПОЛЬЗОВАТЕЛИ ===')
        for u in db.query(User).order_by(User.role, User.username).all():
            grp = u.group_name or '—'
            print(f'  #{u.id} {u.username:20s} {u.role:10s} гр. {grp}')

        print('\n=== МЕРОПРИЯТИЯ ===')
        for e in db.query(Event).order_by(Event.created_at.desc()).limit(20).all():
            print(f'  #{e.id} ст.{e.student_id} {e.status:10s} {e.title[:50]}')

        print(f'\n=== АУДИТ-ЛОГ: {db.query(AuditLog).count()} записей ===')
        for a in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all():
            print(f'  #{a.id} {a.created_at} | {a.username} | {a.action} | {a.details or ""}')
    finally:
        db.close()


if __name__ == '__main__':
    check_db()
