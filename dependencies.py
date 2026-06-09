"""
FastAPI dependencies — аутентификация через JWT в куке.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Request, HTTPException, Depends
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import User

SECRET_KEY = os.environ.get('SECRET_KEY', 'gruvbox-material-secure-shadow-key-1984')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _decode_token(token: str) -> Optional[int]:
    """Синхронная расшифровка JWT, возвращает user_id или None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get('sub')
        return user_id
    except JWTError:
        return None


def get_current_user_sync(request: Request, db: Session = None) -> Optional[User]:
    """Синхронная версия — для middleware."""
    token = request.cookies.get('access_token')
    if not token:
        return None
    user_id = _decode_token(token)
    if user_id is None:
        return None
    if db is None:
        db = SessionLocal()
        try:
            return db.get(User, int(user_id))
        finally:
            db.close()
    return db.get(User, int(user_id))


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get('access_token')
    if not token:
        return None
    user_id = _decode_token(token)
    if user_id is None:
        return None
    return db.get(User, int(user_id))


async def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail='Требуется авторизация')
    return user


def require_role(role: str):
    async def _check(user: User = Depends(require_user)):
        if user.role != role:
            raise HTTPException(status_code=403, detail='Доступ ограничен')
        return user
    return _check


require_admin      = require_role('admin')
require_curator    = require_role('curator')
require_student    = require_role('student')
require_commission = require_role('commission')
