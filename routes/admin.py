"""
Административные маршруты — FastAPI.
"""
import json, os
from datetime import timedelta
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from database import get_db
from utils import render
from dependencies import require_admin, hash_password
from helpers import (generate_abbreviation, build_group_name, parse_date,
                     now_utc, log_audit, BASE_UPLOAD_FOLDER)
from models import User, Group, Specialty, Department, Event, AuditLog
from constants import UserRole

router = APIRouter()





# ── Dashboard ─────────────────────────────────────────────────────────
@router.get('/admin/dashboard')
async def admin_dashboard(request: Request, user: User = Depends(require_admin),
                           db: Session = Depends(get_db)):
    now = now_utc()
    month_ago = now - timedelta(days=30)
    stats = {
        'users_count': db.query(User).count(),
        'students_count': db.query(User).filter(User.role == 'student').count(),
        'curators_count': db.query(User).filter(User.role == 'curator').count(),
        'groups_count': db.query(Group).count(),
        'events_total': db.query(Event).count(),
        'events_pending': db.query(Event).filter(Event.status == 'pending').count(),
        'events_approved': db.query(Event).filter(Event.status == 'approved').count(),
        'events_rejected': db.query(Event).filter(Event.status == 'rejected').count(),
        'events_month': db.query(Event).filter(Event.created_at >= month_ago).count(),
        'dept_count': db.query(Department).count(),
        'specialty_count': db.query(Specialty).count(),
    }
    dept_stats = []
    for d in db.query(Department).all():
        spec_ids = [s.id for s in d.specialties]
        grps = db.query(Group).filter(Group.specialty_id.in_(spec_ids)).all()
        grp_ids = [g.id for g in grps]
        stu_count = db.query(User).filter(
            User.role == 'student', User.group_id.in_(grp_ids)
        ).count() if grp_ids else 0
        dept_stats.append({'name': d.name, 'groups': len(grps), 'students': stu_count})
    return render(request, 'admin.html', stats=stats, dept_stats=dept_stats)


# ── Users ──────────────────────────────────────────────────────────────
@router.get('/admin/users')
async def admin_users(request: Request, user: User = Depends(require_admin),
                       db: Session = Depends(get_db)):
    users = db.query(User).all()
    groups = db.query(Group).order_by(Group.name).all()
    return render(request, 'admin_users.html', users=users, groups=groups)


@router.post('/admin/add_user')
async def admin_add_user(request: Request, user: User = Depends(require_admin),
                          db: Session = Depends(get_db),
                          username: str = Form(...), password: str = Form(...),
                          role: str = Form(...), group_id: str = Form(''),
                          last_name: str = Form(''), first_name: str = Form(''),
                          patronymic: str = Form('')):
    if db.query(User).filter(User.username == username).first():
        request.session['flash'] = {'type': 'danger', 'message': 'Пользователь с таким логином уже существует!'}
        return RedirectResponse(url='/admin/users', status_code=302)
    grp_name, grp_id_val = None, None
    if group_id:
        grp = db.get(Group, int(group_id))
        if grp: grp_name, grp_id_val = grp.name, grp.id
    new_user = User(
        username=username, password_hash=hash_password(password), role=role,
        last_name=last_name or None, first_name=first_name or None,
        patronymic=patronymic or None, group_name=grp_name, group_id=grp_id_val
    )
    db.add(new_user); db.commit()
    log_audit(db, user, 'user_create', f'Создан пользователь {username} ({role})')
    request.session['flash'] = {'type': 'success', 'message': f'Пользователь {username} ({role}) успешно добавлен.'}
    return RedirectResponse(url='/admin/users', status_code=302)


