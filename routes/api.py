"""
API-эндпоинты и SSE — FastAPI.
"""
import time, json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from database import get_db
from utils import render
from dependencies import require_user, require_curator, get_current_user
from helpers import BASE_UPLOAD_FOLDER
from models import User, Event, Notification
from constants import EventStatus

router = APIRouter()





@router.get('/event/{event_id}')
async def event_detail(request: Request, event_id: int,
                        user: User = Depends(require_user)):
    db = next(get_db())
    try:
        event = db.query(Event).options(
            joinedload(Event.student), joinedload(Event.files)
        ).filter(Event.id == event_id).first()
        if not event:
            return HTMLResponse('', status_code=404)
        if user.role == 'student' and event.student_id != user.id:
            return HTMLResponse('Доступ ограничен', status_code=403)
        if user.role == 'curator':
            curator_group_ids = [g.id for g in user.curated_groups]
            if event.student.group_id not in curator_group_ids:
                return HTMLResponse('Доступ ограничен', status_code=403)
        if user.role not in ('student', 'curator', 'admin'):
            return HTMLResponse('Доступ ограничен', status_code=403)
    finally:
        db.close()
    return render(request, 'event_detail.html', event=event)


# ── Notifications ────────────────────────────────────────────────────
@router.get('/notifications')
async def notifications(request: Request, user: User = Depends(require_user)):
    db = next(get_db())
    try:
        notifs = db.query(Notification).filter(
            Notification.user_id == user.id
        ).order_by(Notification.created_at.desc()).all()
        unread = db.query(Notification).filter(
            Notification.user_id == user.id, Notification.is_read == False
        ).count()
    finally:
        db.close()
    return render(request, 'notifications.html', notifications=notifs, unread_count=unread)


@router.post('/notifications/mark_read/{notif_id}')
async def mark_notification_read(request: Request, notif_id: int,
                                  user: User = Depends(require_user)):
    db = next(get_db())
    try:
        notif = db.get(Notification, notif_id)
        if notif and notif.user_id == user.id:
            notif.is_read = True
            db.commit()
    finally:
        db.close()
    return RedirectResponse(url='/notifications', status_code=302)


@router.post('/notifications/mark_all_read')
async def mark_all_notifications_read(request: Request, user: User = Depends(require_user)):
    db = next(get_db())
    try:
        db.query(Notification).filter(
            Notification.user_id == user.id, Notification.is_read == False
        ).update({'is_read': True})
        db.commit()
    finally:
        db.close()
    request.session['flash'] = {'type': 'success', 'message': 'Все уведомления отмечены как прочитанные.'}
    return RedirectResponse(url='/notifications', status_code=302)


@router.get('/api/notifications/count')
async def api_notification_count(request: Request, user: User = Depends(require_user)):
    db = next(get_db())
    try:
        count = db.query(Notification).filter(
            Notification.user_id == user.id, Notification.is_read == False
        ).count()
    finally:
        db.close()
    return JSONResponse({'unread': count})


@router.get('/api/notifications/stream')
async def api_notifications_stream(request: Request, user: User = Depends(require_user)):
    uid = user.id
    async def event_stream():
        last_count = -1
        while True:
            try:
                db = next(get_db())
                cnt = db.query(Notification).filter(
                    Notification.user_id == uid, Notification.is_read == False
                ).count()
                db.close()
                if cnt != last_count:
                    last_count = cnt
                    yield f'data: {{"unread":{cnt}}}\n\n'
            except Exception:
                pass
            await time.sleep(3)
    return StreamingResponse(event_stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache',
                                      'X-Accel-Buffering': 'no',
                                      'Connection': 'keep-alive'})


# ── Curator API ──────────────────────────────────────────────────────
@router.get('/curator/api/events')
async def curator_api_events(request: Request, user: User = Depends(require_curator),
                              scope: str = 'pending', q: str = ''):
    db = next(get_db())
    try:
        group_ids = [g.id for g in user.curated_groups]
        group_students = db.query(User).filter(
            User.role == 'student', User.group_id.in_(group_ids)
        ).all()
        student_ids = [s.id for s in group_students]

        if scope == 'resolved':
            query = db.query(Event).options(joinedload(Event.student)).filter(
                Event.student_id.in_(student_ids),
                Event.status.in_(['approved', 'rejected'])
            )
        else:
            query = db.query(Event).options(joinedload(Event.student)).filter(
                Event.student_id.in_(student_ids),
                Event.status == EventStatus.PENDING
            )
        if q:
            like = f'%{q}%'
            query = query.filter(or_(Event.title.ilike(like), Event.description.ilike(like)))
        events = query.order_by(Event.created_at.desc()).all()
    finally:
        db.close()
    return JSONResponse({'events': [_ser_event(e) for e in events], 'scope': scope})


# ── Student API ──────────────────────────────────────────────────────
@router.get('/student/api/events')
async def student_api_events(request: Request, user: User = Depends(require_user),
                              q: str = ''):
    db = next(get_db())
    try:
        query = db.query(Event).options(joinedload(Event.files)).filter(
            Event.student_id == user.id
        )
        if q:
            like = f'%{q}%'
            query = query.filter(or_(Event.title.ilike(like), Event.description.ilike(like)))
        events = query.order_by(Event.created_at.desc()).all()
    finally:
        db.close()
    return JSONResponse({'events': [_ser_event_student(e) for e in events]})


def _ser_event(e):
    return {
        'id': e.id, 'title': e.title, 'description': e.description or '',
        'category': e.category, 'status': e.status, 'score': e.score,
        'curator_comment': e.curator_comment or '',
        'created_at': e.created_at.strftime('%d.%m.%Y %H:%M') if e.created_at else '',
        'student': e.student.username if e.student else 'Удален'
    }


def _ser_event_student(e):
    return {
        'id': e.id, 'title': e.title, 'description': e.description or '',
        'category': e.category, 'status': e.status, 'score': e.score,
        'curator_comment': e.curator_comment or '',
        'created_at': e.created_at.strftime('%d.%m.%Y %H:%M') if e.created_at else '',
        'files': [{'path': f.file_path, 'type': f.file_type} for f in e.files]
    }
