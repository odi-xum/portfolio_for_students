# AGENTS.md — Руководство по работе с репозиторием Diplom

## Project Overview

Flask-приложение для управления портфолио достижений студентов и заявками на стипендию. Четыре роли:

- **admin** — управление пользователями, группами, специальностями, импорт студентов
- **student** — создание мероприятий, загрузка файлов, запрос стипендии, просмотр портфолио
- **curator** — проверка мероприятий, отметка ОК, просмотр рейтинга, экспорт отчётов
- **commission** — арбитраж спорных мероприятий, принятие решений по стипендиям

## Essential Commands

### Запуск

```bash
source venv/bin/activate
python app.py
```
По умолчанию — `http://localhost:5000`, debug mode.

### Инициализация БД

```bash
python sql/load.py
```
Таблицы создаются автоматически при первом запуске `app.py`.

### Тестовые пользователи (пароль: `111`)

| Login | Role | Group |
|-------|------|-------|
| `admin` | admin | — |
| `commission` | commission | — |
| `cur1` | curator | ИСП-Б-2022 |
| `student1` | student | ИСП-Б-2022 |
| `student2` | student | ИСП-Б-2022 |
| `student3` | student | ИСП-Б-2022 |

Всего 50 студентов, 7 кураторов, 8 групп, 3 отделения, 8 специальностей.

### Вспомогательные скрипты

```bash
python check_db.py        # просмотр содержимого БД
python sql/load.py        # загрузка seed-данных
```

## Code Organization

### Архитектура: Application Factory

`app.py` создаёт приложение через `create_app()`:

```
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=...)
```

- `create_app()` в `app.py` — настройка Flask, БД, LoginManager, CSRF, security headers
- Маршруты регистрируются через `register_routes(app)` из `routes/__init__.py`
- WAL mode + NORMAL sync для SQLite (конкурентное чтение/запись)

### Core Files

- **`app.py`** — точка входа, фабрика приложения, CSRF-защита, security-заголовки, обработчики ошибок
- **`constants.py`** — StrEnum-классы (`UserRole`, `EventStatus`, `ScholarshipStatus`), лимиты стипендии, MIME-типы
- **`models.py`** — SQLAlchemy модели (User, Event, EventFile, Notification, Group, Department, Specialty, ScholarshipRequest, AuditLog, CuratorOKOverride)
- **`helpers.py`** — CSRF-токены, аудит-лог, загрузка файлов, работа с датами, генерация названий групп
- **`routes/`** — модульные группы маршрутов
- **`services/`** — слой бизнес-логики
- **`export.py`** — генерация Excel-отчётов с графиками (openpyxl)
- **`pdf_export.py`** — генерация PDF-портфолио (weasyprint)
- **`excel_import.py`** — импорт студентов из .xlsx
- **`check_db.py`** — просмотр БД (отделения, специальности, группы, пользователи)

### Routes (`routes/`)

| Module | Routes | Role |
|--------|--------|------|
| `auth.py` | `/` (login), `/logout` | Все |
| `admin.py` | `/admin/dashboard`, `/admin/users`, `/admin/groups`, `/admin/group/<id>`, `/admin/users/create`, `/admin/import_students`, `/admin/audit` | admin |
| `student.py` | `/student/dashboard`, `/student/create`, `/student/history`, `/student/request_scholarship`, `/student/download_portfolio` | student |
| `curator.py` | `/curator/dashboard`, `/curator/pending`, `/curator/resolved`, `/curator/student/<id>`, `/curator/export`, `/curator/student/<id>/ok` | curator |
| `commission.py` | `/commission/dashboard`, `/commission/disputes`, `/commission/scholarships`, `/commission/archive`, `/commission/export` | commission |
| `api.py` | `/event/<id>`, `/diplom/<path>`, `/notifications`, `/api/notifications/stream` (SSE) | Все |
| `rating.py` | `/rating` | student, curator |
| `profile.py` | `/profile` (изменение ФИО, пароля) | Все |
| `portfolio.py` | `/portfolio/<username>` (публичное, без аутентификации) | Все |

### Services (`services/`)

