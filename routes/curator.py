"""
Куратор — FastAPI.
"""
import io, os, zipfile
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from utils import render
from dependencies import require_curator
from helpers import log_audit
from models import User, Event
from constants import EventStatus
from export import generate_report
from services.curator_service import (
    get_curator_dashboard_stats, get_curator_students, get_curator_events,
)
from services.notification_service import notify_user
from services.ok_service import get_ok_stats, toggle_override, OK_LIST
from pdf_export import generate_portfolio_pdf

router = APIRouter()


@router.get('/curator/dashboard')
async def curator_dashboard(request: Request, user: User = Depends(require_curator)):
    stats = get_curator_dashboard_stats(user)
    groups = user.curated_groups
    students = get_curator_students(user)
    return render(request, 'curator.html', pending_count=stats['pending'],
                   approved_count=stats['approved'], rejected_count=stats['rejected'],
                   total_resolved=stats['total_resolved'], groups=groups, students=students)


@router.get('/curator/pending')
async def curator_pending(request: Request, user: User = Depends(require_curator)):
    events = get_curator_events(user, EventStatus.PENDING)
    return render(request, 'curator_pending.html', events=events)


@router.get('/curator/resolved')
async def curator_resolved(request: Request, user: User = Depends(require_curator)):
    events = get_curator_events(user, 'resolved')
    return render(request, 'curator_resolved.html', events=events)


@router.post('/curator/evaluate/{event_id}')
async def curator_evaluate(request: Request, event_id: int,
                            user: User = Depends(require_curator),
                            action: str = Form(...), comment: str = Form(''),
                            score: int = Form(5)):
    db = next(get_db())
    try:
        event = db.get(Event, event_id)
        if not event: return RedirectResponse(url='/curator/pending', status_code=302)

        if action == 'approve':
            event.score = score; event.curator_comment = comment or None
            event.status = EventStatus.APPROVED
            notify_user(event.student_id,
                f"Куратор одобрил ваше мероприятие «{event.title}» с оценкой {score}.",
                f'/event/{event.id}')
            log_audit(db, user, 'event_approve',
                      f'Одобрено мероприятие #{event.id} «{event.title}», оценка {score}')

        elif action == 'reject':
            if not comment.strip():
                request.session['flash'] = {'type': 'danger', 'message': 'При отклонении комментарий обязателен!'}
                return RedirectResponse(url='/curator/pending', status_code=302)
            event.curator_comment = comment
            event.status = EventStatus.REJECTED
            notify_user(event.student_id,
                f"Куратор отклонил ваше мероприятие «{event.title}». Причина: {comment}",
                f'/event/{event.id}')
            log_audit(db, user, 'event_reject',
                      f'Отклонено мероприятие #{event.id} «{event.title}»')

        db.commit()
    finally:
        db.close()
    return RedirectResponse(url='/curator/pending', status_code=302)


@router.get('/curator/export')
async def curator_export_get(request: Request, user: User = Depends(require_curator)):
    db = next(get_db())
    try:
        groups = user.curated_groups
        group_ids = [g.id for g in groups]
        all_students = db.query(User).filter(
            User.role == 'student', User.group_id.in_(group_ids)
        ).order_by(User.last_name).all()
    finally:
        db.close()
    return render(request, 'curator_export.html', students=all_students, groups=groups)


