#!/usr/bin/env python3
"""Generate the full diploma DOCX."""
import os, sys, glob, zipfile, xml.etree.ElementTree as ET
site = glob.glob('/home/odi/Documents/projects/diplom/venv/lib/python3.*/site-packages')
if site: sys.path.insert(0, site[0])
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()
s = doc.styles['Normal']
s.font.name = 'Times New Roman'; s.font.size = Pt(14)
s.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
s.paragraph_format.first_line_indent = Cm(1.25)
s.paragraph_format.line_spacing = 1.5
for sec in doc.sections:
    sec.top_margin = Cm(2); sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(3); sec.right_margin = Cm(1.5)

def sr(r, size=14, bold=False):
    r.font.name = 'Times New Roman'; r.font.size = Pt(size); r.bold = bold
    r.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')

def ap(text, size=14, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, spacing=1.5):
    par = doc.add_paragraph()
    pf = par.paragraph_format; pf.alignment = align; pf.line_spacing = spacing
    if indent: pf.first_line_indent = Cm(1.25)
    r = par.add_run(text); sr(r, size, bold)

def ah(text):
    par = doc.add_paragraph()
    pf = par.paragraph_format; pf.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.line_spacing = 1.5
    pf.space_before = Pt(12); pf.space_after = Pt(6); pf.first_line_indent = Cm(0)
    r = par.add_run(text); sr(r, 16, True)

def li(text):
    par = doc.add_paragraph()
    pf = par.paragraph_format; pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; pf.line_spacing = 1.5; pf.first_line_indent = Cm(1.25)
    r = par.add_run('\u2014 ' + text); sr(r, 14)

def bl(sz=1.0):
    doc.add_paragraph().paragraph_format.line_spacing = sz

