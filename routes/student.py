"""
Студент — FastAPI.
"""
import os
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from werkzeug.utils import secure_filename

from database import get_db
from utils import render
from dependencies import require_student
from helpers import allowed_file, now_utc, log_audit, BASE_UPLOAD_FOLDER
from models import User, Event, EventFile
from constants import EventStatus
from services.student_service import get_student_event_stats
from services.notification_service import notify_curators_of_group
from services.ok_service import get_ok_stats, all_ok_completed
from pdf_export import generate_portfolio_pdf

router = APIRouter()


@router.get('/student/dashboard')
async def student_dashboard(request: Request, user: User = Depends(require_student),
                             db: Session = Depends(get_db)):
    stats = get_student_event_stats(db, user.id)
    ok_stats = get_ok_stats(db, user.id)
    ok_all_done = all_ok_completed(db, user.id)
    return render(request, 'student.html', total=stats['total'],
                   approved=stats['approved'], pending=stats['pending'],
                   rejected=stats['rejected'], ok_stats=ok_stats, ok_all_done=ok_all_done)


@router.get('/student/create')
async def student_create_get(request: Request, user: User = Depends(require_student)):
    return render(request, 'student_create.html')


@router.post('/student/create')
async def student_create_post(request: Request, user: User = Depends(require_student),
                               title: str = Form(...), description: str = Form(''),
                               category: str = Form(''),
                               files: list[UploadFile] = File(...)):
    db = next(get_db())
    try:
        valid_files = [f for f in files if f.filename and allowed_file(f.filename)]
        if not title:
            request.session['flash'] = {'type': 'warning', 'message': 'Пожалуйста, заполните название мероприятия.'}
            return RedirectResponse(url='/student/create', status_code=302)
        if not valid_files:
            request.session['flash'] = {'type': 'danger', 'message': 'Ошибка: Не хватает доказательств! Прикрепите JPG/PNG или PDF.'}
            return RedirectResponse(url='/student/create', status_code=302)

        new_event = Event(
            student_id=user.id, title=title, description=description or None,
            category=category or None, status=EventStatus.PENDING, created_at=now_utc()
        )
        db.add(new_event)
        db.flush()

        safe_username = secure_filename(user.username)
        safe_title = secure_filename(title)
        event_dir = os.path.join(BASE_UPLOAD_FOLDER, 'students', safe_username, f"{new_event.id}_{safe_title}")
        os.makedirs(event_dir, exist_ok=True)

        for f in valid_files:
            filename = secure_filename(f.filename)
            file_path = os.path.join(event_dir, filename)
            content = await f.read()
            with open(file_path, 'wb') as wf:
                wf.write(content)
            ext = filename.rsplit('.', 1)[1].lower()
            db.add(EventFile(event_id=new_event.id, file_path=file_path, file_type=ext))

        if user.group_id:
            notify_curators_of_group(db, user.group_id,
                f"Студент {user.username} опубликовал новое мероприятие: '{title}'. Требуется проверка.",
                f'/event/{new_event.id}')

        db.commit()
        log_audit(db, user, 'event_create', f'Создано мероприятие #{new_event.id} «{title}»')
        request.session['flash'] = {'type': 'success', 'message': 'Мероприятие успешно опубликовано.'}
    finally:
        db.close()
    return RedirectResponse(url='/student/history', status_code=302)


@router.get('/student/history')
async def student_history(request: Request, user: User = Depends(require_student)):
    db = next(get_db())
    try:
        events = db.query(Event).options(joinedload(Event.files)).filter(
            Event.student_id == user.id
        ).order_by(Event.created_at.desc()).all()
    finally:
        db.close()
    return render(request, 'student_history.html', events=events)


@router.post('/student/notify_ok')
async def student_notify_ok(request: Request, user: User = Depends(require_student)):
    db = next(get_db())
    try:
        done = all_ok_completed(db, user.id)
    finally:
        db.close()

    if done:
        if user.group_id:
            db2 = next(get_db())
            try:
                notify_curators_of_group(db2, user.group_id,
                    f"Студент {user.full_name} выполнил все общие компетенции (ОК-1 — ОК-9). Требуется подтверждение.")
            finally:
                db2.close()
        request.session['flash'] = {'type': 'success', 'message': 'Уведомление отправлено куратору.'}
    else:
        request.session['flash'] = {'type': 'warning', 'message': 'Не все общие компетенции выполнены.'}
    return RedirectResponse(url='/student/dashboard', status_code=302)


@router.get('/student/portfolio_pdf')
async def student_portfolio_pdf(request: Request, user: User = Depends(require_student)):
    buf = generate_portfolio_pdf(user.username)
    if not buf:
        request.session['flash'] = {'type': 'danger', 'message': 'Ошибка генерации портфолио.'}
        return RedirectResponse(url='/student/history', status_code=302)
    filename = f'portfolio_{user.username}.pdf'
    return StreamingResponse(buf, media_type='application/pdf',
                             headers={'Content-Disposition': f'attachment; filename={filename}'})