@router.post('/admin/delete_user/{user_id}')
async def admin_delete_user(request: Request, user_id: int,
                             user: User = Depends(require_admin),
                             db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target: return RedirectResponse(url='/admin/users', status_code=302)
    if target.id == user.id:
        request.session['flash'] = {'type': 'danger', 'message': 'Вы не можете удалить самого себя!'}
        return RedirectResponse(url='/admin/dashboard', status_code=302)
    log_audit(db, user, 'user_delete', f'Удалён пользователь #{target.id} {target.username} ({target.role})')
    db.delete(target); db.commit()
    request.session['flash'] = {'type': 'success', 'message': 'Пользователь успешно удален из системы.'}
    return RedirectResponse(url='/admin/users', status_code=302)


# ── Groups ────────────────────────────────────────────────────────────
@router.get('/admin/groups')
async def admin_groups(request: Request, user: User = Depends(require_admin),
                        db: Session = Depends(get_db)):
    groups = db.query(Group).options(
        joinedload(Group.curator), joinedload(Group.specialty_rel)
    ).order_by(Group.name).all()
    curators = db.query(User).filter(User.role == 'curator').all()
    departments = db.query(Department).options(
        joinedload(Department.specialties)
    ).order_by(Department.name).all()
    specialties = db.query(Specialty).options(
        joinedload(Specialty.department_rel)
    ).order_by(Specialty.name).all()
    return render(request, 'admin_groups.html', groups=groups, curators=curators,
                   departments=departments, specialties=specialties)


@router.post('/admin/add_group')
async def admin_add_group(request: Request, user: User = Depends(require_admin),
                           db: Session = Depends(get_db),
                           specialty_id: str = Form(...), group_number: str = Form(''),
                           budget_type: str = Form(''), start_year: str = Form(''),
                           course: int = Form(...), department: str = Form(''),
                           form_of_study: str = Form('очная'), curator_id: str = Form(''),
                           start_date: str = Form(''), end_date: str = Form('')):
    if not specialty_id or not course:
        request.session['flash'] = {'type': 'danger', 'message': 'Выберите специальность и укажите курс.'}
        return RedirectResponse(url='/admin/groups', status_code=302)
    spec = db.get(Specialty, int(specialty_id))
    name = build_group_name(spec.abbreviation, budget_type, start_year)
    if db.query(Group).filter(Group.name == name).first():
        request.session['flash'] = {'type': 'danger', 'message': f'Группа {name} уже существует!'}
        return RedirectResponse(url='/admin/groups', status_code=302)
    new_group = Group(
        name=name, group_number=group_number or None,
        specialty_id=spec.id, specialty_name=spec.name, specialty_code=spec.code,
        budget_type=budget_type or None, start_year=int(start_year) if start_year else None,
        course=course, department=department or None, form_of_study=form_of_study,
        start_date=parse_date(start_date), end_date=parse_date(end_date),
        curator_id=int(curator_id) if curator_id else None
    )
    db.add(new_group); db.commit()
    log_audit(db, user, 'group_create', f'Создана группа {name}')
    request.session['flash'] = {'type': 'success', 'message': f'Группа {name} успешно создана.'}
    return RedirectResponse(url='/admin/groups', status_code=302)


@router.get('/admin/edit_group/{group_id}')
async def admin_edit_group_get(request: Request, group_id: int,
                                user: User = Depends(require_admin),
                                db: Session = Depends(get_db)):
    group = db.query(Group).options(
        joinedload(Group.curator), joinedload(Group.specialty_rel)
    ).filter(Group.id == group_id).first()
    if not group: return RedirectResponse(url='/admin/groups', status_code=302)
    curators = db.query(User).filter(User.role == 'curator').all()
    specialties = db.query(Specialty).options(
        joinedload(Specialty.department_rel)
    ).order_by(Specialty.name).all()
    return render(request, 'admin_edit_group.html',
                   group=group, curators=curators, specialties=specialties)


@router.post('/admin/edit_group/{group_id}')
async def admin_edit_group_post(request: Request, group_id: int,
                                 user: User = Depends(require_admin),
                                 db: Session = Depends(get_db),
                                 group_number: str = Form(''), course: int = Form(...),
                                 department: str = Form(''), form_of_study: str = Form('очная'),
                                 curator_id: str = Form(''),
                                 start_date: str = Form(''), end_date: str = Form('')):
    group = db.get(Group, group_id)
    if not group: return RedirectResponse(url='/admin/groups', status_code=302)
    group.group_number = group_number or None
    group.course = course
    group.department = department or group.department
    group.form_of_study = form_of_study
    group.curator_id = int(curator_id) if curator_id else None
    group.start_date = parse_date(start_date)
    group.end_date = parse_date(end_date)
    db.commit()
    log_audit(db, user, 'group_edit', f'Обновлена группа {group.name}')
    request.session['flash'] = {'type': 'success', 'message': f'Группа {group.name} обновлена.'}
    return RedirectResponse(url='/admin/groups', status_code=302)


@router.post('/admin/delete_group/{group_id}')
async def admin_delete_group(request: Request, group_id: int,
                              user: User = Depends(require_admin),
                              db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group: return RedirectResponse(url='/admin/groups', status_code=302)
    students_in_group = db.query(User).filter(User.group_id == group_id).count()
    if students_in_group > 0:
        request.session['flash'] = {'type': 'danger', 'message': f'Нельзя удалить группу: к ней привязано {students_in_group} студентов.'}
        return RedirectResponse(url='/admin/groups', status_code=302)
    log_audit(db, user, 'group_delete', f'Удалена группа {group.name}')
    db.delete(group); db.commit()
    request.session['flash'] = {'type': 'success', 'message': f'Группа {group.name} удалена.'}
    return RedirectResponse(url='/admin/groups', status_code=302)


# ── Specialties ───────────────────────────────────────────────────────
@router.post('/admin/add_specialty')
async def admin_add_specialty(request: Request, user: User = Depends(require_admin),
                               db: Session = Depends(get_db),
                               specialty_name: str = Form(...),
                               specialty_code: str = Form(...),
                               department_id: str = Form('')):
    if not specialty_name or not specialty_code:
        request.session['flash'] = {'type': 'danger', 'message': 'Заполните название и код специальности.'}
        return RedirectResponse(url='/admin/groups', status_code=302)
    if db.query(Specialty).filter(Specialty.name == specialty_name).first():
        request.session['flash'] = {'type': 'danger', 'message': 'Специальность с таким названием уже существует!'}
        return RedirectResponse(url='/admin/groups', status_code=302)
    abbr = generate_abbreviation(specialty_name)
    spec = Specialty(name=specialty_name, code=specialty_code, abbreviation=abbr,
                     department_id=int(department_id) if department_id else None)
    db.add(spec); db.commit()
    request.session['flash'] = {'type': 'success', 'message': f'Специальность «{specialty_name}» ({abbr}) добавлена.'}
    return RedirectResponse(url='/admin/groups', status_code=302)


@router.post('/admin/delete_specialty/{specialty_id}')
async def admin_delete_specialty(request: Request, specialty_id: int,
                                  user: User = Depends(require_admin),
                                  db: Session = Depends(get_db)):
    spec = db.get(Specialty, specialty_id)
    if not spec: return RedirectResponse(url='/admin/groups', status_code=302)
    groups_count = db.query(Group).filter(Group.specialty_id == specialty_id).count()
    if groups_count > 0:
        request.session['flash'] = {'type': 'danger', 'message': f'Нельзя удалить специальность: к ней привязано {groups_count} групп.'}
        return RedirectResponse(url='/admin/groups', status_code=302)
    db.delete(spec); db.commit()
    request.session['flash'] = {'type': 'success', 'message': f'Специальность «{spec.name}» удалена.'}
    return RedirectResponse(url='/admin/groups', status_code=302)


# ── Import students JSON ──────────────────────────────────────────────
@router.post('/admin/import_students')
async def admin_import_students(request: Request, user: User = Depends(require_admin),
                                 db: Session = Depends(get_db),
                                 json_file: UploadFile = File(...)):
    if not json_file:
        request.session['flash'] = {'type': 'danger', 'message': 'Файл не выбран.'}
        return RedirectResponse(url='/admin/users', status_code=302)
    try:
        data = json.loads(await json_file.read())
    except Exception:
        request.session['flash'] = {'type': 'danger', 'message': 'Ошибка чтения JSON-файла.'}
        return RedirectResponse(url='/admin/users', status_code=302)
    if not isinstance(data, list): data = [data]
    imported = skipped = 0
    for item in data:
        uname = item.get('username')
        if not uname or db.query(User).filter(User.username == uname).first():
            skipped += 1; continue
        grp_name = item.get('group')
        grp_id = None
        if grp_name:
            grp = db.query(Group).filter(Group.name == grp_name).first()
            if grp: grp_id = grp.id
        db.add(User(
            username=uname, password_hash=hash_password(item.get('password', '111')),
            role=item.get('role', 'student'), last_name=item.get('last_name'),
            first_name=item.get('first_name'), patronymic=item.get('patronymic'),
            group_name=grp_name, group_id=grp_id
        ))
        imported += 1
    db.commit()
    request.session['flash'] = {'type': 'success' if imported else 'warning',
                                 'message': f'Импортировано: {imported}, пропущено: {skipped}.'}
    return RedirectResponse(url='/admin/users', status_code=302)


# ── Audit log ─────────────────────────────────────────────────────────
@router.get('/admin/audit')
async def admin_audit(request: Request, user: User = Depends(require_admin),
                       db: Session = Depends(get_db),
                       page: int = 1, action: str = '', username: str = ''):
    per_page = 50
    q = db.query(AuditLog)
    if action: q = q.filter(AuditLog.action == action)
    if username: q = q.filter(AuditLog.username.ilike(f'%{username}%'))
    q = q.order_by(desc(AuditLog.created_at))
    total = q.count()
    offset = (page - 1) * per_page
    logs = q.offset(offset).limit(per_page).all()
    actions_list = [r[0] for r in db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]
    return render(request, 'admin_audit.html', logs=logs, page=page,
                   per_page=per_page, total=total, actions=actions_list,
                   action_filter=action, user_filter=username)


# ── Import students from Excel ────────────────────────────────────────
@router.post('/admin/import_excel')
async def admin_import_excel(request: Request, user: User = Depends(require_admin),
                              db: Session = Depends(get_db),
                              excel_file: UploadFile = File(...)):
    if not excel_file:
        request.session['flash'] = {'type': 'danger', 'message': 'Файл не выбран.'}
        return RedirectResponse(url='/admin/users', status_code=302)
    from excel_import import import_students_from_excel
    imported, skipped = import_students_from_excel(excel_file)
    log_audit(db, user, 'import_excel', f'Импорт .xlsx: {imported} импортировано, {skipped} пропущено')
    request.session['flash'] = {'type': 'success' if imported else 'warning',
                                 'message': f'Импорт завершён. Создано: {imported}. Пропущено: {skipped}.'}
    return RedirectResponse(url='/admin/users', status_code=302)
