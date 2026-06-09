# AGENTS.md — Руководство по работе с репозиторием Diplom

## Project Overview

FastAPI-приложение для управления портфолио достижений студентов. Три роли:

- **admin** — управление пользователями, группами, специальностями, импорт студентов
- **student** — создание мероприятий, загрузка файлов, просмотр портфолио
- **curator** — проверка мероприятий, отметка ОК, просмотр рейтинга, экспорт отчётов

> Роль **commission** и связанные с ней маршруты/модели (арбитраж спорных мероприятий, стипендиальные заявки) были удалены при миграции с Flask на FastAPI.

## Essential Commands

### Запуск (разработка)

```bash
source venv/bin/activate
python main.py
```

По умолчанию — `http://localhost:5000`, hot-reload (uvicorn).

### Инициализация БД

```bash
python sql/load.py
```

Таблицы создаются автоматически при первом запуске (`init_db()` в `main.py`).

### Генерация тестовых мероприятий

```bash
python sql/seed_events.py
```

Создаёт 3–8 реалистичных мероприятий для каждого студента с PNG-сертификатами/дипломами и PDF-документами.

### Тестовые пользователи (пароль: `111`)

| Login | Role | Group |
|-------|------|-------|
| `admin` | admin | — |
| `cur1` | curator | ИСП-Б-2022 |
| `student1` | student | ИСП-Б-2022 |
| `student2` | student | ИСП-Б-2022 |
| `student3` | student | ИСП-Б-2022 |

Всего 50 студентов, 7 кураторов, 8 групп, 3 отделения, 8 специальностей.

> Кураторы: cur1..cur7. Студенты: student1..student25 и 25 фиктивных (login = фамилия латиницей).

### Вспомогательные скрипты

```bash
python check_db.py          # просмотр содержимого БД
python sql/load.py          # загрузка seed-данных
python sql/seed_events.py   # генерация мероприятий с файлами
```

## Code Organization

### Архитектура: FastAPI Application

`main.py` — точка входа. Создаёт FastAPI-приложение, настраивает middleware, монтирует статику, подключает роутеры.

```
app = FastAPI(title='ИС Портфолио студентов', lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount('/static', StaticFiles(...))
app.mount('/diplom', StaticFiles(...))

# Middleware:
#   1. load_user_and_security — загрузка пользователя из JWT + security-заголовки
#   2. csrf_middleware — защита POST/PUT/DELETE (кроме SSE и импорта)

# Роутеры регистрируются через app.include_router()
```

- Запуск через `uvicorn` с hot-reload
- SQLite с WAL mode + synchronous=NORMAL
- PostgreSQL через Docker Compose (продакшен)

### Core Files

| File | Purpose |
|------|---------|
| **`main.py`** | Точка входа, lifespan, middleware, error handlers, регистрация роутеров |
| **`database.py`** | SQLAlchemy 2.0 engine, SessionLocal, Base, get_db dependency, init_db |
| **`dependencies.py`** | JWT-аутентификация, bcrypt, require_role, get_current_user |
| **`models.py`** | SQLAlchemy 2.0 модели (без Flask-зависимостей) |
| **`constants.py`** | StrEnum-классы (`UserRole`, `EventStatus`), MIME-типы, лимиты |
| **`helpers.py`** | CSRF-токены (Starlette Session), аудит-лог, загрузка файлов, работа с датами |
| **`utils.py`** | Jinja2Templates инстанс, функция `render()` с общими переменными |
| **`routes/`** | Модульные группы маршрутов (APIRouter) |
| **`services/`** | Слой бизнес-логики |
| **`export.py`** | Генерация Excel-отчётов с графиками (openpyxl) |
| **`pdf_export.py`** | Генерация PDF-портфолио (weasyprint) |
| **`excel_import.py`** | Импорт студентов из .xlsx |
| **`check_db.py`** | Просмотр БД (отделения, специальности, группы, пользователи) |

### Routes (`routes/`)

| Module | Routes | Role |
|--------|--------|------|
| `auth.py` | `GET /` (login), `POST /`, `GET /logout` | Все |
| `admin.py` | `/admin/dashboard`, `/admin/users`, `/admin/add_user`, `/admin/delete_user/<id>`, `/admin/groups`, `/admin/create_group`, `/admin/edit_group/<id>`, `/admin/delete_group/<id>`, `/admin/import_students`, `/admin/audit` | admin |
| `student.py` | `/student/dashboard`, `/student/create`, `/student/history`, `/student/notify_ok`, `/student/portfolio_pdf` | student |
| `curator.py` | `/curator/dashboard`, `/curator/pending`, `/curator/resolved`, `/curator/evaluate/<event_id>`, `/curator/export`, `/curator/portfolio_zip`, `/curator/student_ok/<student_id>`, `/curator/toggle_ok_override` | curator |
| `api.py` | `/event/<id>`, `/notifications`, `/notifications/mark_read/<id>`, `/notifications/mark_all_read`, `/api/notifications/count`, `/api/notifications/stream` (SSE), `/curator/api/events`, `/student/api/events` | Все / curator / student |
| `rating.py` | `/rating` | student, curator |
| `profile.py` | `/profile` (изменение ФИО, пароля) | Все |
| `portfolio.py` | `/portfolio/<username>` (публичное, без аутентификации) | Все |

