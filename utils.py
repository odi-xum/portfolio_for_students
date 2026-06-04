"""
Общий экземпляр Jinja2Templates и хелпер рендера.
"""
from pathlib import Path
from fastapi import Request
from fastapi.templating import Jinja2Templates
from helpers import generate_csrf_token

templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
# Python 3.14 / Jinja2 3.1.6 cache fix — отключаем LRUCache
class _NullCache:
    def get(self, key): return None
    def __contains__(self, key): return False
    def __setitem__(self, key, value): pass
    def __getitem__(self, key): raise KeyError(key)
    def __delitem__(self, key): pass
    def clear(self): pass
templates.env.cache = _NullCache()


def render(request: Request, template: str, **ctx):
    """Рендер с общими переменными (current_user, csrf_token, flash)."""
    user = getattr(request.state, 'user', None)
    flash = request.session.pop('flash', None) if hasattr(request, 'session') else None
    status_code = ctx.pop('status_code', 200) or 200
    try:
        csrf = generate_csrf_token(request)
    except Exception:
        csrf = ''
    from main import app
    def _url_for(name, **kw):
        if name == 'static':
            return f"/static/{kw.get('filename', '')}"
        try:
            return app.url_path_for(name, **kw)
        except Exception:
            return f'/{name.replace("_", "/")}'
    context = {
        'request': request,
        'current_user': user,
        'csrf_token': csrf,
        'flash': flash,
        'url_for': _url_for,
    }
    context.update(ctx)
    return templates.TemplateResponse(request, template, context, status_code=status_code)
