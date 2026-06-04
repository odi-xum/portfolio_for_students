"""
Аутентификация: логин / логаут (FastAPI).
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from utils import render
from dependencies import create_access_token, verify_password, require_user
from helpers import log_audit
from models import User

router = APIRouter()


@router.get('/')
async def login_page(request: Request):
    user = getattr(request.state, 'user', None)
    if user:
        return RedirectResponse(url=f'/{user.role}/dashboard', status_code=302)
    return render(request, 'login.html')


@router.post('/')
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...),
                       db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        token = create_access_token({'sub': str(user.id)})
        ip = request.client.host if request.client else None
        log_audit(db, user, 'login', 'Вход в систему', ip)
        response = RedirectResponse(url=f'/{user.role}/dashboard', status_code=302)
        response.set_cookie(key='access_token', value=token, httponly=True,
                            samesite='lax', max_age=28800)
        return response
    ip = request.client.host if request.client else None
    log_audit(db, username, 'login_failed', 'Неудачная попытка входа', ip)
    request.session['flash'] = {'type': 'danger', 'message': 'Неверный логин или пароль. Попробуйте еще раз.'}
    return render(request, 'login.html')


@router.get('/logout')
async def logout(request: Request, user: User = Depends(require_user)):
    db = next(get_db())
    try:
        ip = request.client.host if request.client else None
        log_audit(db, user, 'logout', 'Выход из системы', ip)
    finally:
        db.close()
    response = RedirectResponse(url='/', status_code=302)
    response.delete_cookie('access_token')
    return response
