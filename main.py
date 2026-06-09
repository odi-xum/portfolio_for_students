"""
FastAPI entry point. Многопоточный сервер, SSE без блокировок.
"""
import logging, os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import init_db, SessionLocal
from utils import render, templates
from helpers import BASE_UPLOAD_FOLDER, verify_csrf_token
from dependencies import SECRET_KEY, get_current_user_sync

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
log_dir = Path('/tmp/diplom_logs')
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_dir / 'app.log', encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('app')


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('=== FastAPI запущен ===')
    init_db()
    yield
    SessionLocal.remove()
    logger.info('=== FastAPI остановлен ===')


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title='ИС Портфолио студентов', lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount('/static', StaticFiles(directory=str(Path(__file__).parent / 'static')), name='static')

diplom_path = Path(BASE_UPLOAD_FOLDER)
diplom_path.mkdir(parents=True, exist_ok=True)
app.mount('/diplom', StaticFiles(directory=str(diplom_path)), name='diplom')


# ---------------------------------------------------------------------------
# Глобалы шаблонов
# ---------------------------------------------------------------------------
# url_for передаётся через контекст render() в utils.py
# templates.env.globals не используем — Jinja2 3.1.6 + Python 3.14 несовместимость


# ---------------------------------------------------------------------------
# Middleware: загрузка пользователя + защитные заголовки
# ---------------------------------------------------------------------------
@app.middleware('http')
async def load_user_and_security(request: Request, call_next):
    db = SessionLocal()
    try:
        user = get_current_user_sync(request, db)
        request.state.user = user
    finally:
        db.close()

    response = await call_next(request)

    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if not request.url.path.startswith('/portfolio/'):
        response.headers['Cache-Control'] = 'no-store'

    return response


# ---------------------------------------------------------------------------
# CSRF middleware
# ---------------------------------------------------------------------------
@app.middleware('http')
async def csrf_middleware(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'DELETE'):
        path = request.url.path
        if path.startswith('/api/notifications/stream') or path.startswith('/admin/import_'):
            return await call_next(request)
        if 'session' not in request.scope:
            return await call_next(request)
        try:
            form = await request.form()
            token = form.get('_csrf_token') or request.headers.get('X-CSRF-Token', '')
        except Exception:
            token = request.headers.get('X-CSRF-Token', '')
        if not token or not verify_csrf_token(token, request):
            from fastapi.responses import HTMLResponse
            return HTMLResponse('CSRF-токен недействителен', status_code=400)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.exception_handler(403)
async def forbidden(request, exc):
    return render(request, '403.html', status_code=403)

@app.exception_handler(404)
async def not_found(request, exc):
    return render(request, '404.html', status_code=404)

@app.exception_handler(500)
async def server_error(request, exc):
    logger.exception('HTTP 500: %s', exc)
    try:
        db = SessionLocal()
        db.rollback()
        db.close()
    except Exception:
        pass
    return render(request, '500.html', status_code=500)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.student import router as student_router
from routes.curator import router as curator_router
from routes.api import router as api_router
from routes.rating import router as rating_router
from routes.profile import router as profile_router
from routes.portfolio import router as portfolio_router
from routes.commission import router as commission_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(student_router)
app.include_router(curator_router)
app.include_router(commission_router)
app.include_router(api_router)
app.include_router(rating_router)
app.include_router(profile_router)
app.include_router(portfolio_router)


if __name__ == '__main__':
    import uvicorn
    debug = os.environ.get('FASTAPI_DEBUG', '1') == '1'
    uvicorn.run('main:app', host='127.0.0.1', port=5000, reload=debug, log_level='info')