> Роуты регистрируются напрямую в `main.py`, без `routes/__init__.py`.

### Services (`services/`)

| Service | Role |
|---------|------|
| `curator_service.py` | Поиск студентов куратора, агрегация статистики по группам |
| `student_service.py` | Статистика мероприятий студента |
| `notification_service.py` | Создание уведомлений для одного/всех кураторов группы |
| `ok_service.py` | Статистика по общим компетенциям (ОК-1…ОК-9), отметки куратора, toggle override |

### Templates

```
templates/
├── base.html                  # Базовый шаблон: навигация по ролям, flash-сообщения
├── login.html                 # Страница входа
├── admin.html                 # Панель администратора
├── admin_users.html           # Управление пользователями
├── admin_groups.html          # Список групп
├── admin_edit_group.html      # Редактирование группы
├── admin_audit.html           # Аудит-лог
├── student.html               # Панель студента
├── student_create.html        # Создание мероприятия
├── student_history.html       # История мероприятий
├── curator.html               # Панель куратора
├── curator_pending.html       # Ожидающие проверки мероприятия
├── curator_resolved.html      # Решённые мероприятия
├── curator_export.html        # Экспорт отчётов
├── curator_student_ok.html    # ОК студента
├── event_detail.html          # Детали мероприятия + файлы
├── portfolio.html             # Публичное портфолио / PDF
├── profile.html               # Профиль / смена пароля
├── rating.html                # Рейтинг студентов
├── notifications.html         # Уведомления
├── 403.html / 404.html / 500.html  # Страницы ошибок
```

### Static Files

```
static/
├── css/
│   └── style.css
└── js/
    └── app.js                 # AJAX-поиск, SSE-уведомления, интерактивность
```

## Architecture & Data Flow

### Role-Based Access Control

Проверка роли — через `Depends(require_admin)`, `Depends(require_curator)`, `Depends(require_student)` или `Depends(require_user)`:

- Admin: `/admin/*`
- Curator: `/curator/*`
- Student: `/student/*`
- Публичное портфолио: `/portfolio/<username>` (без аутентификации)

### Аутентификация (JWT)

- JWT-токен хранится в HttpOnly cookie (`access_token`)
- 8 часов жизни, SameSite=Lax
- Расшифровка в middleware (`get_current_user_sync`) и dependency (`get_current_user`)
- Пароли: bcrypt через `passlib`

### Event (мероприятие) Lifecycle

1. **Студент отправляет** → статус `pending`
2. **Куратор проверяет**:
   - Одобрить → `approved` + проставляется балл (1..5)
   - Отклонить → `rejected` + обязательный комментарий

> Статусы `disputed` и арбитраж комиссии удалены при миграции на FastAPI.

События могут быть отнесены к категориям ОК (ОК-1…ОК-9).

### OK (Общие компетенции)

- ОК-1…ОК-9
- Студент закрывает ОК мероприятиями (мин. 3 на категорию)
- Куратор может вручную отметить выполнение через `CuratorOKOverride`
- Студент может отправить уведомление куратору при выполнении всех ОК
- Сервис: `services/ok_service.py`

### Notification System

- Уведомления всем кураторам группы при создании мероприятия студентом
- Уведомление студенту при одобрении/отклонении мероприятия
- SSE-поток: `/api/notifications/stream` (асинхронный, без блокировок)
- REST API: `/api/notifications/count` (JSON)
- Статус `is_read` / bulk mark-read

### Аудит

Все значимые действия логируются в `AuditLog`:
- Вход/выход из системы, управление пользователями
- Изменение статусов мероприятий
- Импорт студентов, создание/редактирование групп
- Используется `helpers.log_audit()` — принимает `db_session` от вызывающей стороны

## Database Models

```python
User              # id, username, password_hash, role, last_name, first_name, patronymic,
                  # group_name, group_id → Group
                  # relations: events, notifications, curated_groups (Group через curator_id)

Event             # id, student_id → User, title, description, status (pending/approved/rejected),
                  # category (OK-1…OK-9), score (1-5), curator_comment, created_at
                  # relations: files

EventFile         # id, event_id, file_path, file_type

Notification      # id, user_id, message, link, is_read, created_at

Department        # id, name, specialties

Specialty         # id, name, code, abbreviation, department_id → Department, groups

Group             # id, name, group_number, specialty_id, specialty_name, specialty_code,
                  # budget_type, start_year, course, department, form_of_study,
                  # curator_id → User, start_date, end_date

AuditLog          # id, user_id, username, action, details, ip_address, created_at

CuratorOKOverride # id, student_id, curator_id, ok_category, created_at
```