@router.post('/curator/export')
async def curator_export_post(request: Request, user: User = Depends(require_curator),
                               student_ids: list[str] = Form(default=[]),
                               group_id: str = Form(''), include_charts: bool = Form(False),
                               include_details: bool = Form(False),
                               status_filter: str = Form('all'),
                               date_from: str = Form(''), date_to: str = Form('')):
    db = next(get_db())
    try:
        groups = user.curated_groups
        group_ids_list = [g.id for g in groups]
        all_students = db.query(User).filter(
            User.role == 'student', User.group_id.in_(group_ids_list)
        ).order_by(User.last_name).all()

        base_students = all_students
        if group_id:
            base_students = [s for s in all_students if str(s.group_id) == group_id]
        selected = [s for s in base_students if str(s.id) in student_ids] or base_students

        buf = generate_report(
            db, students=selected, include_charts=include_charts,
            include_details=include_details, status_filter=status_filter,
            date_from=date_from or None, date_to=date_to or None,
        )
    finally:
        db.close()

    group_label = group_id or 'vse_gruppy'
    filename = f'otchet_kuratora_{group_label}.xlsx'
    return StreamingResponse(
        buf,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@router.post('/curator/portfolio_zip')
async def curator_portfolio_zip(request: Request, user: User = Depends(require_curator),
                                 student_ids: list[str] = Form(default=[])):
    if not student_ids:
        request.session['flash'] = {'type': 'warning', 'message': 'Не выбрано ни одного студента.'}
        return RedirectResponse(url='/curator/export', status_code=302)

    db = next(get_db())
    try:
        group_ids = [g.id for g in user.curated_groups]
        students = db.query(User).filter(
            User.id.in_([int(sid) for sid in student_ids]),
            User.role == 'student', User.group_id.in_(group_ids)
        ).all()
    finally:
        db.close()

    if not students:
        request.session['flash'] = {'type': 'warning', 'message': 'Студенты не найдены.'}
        return RedirectResponse(url='/curator/export', status_code=302)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for student in students:
            pdf_buf = generate_portfolio_pdf(student.username)
            if pdf_buf is None: continue
            safe_name = student.username.replace('/', '_').replace('\\', '_')
            zf.writestr(f'portfolio_{safe_name}.pdf', pdf_buf.getvalue())
    zip_buf.seek(0)

    return StreamingResponse(
        zip_buf,
        media_type='application/zip',
        headers={'Content-Disposition': 'attachment; filename=student_portfolios.zip'},
    )


# ── OK — просмотр компетенций студента ───────────────────────────────
@router.get('/curator/student_ok/{student_id}')
async def curator_student_ok(request: Request, student_id: int,
                              user: User = Depends(require_curator)):
    db = next(get_db())
    try:
        student = db.get(User, student_id)
        if not student or student.role != 'student':
            return RedirectResponse(url='/curator/dashboard', status_code=302)
        curator_gids = [g.id for g in user.curated_groups]
        if student.group_id not in curator_gids:
            return RedirectResponse(url='/curator/dashboard', status_code=302)

        ok_stats = get_ok_stats(student_id)
        current_category = request.query_params.get('category')

        if current_category == 'none':
            events = db.query(Event).filter(
                Event.student_id == student_id, Event.category.is_(None)
            ).order_by(Event.created_at.desc()).all()
        elif current_category:
            events = db.query(Event).filter_by(
                student_id=student_id, category=current_category
            ).order_by(Event.created_at.desc()).all()
        else:
            events = db.query(Event).filter_by(student_id=student_id).order_by(
                Event.created_at.desc()
            ).all()
    finally:
        db.close()

    return render(request, 'curator_student_ok.html', student=student,
                   ok_stats=ok_stats, ok_list=OK_LIST,
                   current_category=current_category, events=events)


@router.post('/curator/toggle_ok/{student_id}/{ok_category}')
async def curator_toggle_ok(request: Request, student_id: int, ok_category: str,
                             user: User = Depends(require_curator)):
    if ok_category not in OK_LIST:
        request.session['flash'] = {'type': 'danger', 'message': f'Некорректная категория: {ok_category}'}
        return RedirectResponse(url='/curator/dashboard', status_code=302)
    added = toggle_override(student_id, user.id, ok_category)
    label = 'засчитана' if added else 'отменена'
    db = next(get_db())
    try:
        log_audit(db, user, f'ok_{"override" if added else "undo"}',
                  f'{label.capitalize()} {ok_category} для студента #{student_id}')
    finally:
        db.close()
    request.session['flash'] = {'type': 'success' if added else 'warning',
                                 'message': f'Категория {ok_category} {label} для студента.'}
    return RedirectResponse(url=f'/curator/student_ok/{student_id}', status_code=302)