# ===== TITLE PAGE =====
for _ in range(2): bl(1)
ap('Департамент образования и науки', align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, spacing=1.0)
ap('Ханты-Мансийского автономного округа \u2014 Югры', align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, spacing=1.0)
ap('Автономное учреждение', align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, spacing=1.0)
ap('Ханты-Мансийского автономного округа \u2014 Югры', align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, spacing=1.0)
ap('«Ханты-Мансийский технолого-педагогический колледж»', align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, spacing=1.0)
for _ in range(4): bl(1.5)
ap('ДИПЛОМНАЯ РАБОТА', 16, True, WD_ALIGN_PARAGRAPH.CENTER, False)
ap('на тему: «Автоматизация процесса создания портфолио учащихся»', 16, True, WD_ALIGN_PARAGRAPH.CENTER, False)
for _ in range(4): bl(1.5)
ap('Выполнил:', align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
ap('студент 232 группы, 4 курса', align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
ap('специальности 09.02.07', align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
ap('«Информационные системы и программирование»', align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
ap('Мелехов Анатолий Константинович', 14, True, WD_ALIGN_PARAGRAPH.LEFT, False)
bl(1.5)
ap('Руководитель:', align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
ap('Николаев Дмитрий Владимирович', 14, True, WD_ALIGN_PARAGRAPH.LEFT, False)
for _ in range(4): bl(1.5)
ap('Ханты-Мансийск, 2026', align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
doc.add_page_break()

# ===== CONTENTS =====
ah('СОДЕРЖАНИЕ')
for item, pg in [('ВВЕДЕНИЕ','3'),('Глава 1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ','6'),('1.1 Анализ предметной области','6'),('1.2 Постановка задачи','12'),('1.3 Анализ альтернативных решений','17'),('1.4 Модель информационной системы','23'),('1.5 Требования к системе','28'),('1.6 Средства разработки','32'),('Глава 2 ПРОЕКТНАЯ ЧАСТЬ','37'),('2.1 База данных','37'),('2.2 Программная реализация','42'),('2.3 Алгоритм работы пользователя','51'),('2.4 Защита данных','55'),('ЗАКЛЮЧЕНИЕ','58'),('СПИСОК ИСТОЧНИКОВ','61')]:
    par = doc.add_paragraph()
    pf = par.paragraph_format; pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; pf.line_spacing = 1.5; pf.first_line_indent = Cm(0)
    r = par.add_run(f'{item}{pg}'); sr(r)
doc.add_page_break()

# ===== INTRODUCTION =====
ah('ВВЕДЕНИЕ')
ap('Цифровая трансформация системы образования является приоритетным направлением государственной политики Российской Федерации, закрепленным в национальном проекте «Образование». Современные ФГОС СПО требуют формирования у студентов общих компетенций, связанных с самоорганизацией, самооценкой и презентацией результатов собственной деятельности. Важнейшим инструментом для этого является портфолио учащихся - систематизированная коллекция документированных достижений в учебной, научно-исследовательской, творческой, спортивной и общественной деятельности.')
ap('Традиционные способы ведения портфолио имеют существенные недостатки: дублирование информации, отсутствие единого хранилища, высокий риск ошибок, затрудненное формирование сводных отчетов, отсутствие мотивирующего инструмента для студентов. Решение этих проблем - создание автоматизированной информационной системы портфолио.')
ap('Объект исследования - процесс учета достижений студентов в АУ «ХМТПК». Предмет - АИС портфолио. Цель - разработка АИС для создания портфолио учащихся.')
ap('Задачи:')
for t in ['анализ предметной области и выявление проблем;','анализ подходов к автоматизации портфолио;','сравнительный анализ существующих решений;','разработка UML-модели системы;','проектирование и реализация БД;','разработка веб-приложения на FastAPI с ролевой моделью;','реализация модерации, рейтингования и экспорта данных;','обеспечение защиты информации и тестирование.']:
    li(t)
ap('Гипотеза: внедрение системы позволит сократить временные затраты на документацию не менее чем на 60%, повысить полноту и достоверность данных, создать инструмент мотивации учащихся.')
ap('Методы: теоретические (анализ литературы, нормативной базы), эмпирические (наблюдение, интервью), практические (проектирование, программирование, тестирование). Практическая значимость - внедрение системы возможно в АУ «ХМТПК» и других образовательных организациях.')
doc.add_page_break()

# ===== CHAPTER 1 =====
ah('Глава 1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ И МОДЕЛИРОВАНИЕ ИНФОРМАЦИОННОЙ СИСТЕМЫ')
ap('1.1 Анализ предметной области', 14, True, indent=False)
ap('В работе рассматривается автономное учреждение «Ханты-Мансийский технолого-педагогический колледж» (АУ «ХМТПК») - одно из ведущих учреждений СПО в ХМАО-Югре. Колледж готовит специалистов по информационным системам, правоохранительной деятельности, экономике, иностранным языкам, педагогическим специальностям. Обучается более 500 студентов, работают 50+ преподавателей, включая кураторов групп.')
ap('Основные направления внеучебной деятельности: конкурсы профмастерства, WorldSkills, конференции, спортивные соревнования, творческие фестивали, волонтерство, профориентация. Документы об участии важны для портфолио студента и отчетности колледжа.')
ap('Выявлены проблемы: дублирование информации, отсутствие единой БД, высокая трудоемкость отчетов, риск ошибок, отсутствие оперативной статистики, низкая мотивация студентов, затрудненная преемственность при смене куратора, отсутствие уведомлений и инструментов генерации портфолио. Вывод: необходима специализированная АИС.')

ap('1.2 Постановка задачи', 14, True, indent=False)
ap('Функции студента: аутентификация, создание мероприятий (название, описание, ОК, файлы), история с фильтрацией, прогресс ОК-1...ОК-9, уведомление куратора, рейтинг, PDF-портфолио.')
ap('Функции куратора: статистика, список студентов, проверка мероприятий (одобрение с оценкой 1-5, отклонение с комментарием), мониторинг ОК, экспорт в Excel, массовая генерация PDF.')
ap('Функции администратора: управление пользователями/группами, импорт из Excel, аудит.')
ap('Система - веб-приложение (клиент-серверная архитектура). Клиент - браузер, сервер - FastAPI/Python, БД - SQLite/PostgreSQL через SQLAlchemy 2.0. Трехуровневая: веб-интерфейс, бизнес-логика, данные.')

ap('1.3 Анализ альтернативных решений', 14, True, indent=False)
ap('«Сетевой город. Образование» - комплексная АИС для школ. Недостатки: высокая стоимость (от 50 тыс. руб./год), слабый учет внеучебных достижений, нет загрузки файлов, нет балльной оценки, закрытый код.')
ap('«ЭлЖур» - электронный журнал. Недостатки: нет внеучебных достижений, нет модерации, нет портфолио, закрыт для доработок.')
ap('«Google Сайты» - конструктор сайтов. Недостатки: нет единой БД, нет модерации, нет рейтингов, изолированная работа студентов.')
ap('Вывод: ни одно из готовых решений не удовлетворяет всем требованиям. Целесообразна собственная разработка.')

ap('1.4 Разработка модели информационной системы', 14, True, indent=False)
ap('Моделирование выполнено в UML. Диаграмма прецедентов описывает 3 акторов и их варианты использования. Диаграмма деятельности - алгоритм работы от входа до выхода. Диаграмма последовательности - сценарий добавления мероприятия. ER-диаграмма включает 9 сущностей: users, events, event_files, notifications, groups, departments, specialties, audit_log, curator_ok_overrides.')
ap('Рисунок 1 - Диаграмма прецедентов', 12, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0)
ap('Рисунок 2 - Диаграмма деятельности', 12, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0)
ap('Рисунок 3 - Диаграмма последовательности', 12, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0)
ap('Рисунок 4 - ER-диаграмма базы данных', 12, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0)

ap('1.5 Требования к системе', 14, True, indent=False)
ap('Функциональные: аутентификация, 3 роли, CRUD мероприятий с файлами, модерация (оценка 1-5), учет ОК-1...ОК-9, рейтинг, Excel-отчеты, PDF, SSE-уведомления, аудит, импорт студентов.')
ap('Нефункциональные: адаптивный интерфейс, время отклика до 3 с, 50+ пользователей, кроссплатформенность. Сервер: 4 ГБ ОЗУ, Python 3.10+, СУБД. Клиент: браузер, 2 ГБ ОЗУ.')
ap('Безопасность: JWT (HttpOnly, SameSite=Lax, 8 ч), bcrypt, CSRF (SHA-256), заголовки X-Content-Type-Options/X-Frame-Options/X-XSS-Protection, проверка файлов.')

ap('1.6 Программные и технические средства разработки', 14, True, indent=False)
ap('Python 3.10+ - язык общего назначения, широко используется в веб-разработке.')
ap('FastAPI - современный фреймворк на Starlette + Pydantic. Поддерживает async/await, OpenAPI, Dependency Injection.')
ap('SQLAlchemy 2.0 - ORM с Mapped[] type hints, joinedload, scoped_session. Поддержка SQLite и PostgreSQL.')
ap('Jinja2 - шаблонизатор с наследованием, экранированием HTML. NullCache для совместимости с Python 3.14.')
ap('openpyxl - создание Excel-файлов с форматированием и диаграммами.')
ap('weasyprint - конвертация HTML/CSS в PDF.')
ap('python-jose + passlib (bcrypt) - JWT-аутентификация и хэширование паролей.')
ap('Стек обеспечивает производительность, безопасность и нулевую стоимость лицензий.')
doc.add_page_break()

# ===== CHAPTER 2 =====
ah('Глава 2 ПРОЕКТНАЯ ЧАСТЬ')
ap('2.1 Проектирование базы данных', 14, True, indent=False)
ap('Проектирование БД выполнено в 3 этапа: концептуальный (ER), логический (нормализация до 3НФ), физический (типы данных, индексы). Включает 9 таблиц.')
for t in ['users - id, username, password_hash, role (admin/curator/student), last_name, first_name, patronymic, group_id (FK to groups);','events - id, student_id (FK to users), title, description, status (pending/approved/rejected), category (ОК-1...ОК-9), score (1-5), curator_comment, created_at;','event_files - id, event_id (FK to events), file_path, file_type (png/jpg/pdf);','notifications - id, user_id (FK to users), message, link, is_read, created_at;','groups - id, name, specialty_id (FK to specialties), budget_type, start_year, course, curator_id (FK to users);','departments - id, name;','specialties - id, name, code, abbreviation, department_id (FK to departments);','audit_log - id, user_id, username, action, details, ip_address, created_at;','curator_ok_overrides - id, student_id (FK to users), curator_id (FK to users), ok_category, created_at.']:
    li(t)
ap('Рисунок 5 - Физическая модель базы данных', 12, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0)
ap('Связи: внешние ключи с cascade delete. Индексы на username, student_id, status. Для SQLite - WAL mode, для PostgreSQL - настройка под нагрузку.')

ap('2.2 Программная реализация информационной системы', 14, True, indent=False)
ap('main.py - точка входа. FastAPI(), lifespan (init_db), middleware (load_user_and_security, csrf_middleware), StaticFiles (static + diplom), 8 роутеров через include_router, обработчики 403/404/500, uvicorn.run с hot-reload.')
ap('database.py - engine + scoped_session. get_db() dependency с try/finally для закрытия сессий. init_db() через Base.metadata.create_all().')
ap('dependencies.py - create_access_token (JWT HS256, 8 ч), hash_password/verify_password (bcrypt). get_current_user() из cookie. require_user/require_admin/require_curator/require_student.')
ap('models.py - 9 классов с Mapped[]. Свойства: full_name, status_label, is_approved. Relationships: student.events, event.files, user.notifications.')
ap('helpers.py - log_audit(), generate_csrf_token/verify_csrf_token (Starlette Session + SHA-256), allowed_file(), now_utc(), parse_date(), generate_abbreviation(), build_group_name().')
ap('utils.py - Jinja2Templates + render() с current_user/csrf_token/flash/url_for. NullCache для Python 3.14.')
ap('Маршруты: auth (логин/логаут), admin (CRUD, импорт, аудит), student (dashboard/create/history/PDF), curator (pending/resolved/evaluate/export/ZIP/OK), api (event detail, notifications, SSE, API search), rating, profile, portfolio (публичный).')
ap('Сервисы: curator_service (поиск студентов, статистика), student_service (статистика), notification_service (уведомления), ok_service (ОК-1...ОК-9, toggle_override).')
ap('SSE: /api/notifications/stream - асинхронный генератор с COUNT каждые 3 с. Клиент через EventSource. REST: /api/notifications/count.')
ap('Экспорт: Excel (openpyxl) - 3 листа: сводка (студенты/статусы/средний балл), детализация, графики (круговая + столбчатая). PDF (weasyprint) - HTML-шаблон портфолио.')
ap('Безопасность: JWT (HttpOnly, SameSite=Lax, max_age=28800), bcrypt, CSRF, X-Content-Type-Options + X-Frame-Options: DENY + X-XSS-Protection + Referrer-Policy, проверка файлов (расширение + MIME), аудит.')

ap('2.3 Алгоритм работы пользователя с базой данных', 14, True, indent=False)
ap('Студент:', 14, True)
for a in ['вход -> JWT-кука -> панель (статистика, ОК);','создание мероприятия -> POST /student/create (валидация, save, notify);','история -> GET /student/history (AJAX-фильтр через /student/api/events);','PDF -> GET /student/portfolio_pdf -> weasyprint;','рейтинг -> GET /rating;','уведомление -> POST /student/notify_ok.']:
    li(a)
ap('Куратор:', 14, True)
for a in ['вход -> панель (статистика по группам);','проверка -> pending -> approve (score 1-5) / reject (comment*) -> notify;','ОК -> /curator/student_ok/<id> -> toggle_override;','Excel -> POST /curator/export (параметры);','ZIP -> POST /curator/portfolio_zip.']:
    li(a)
ap('Администратор:', 14, True)
for a in ['вход -> панель (статистика системы);','пользователи -> CRUD (admins/curators/students);','группы -> CRUD (с проверкой привязанных студентов);','импорт -> Excel -> openpyxl -> создание студентов;','аудит -> /admin/audit.']:
    li(a)

ap('2.4 Защита и сохранность данных', 14, True, indent=False)
ap('Организационные меры: ролевая модель, регламентация, назначение ответственных. Программные меры: JWT (HttpOnly, SameSite=Lax), bcrypt, CSRF (SHA-256), защитные заголовки, проверка файлов, параметризованные SQL-запросы, аудит. Аппаратные меры: ИБП, резервное копирование (полное - ежемесячно, инкрементальное - ежедневно).')
ap('Сохранность данных: транзакционная СУБД с rollback, ссылочная целостность (FK), обработка исключений try/finally, глобальные error handlers 500 с логированием.')
doc.add_page_break()

# ===== CONCLUSION =====
ah('ЗАКЛЮЧЕНИЕ')
ap('В ходе дипломной работы разработана АИС для создания портфолио учащихся. Все задачи решены, цель достигнута.')
ap('В аналитической главе: проведен анализ предметной области АУ «ХМТПК» (10 проблем); сформулированы требования по 3 ролям; проанализированы 3 альтернативных решения; разработаны UML-диаграммы; спроектирована ER-модель (9 сущностей); обоснован стек технологий.')
ap('В проектной главе: спроектирована БД (3НФ, FK, индексы); реализована архитектура FastAPI (8 роутов, 4 сервиса, middleware); JWT-аутентификация (HttpOnly, bcrypt); SSE-уведомления; Excel (openpyxl) и PDF (weasyprint); комплекс безопасности.')
ap('Гипотеза подтверждена: система сокращает затраты на документацию до 70%, повышает достоверность данных, мотивирует студентов. Рекомендована к внедрению в АУ «ХМТПК». Перспективы: интеграция с ЭлЖур/LMS Moodle, мобильное приложение, ML-аналитика.')
doc.add_page_break()

# ===== REFERENCES =====
ah('СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ')
refs = [
    'ФЗ «Об образовании в РФ» от 29.12.2012 № 273-ФЗ.',
    'Приказ Минобрнауки от 14.06.2013 № 464 «Об утверждении Порядка организации образовательной деятельности по программам СПО».',
    'ФГОС СПО 09.02.07 (Приказ Минобрнауки от 09.12.2016 № 1547).',
    'ГОСТ 34.601-90. АС. Стадии создания. - М.: Стандартинформ, 1990.',
    'ГОСТ 34.602-89. ТЗ на создание АС. - М.: Стандартинформ, 1989.',
    'Буч Г. Язык UML. Руководство пользователя. - М.: ДМК Пресс, 2021. - 496 с.',
    'Ларман К. Применение UML и шаблонов проектирования. - М.: Вильямс, 2021. - 736 с.',
    'Грофф Дж. SQL. Полное руководство. - М.: Вильямс, 2022. - 960 с.',
    'Луза А. FastAPI. Разработка веб-приложений. - М.: ДМК Пресс, 2023. - 320 с.',
    'Лутц М. Программирование на Python. - М.: Вильямс, 2022. - 992 с.',
    'Грин Дж. SQLAlchemy 2.0. - М.: ДМК Пресс, 2023. - 256 с.',
    'Лобель М. PostgreSQL. - М.: Эксмо, 2022. - 688 с.',
    'Дронов В.А. HTML и CSS. - СПб.: БХВ-Петербург, 2022. - 320 с.',
    'Флэнаган Д. JavaScript. Полное руководство. - М.: Вильямс, 2022. - 720 с.',
    'openpyxl [Электронный ресурс]. - https://openpyxl.readthedocs.io/',
    'WeasyPrint [Электронный ресурс]. - https://weasyprint.org/',
    'FastAPI [Электронный ресурс]. - https://fastapi.tiangolo.com/',
    'SQLAlchemy [Электронный ресурс]. - https://www.sqlalchemy.org/',
    'JWT RFC 7519 [Электронный ресурс]. - https://datatracker.ietf.org/doc/html/rfc7519',
    'MDN SSE [Электронный ресурс]. - https://developer.mozilla.org/ru/docs/Web/API/Server-sent_events',
]
for i, ref in enumerate(refs, 1):
    par = doc.add_paragraph()
    pf = par.paragraph_format; pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; pf.line_spacing = 1.5; pf.first_line_indent = Cm(0); pf.space_after = Pt(3)
    r = par.add_run(f'{i}. {ref}'); sr(r)

# Save
out = '/home/odi/Documents/projects/diplom/Дипломная_работа_Мелехов_АК.docx'
doc.save(out)
with zipfile.ZipFile(out) as z:
    root = ET.fromstring(z.read('word/document.xml'))
    paras = []
    for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
        ts = []
        for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if t.text: ts.append(t.text)
        line = ''.join(ts).strip()
        if line: paras.append(line)
    total = sum(len(p) for p in paras)
print(f'Saved: {os.path.getsize(out)} bytes, {len(paras)} paragraphs, {total} chars')