> **Удалённые модели** (были во Flask-версии): `ScholarshipRequest` — функциональность стипендиальных заявок убрана.

## Naming Conventions & Style

### Python
- Функции и переменные: `snake_case`
- Классы: `PascalCase`
- Константы: `UPPER_CASE`
- Enum-классы: `StrEnum` в `constants.py`
- Комментарии: преимущественно русские
- Type hints: активно используется (`Mapped[]`, `Optional`, `|`)

### Templates
- Jinja2 с наследованием от `base.html`
- Переменные передаются через `render()` (обёртка над `Jinja2Templates`)
- CSRF-токен доступен во всех шаблонах как `{{ csrf_token }}`
- Кастомный `url_for` (из-за отсутствия Flask)

## Security

- **Аутентификация**: JWT в HttpOnly cookie, SameSite=Lax, 8 часов
- **Пароли**: bcrypt через `passlib`
- **CSRF**: проверка для POST/PUT/DELETE, исключая `/api/notifications/stream` и `/admin/import_*`. Токен хранится в Starlette Session, сравнивается через SHA-256.
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Cache-Control: no-store` (кроме `/portfolio/`)
- **Файлы**: проверка расширения + MIME-типа (`ALLOWED_EXTENSIONS` + `ALLOWED_MIME_TYPES` в `constants.py`)
- **Session**: Starlette SessionMiddleware (HTTPonly не применим к Starlette сессиям, используется JWT cookie)

## Important Patterns & Gotchas

### File Uploads
- Путь: `./diplom/students/{username}/{event_id}_{title}/`
- Разрешены: png, jpg, jpeg, pdf
- Физические файлы **НЕ удаляются** при удалении записи из БД
- Имена: `werkzeug.utils.secure_filename()`
- Загрузка через `await f.read()` (асинхронная)

### Query Optimization
- `joinedload()` для предотвращения N+1 в dashboard-запросах
- Сессия открывается/закрывается вручную (нет Flask-SQLAlchemy автозакрытия)

### Time Handling
- Все timestamp — `datetime.now(timezone.utc).replace(tzinfo=None)`, без timezone
- Вспомогательная функция: `helpers.now_utc()`

### Database
- SQLite с WAL mode + synchronous=NORMAL (через `check_same_thread: False`)
- PostgreSQL через переменную окружения `DATABASE_URL`
- Миграции не настроены — удалить `instance/database.db` и выполнить `sql/load.py` для пересоздания

### Session & DB Lifecycle
- Сессия БД НЕ привязана к request-scope автоматически (в отличие от Flask-SQLAlchemy)
- Роуты сами открывают/закрывают `db = next(get_db())` в try/finally
- `get_db()` — FastAPI dependency, но некоторые роуты используют `SessionLocal()` напрямую

### CSRF & Jinja2 Cache (Python 3.14)
- Для совместимости Jinja2 3.1.6 + Python 3.14 используется `_NullCache` (отключает LRUCache)
- `templates.env.cache = _NullCache()`

## Deployment

### Docker Compose (рекомендуется)

```bash
docker compose up -d
```

Поднимает PostgreSQL 16 + веб-сервер (gunicorn + gevent).

### Окружение

См. `.env.example`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL или SQLite URL |
| `SECRET_KEY` | Секретный ключ для JWT и сессий |
| `FLASK_DEBUG` | `1` для debug (оставлено для совместимости) |

### Замечания

- `Dockerfile` использует `gunicorn` с gevent worker'ами
- `docker-entrypoint.sh` ждёт PostgreSQL, создаёт таблицы, опционально загружает seed
- Health-check через HTTP GET на `/`

## Development Guidelines

### Adding New Features
1. Модели в `models.py` (если нужно)
2. Бизнес-логика в `services/`
3. Маршруты в соответствующем модуле `routes/` (APIRouter)
4. Зарегистрировать роутер в `main.py`: `app.include_router(router)`
5. Шаблоны в `templates/`
6. Аудит через `helpers.log_audit(db, user, action, details)`

### Database Changes
- Правка в `models.py`
- Для прода — настроить Alembic/Flask-Migrate
- Для разработки — `rm instance/database.db && python sql/load.py`

## Troubleshooting

- **Database locked**: одна копика приложения (SQLite)
- **Missing upload dirs**: создаются автоматически, но проверить права на `./diplom/`
- **Role access denied**: сверить роль в БД с `Depends(require_*)`
- **File upload fails**: расширение или MIME-тип не в `ALLOWED_EXTENSIONS`/`ALLOWED_MIME_TYPES`
- **CSRF error**: нет `_csrf_token` в форме или заголовке `X-CSRF-Token`
- **JWT error**: кука `access_token` не установлена или просрочена
- **Jinja2 error**: проверить `_NullCache` в `utils.py`, возможны конфликты с Python 3.14

### Debugging
- `uvicorn` hot-reload в dev
- WAL mode позволяет читать БД во время работы приложения
- Логи: `/tmp/diplom_logs/app.log`
