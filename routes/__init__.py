"""
Регистрация маршрутов — все роутеры подключаются в main.py.
"""
# Роутеры импортируются и подключаются в main.py через APIRouter.
# Этот файл оставлен для обратной совместимости.
from .auth import router as auth_router
from .admin import router as admin_router
from .student import router as student_router
from .curator import router as curator_router
from .api import router as api_router
from .rating import router as rating_router
from .profile import router as profile_router
from .portfolio import router as portfolio_router