| Service | Role |
|---------|------|
| `curator_service.py` | Поиск студентов куратора, агрегация статистики по группам |
| `student_service.py` | Статистика мероприятий студента, проверка eligibility стипендии |
| `notification_service.py` | Создание уведомлений для одного/всех кураторов/всей комиссии |
| `ok_service.py` | Статистика по общим компетенциям (ОК-1…ОК-9), отметки куратора |

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
├── commission.html            # Панель комиссии
├── commission_disputes.html   # Спорные мероприятия
├── commission_scholarships.html # Заявки на стипендию
├── commission_archive.html    # Архив решённых
├── commission_export.html     # Экспорт
├── event_detail.html          # Детали мероприятия + файлы
├── portfolio.html             # Публичное портфолио / PDF
├── profile.html               # Профиль / смена пароля
├── rating.html                # Рейтинг студентов
├── notifications.html         # Уведомления
├── 403.html / 404.html / 500.html  # Страницы ошибок
```

## Architecture & Data Flow

### Role-Based Access Control

Проверка роли — на каждом маршруте через `current_user.role` или хелперы `User.is_admin()`, `User.is_student()` и т.д.:

- Admin: `/admin/*`
- Curator: `/curator/*`
- Commission: `/commission/*`
- Student: `/student/*`
- Публичное портфолио: `/portfolio/<username>` (без аутентификации)

### Event (мероприятие) Lifecycle

1. **Студент отправляет** → статус `pending`
2. **Куратор проверяет**:
   - Одобрить → `approved` + проставляется балл (1..5)
   - Отклонить → `disputed`, отправляется в комиссию
3. **Комиссия арбитраж** (для `disputed`):
   - Подтвердить отклонение → `rejected`
   - Отменить → `approved`, проставляется балл
   - Пересмотреть → статус сбрасывается в `pending` (через `previous_status`)

События могут быть отнесены к категориям ОК (ОК-1…ОК-9).

### Scholarship Request Flow

1. Студент подаёт заявку (требуется ≥20 одобренных мероприятий, средний балл ≥4.5)
2. Куратор проверяет → `under_curator_review` → `under_commission_review`
3. Комиссия решает → `approved` или `rejected`

### Notification System

- Уведомления всем кураторам группы при создании мероприятия студентом
- Всем членам комиссии — при отклонении мероприятия куратором
- SSE-поток: `/api/notifications/stream`
- Статус `is_read` / `is_unread`

### OK (Общие компетенции)

- ОК-1…ОК-9
- Студент закрывает ОК мероприятиями (мин. 3 на категорию)
- Куратор может вручную отметить выполнение через `CuratorOKOverride`
- Сервис: `services/ok_service.py`

### Аудит

Все значимые действия логируются в `AuditLog`:
- Вход в систему, управление пользователями
- Изменение статусов мероприятий и стипендий
- Импорт студентов
- Используется `helpers.log_audit()`

## Database Models

```python
User              # id, username, password_hash, role, last_name, first_name, patronymic,
                  # group_name, group_id → Group, events, notifications, scholarship_requests,
                  # curated_groups (Group через curator_id)

Event             # id, student_id → User, title, description, status, previous_status,
                  # category (OK-1…OK-9), score (1-5), curator_comment, commission_comment,
                  # created_at, commission_reviewed_at, files

EventFile         # id, event_id, file_path, file_type

Notification      # id, user_id, message, link, is_read, created_at

ScholarshipRequest # id, student_id, status (under_curator_review / under_commission_review /
                   # approved / rejected), created_at, commission_reviewed_at

Department        # id, name, specialties

Specialty         # id, name, code, abbreviation, department_id → Department, groups

Group             # id, name, group_number, specialty_id, specialty_name, specialty_code,
                  # budget_type, start_year, course, department, form_of_study,
                  # curator_id → User, start_date, end_date

AuditLog          # id, user_id, username, action, details, ip_address, created_at

CuratorOKOverride # id, student_id, curator_id, ok_category, created_at
```

## Naming Conventions & Style

### Python
- Функции и переменные: `snake_case`
- Классы: `PascalCase`
- Константы: `UPPER_CASE`
- Enum-классы: `StrEnum` в `constants.py`
- Комментарии: преимущественно русские

### Templates
- Jinja2 с наследованием от `base.html`
- Переменные передаются явно в `render_template()`
- CSRF-токен доступен во всех шаблонах как `{{ csrf_token }}`

## Security

- **CSRF**: проверка для POST/PUT/DELETE, исключая `/api/notifications/stream` и `/admin/import_*`. Токен хранится в сессии, сравнивается через SHA-256.
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Cache-Control: no-store`
- **Пароли**: Werkzeug `generate_password_hash` (scrypt)
- **Файлы**: проверка расширения + MIME-типа (`ALLOWED_EXTENSIONS` + `ALLOWED_MIME_TYPES` в `constants.py`)
- **Session**: HttpOnly, SameSite=Lax, 8 часов жизни
- `SECRET_KEY` из переменной окружения или захардкожен для разработки

## Important Patterns & Gotchas

### File Uploads
- Путь: `./diplom/students/{username}/{event_id}_{title}/`
- Разрешены: png, jpg, jpeg, pdf
- Физические файлы **НЕ удаляются** при удалении записи из БД
- Имена: `secure_filename()`

### Query Optimization
- `joinedload()` для предотвращения N+1 в dashboard-запросах

### Time Handling
- Все timestamp — `datetime.utcnow()`, без timezone

### Database
- SQLite с WAL mode + synchronous=NORMAL
- Миграции не настроены — удалить `instance/database.db` и выполнить `sql/load.py` для пересоздания

### Model Relationships
- Student → Event: 1:N, cascade delete
- Student → ScholarshipRequest: 1:N
- Student → Notification: 1:N
- Group → User.students: через `group_id`
- Group → User.curator: через `curator_id`
- Specialty → Department: N:1
- Group → Specialty: N:1

## Development Guidelines

### Adding New Features
1. Модели в `models.py` (если нужно)
2. Бизнес-логика в `services/`
3. Маршруты в соответствующем модуле `routes/`
4. Шаблоны в `templates/`
5. Аудит через `helpers.log_audit()`

### Database Changes
- Правка в `models.py`
- Для прода — настроить Flask-Migrate
- Для разработки — `rm instance/database.db && python sql/load.py`

## Troubleshooting

- **Database locked**: одна копия Flask
- **Missing upload dirs**: создаются автоматически, но проверить права
- **Role access denied**: сверить роль в БД с ожиданиями маршрута
- **File upload fails**: расширение или MIME-тип не в `ALLOWED_EXTENSIONS`/`ALLOWED_MIME_TYPES`
- **CSRF error**: нет `_csrf_token` в форме или заголовке `X-CSRF-Token`

### Debugging
- `debug=True` в dev
- WAL mode позволяет читать БД во время работы приложения

## Deployment
- Сменить `SECRET_KEY`
- WSGI-сервер (Gunicorn, uWSGI)
- PostgreSQL/MySQL вместо SQLite
- Логирование и мониторинг
- HTTPS, rate limiting
- `FLASK_DEBUG=0` в окружении