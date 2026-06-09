"""
Комиссия — FastAPI.
Просмотр всех постов/профилей, изменение оценок, статистика с графиками.
"""
from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from utils import render
from dependencies import require_commission
from helpers import log_audit
from models import User, Event, EventFile
from constants import EventStatus
from services.commission_service import (
    get_all_students, get_all_groups, get_group_stats,
    get_category_distribution, get_score_distribution,
    get_status_distribution, get_top_students, get_student_stats_for_group,
)
from services.notification_service import notify_user

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────
@router.get('/commission/dashboard')
async def commission_dashboard(request: Request,
                                user: User = Depends(require_commission),
                                db: Session = Depends(get_db)):
    groups = get_group_stats(db)
    total_events = db.query(Event).count()
    total_students = db.query(User).filter(User.role == 'student').count()
    best_group = groups[0] if groups else None
    top_students = get_top_students(db, limit=5)
    return render(request, 'commission_dashboard.html',
                  groups=groups, total_events=total_events,
                  total_students=total_students, best_group=best_group,
                  top_students=top_students)


# ── Все посты (с фильтрацией) ────────────────────────────────────────────
@router.get('/commission/posts')
async def commission_posts(request: Request,
                            user: User = Depends(require_commission),
                            db: Session = Depends(get_db),
                            status: str = Query('all'),
                            group_id: int = Query(None),
                            search: str = Query('')):
    q = db.query(Event).options(joinedload(Event.student), joinedload(Event.files))

    if status != 'all':
        q = q.filter(Event.status == status)
    if group_id:
        group_student_ids = [
            s.id for s in db.query(User).filter(
                User.role == 'student', User.group_id == group_id
            ).all()
        ]
        q = q.filter(Event.student_id.in_(group_student_ids))
    if search:
        q = q.filter(Event.title.ilike(f'%{search}%'))

    events = q.order_by(Event.created_at.desc()).all()
    groups = get_all_groups(db)
    return render(request, 'commission_posts.html',
                  events=events, groups=groups,
                  current_status=status, current_group_id=group_id,
                  current_search=search)


# ── Студенты (список с фильтрацией по группе) ────────────────────────────
@router.get('/commission/students')
async def commission_students(request: Request,
                               user: User = Depends(require_commission),
                               db: Session = Depends(get_db),
                               group_id: int = Query(None),
                               search: str = Query('')):
    q = db.query(User).filter(User.role == 'student')
    if group_id:
        q = q.filter(User.group_id == group_id)
    if search:
        q = q.filter(
            (User.last_name.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.username.ilike(f'%{search}%'))
        )
    students = q.order_by(User.last_name).all()
    groups = get_all_groups(db)
    return render(request, 'commission_students.html',
                  students=students, groups=groups,
                  current_group_id=group_id, current_search=search)


# ── Профиль студента (просмотр мероприятий) ──────────────────────────────
@router.get('/commission/student/{student_id}')
async def commission_student_view(request: Request, student_id: int,
                                   user: User = Depends(require_commission),
                                   db: Session = Depends(get_db)):
    student = db.get(User, student_id)
    if not student or student.role != 'student':
        request.session['flash'] = {'type': 'danger', 'message': 'Студент не найден.'}
        return RedirectResponse(url='/commission/students', status_code=302)
    events = db.query(Event).options(joinedload(Event.files)).filter(
        Event.student_id == student_id
    ).order_by(Event.created_at.desc()).all()
    approved_total = sum(e.score or 0 for e in events if e.is_approved)
    return render(request, 'commission_student_detail.html',
                  student=student, events=events, approved_total=approved_total)


# ── Изменение оценки ─────────────────────────────────────────────────────
@router.post('/commission/change_score/{event_id}')
async def commission_change_score(request: Request, event_id: int,
                                   user: User = Depends(require_commission),
                                   score: int = Form(...),
                                   comment: str = Form('')):
    if score < 1 or score > 5:
        request.session['flash'] = {'type': 'danger', 'message': 'Оценка должна быть от 1 до 5.'}
        return RedirectResponse(url='/commission/posts', status_code=302)

    db = next(get_db())
    try:
        event = db.get(Event, event_id)
        if not event:
            request.session['flash'] = {'type': 'danger', 'message': 'Мероприятие не найдено.'}
            return RedirectResponse(url='/commission/posts', status_code=302)

        old_score = event.score
        event.score = score
        if comment:
            event.curator_comment = comment
        db.commit()

        log_audit(db, user, 'commission_change_score',
                  f'Изменена оценка мероприятия #{event.id} «{event.title}» '
                  f'с {old_score} на {score}, комментарий: {comment or "нет"}')
        request.session['flash'] = {'type': 'success',
                                     'message': f'Оценка мероприятия «{event.title}» изменена на {score}.'}
    finally:
        db.close()
    return RedirectResponse(url=f'/commission/posts', status_code=302)


# ── Статистика ────────────────────────────────────────────────────────────
@router.get('/commission/stats')
async def commission_stats(request: Request,
                            user: User = Depends(require_commission),
                            db: Session = Depends(get_db)):
    group_stats = get_group_stats(db)
    category_dist = get_category_distribution(db)
    score_dist = get_score_distribution(db)
    status_dist = get_status_distribution(db)
    top_students = get_top_students(db, limit=20)

    return render(request, 'commission_stats.html',
                  group_stats=group_stats,
                  category_dist=category_dist,
                  score_dist=score_dist,
                  status_dist=status_dist,
                  top_students=top_students)


# ── API: данные для графиков (JSON) ──────────────────────────────────────
@router.get('/commission/api/group_scores')
async def api_group_scores(db: Session = Depends(get_db),
                            user: User = Depends(require_commission)):
    stats = get_group_stats(db)
    return {
        'labels': [s['group'].name for s in stats],
        'avg_scores': [s['avg_score'] for s in stats],
        'total_scores': [s['total_score'] for s in stats],
    }


@router.get('/commission/api/student_scores/{group_id}')
async def api_student_scores(group_id: int,
                              db: Session = Depends(get_db),
                              user: User = Depends(require_commission)):
    stats = get_student_stats_for_group(db, group_id)
    return {
        'labels': [s['student'].last_name or s['student'].username for s in stats],
        'total_scores': [s['total_score'] for s in stats],
        'event_counts': [s['event_count'] for s in stats],
    }
