"""
Профиль / смена пароля — FastAPI.
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from utils import render
from dependencies import require_user, hash_password, verify_password

router = APIRouter()


@router.get('/profile')
async def profile_get(request: Request, user: User = Depends(require_user)):
    return render(request, 'profile.html')


@router.post('/profile')
async def profile_post(request: Request, user: User = Depends(require_user),
                        last_name: str = Form(''), first_name: str = Form(''),
                        patronymic: str = Form(''), old_password: str = Form(''),
                        new_password: str = Form(''), confirm_password: str = Form('')):
    if last_name: user.last_name = last_name
    if first_name: user.first_name = first_name
    if patronymic: user.patronymic = patronymic

    if new_password:
        if not old_password or not verify_password(old_password, user.password_hash):
            request.session['flash'] = {'type': 'danger', 'message': 'Старый пароль указан неверно.'}
            return RedirectResponse(url='/profile', status_code=302)
        if new_password != confirm_password:
            request.session['flash'] = {'type': 'danger', 'message': 'Новый пароль и подтверждение не совпадают.'}
            return RedirectResponse(url='/profile', status_code=302)
        if len(new_password) < 3:
            request.session['flash'] = {'type': 'danger', 'message': 'Новый пароль слишком короткий (мин. 3 символа).'}
            return RedirectResponse(url='/profile', status_code=302)
        user.password_hash = hash_password(new_password)

    db = next(get_db())
    try:
        db.commit()
    finally:
        db.close()
    request.session['flash'] = {'type': 'success', 'message': 'Данные сохранены.'}
    return RedirectResponse(url='/profile', status_code=302)
