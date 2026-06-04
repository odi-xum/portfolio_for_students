#!/usr/bin/env python3
"""
Генерация мероприятий (постов) для всех студентов с реалистичными данными
и файлами-доказательствами (сертификаты, грамоты, дипломы).
"""
import os, sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from io import BytesIO
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

from database import init_db, SessionLocal
from models import User, Event, EventFile
from constants import EventStatus
from helpers import BASE_UPLOAD_FOLDER

random.seed(42)

EVENT_TEMPLATES = [
    ('Участие в хакатоне «Цифровой прорыв»',
     'Командная разработка MVP за 48 часов. Заняли 3 место.',
     ['OK-1', 'OK-2', 'OK-3', 'OK-4']),
    ('Сертификат «Python-разработчик» на Stepik',
     'Курс 72 ак. часа. Итоговый проект — телеграм-бот.',
     ['OK-1', 'OK-4', 'OK-5']),
    ('Волонтёрская помощь на городском форуме',
     'Регистрация участников и сопровождение гостей.',
     ['OK-3', 'OK-6', 'OK-8']),
    ('Диплом участника конференции «Молодёжь и наука»',
     'Доклад «Применение нейросетей в образовании».',
     ['OK-1', 'OK-4', 'OK-7']),
    ('Победа в олимпиаде по информатике',
     '1 место в региональной олимпиаде среди СПО.',
     ['OK-1', 'OK-4']),
    ('Сертификат английского языка B1',
     'Курс 6 месяцев, 120 ак. часов.',
     ['OK-5', 'OK-6']),
    ('Турнир по волейболу',
     '2 место в межфакультетском турнире в составе сборной.',
     ['OK-3', 'OK-8']),
    ('Практика в ООО «ТехноСофт»',
     'Разработка модуля авторизации для внутреннего портала.',
     ['OK-1', 'OK-2', 'OK-4', 'OK-9']),
    ('Грамота за активную студенческую жизнь',
     'Награда от деканата за организацию мероприятий.',
     ['OK-6', 'OK-8', 'OK-9']),
    ('Курс «Web-разработчик: HTML, CSS, JS»',
     'Разработка лендинга для портфолио.',
     ['OK-1', 'OK-4']),
    ('Курс «Основы баз данных и SQL»',
     'PostgreSQL, сложные запросы, проектирование БД.',
     ['OK-1', 'OK-4', 'OK-5']),
    ('Хакатон «IT-SPRINT»',
     'Мобильное приложение для трекинга привычек. Спецприз.',
     ['OK-1', 'OK-2', 'OK-4']),
    ('Экскурсия в офис Яндекса',
     'Знакомство с корпоративной культурой IT-гиганта.',
     ['OK-2', 'OK-9']),
    ('Курс «Кибербезопасность» от Kaspersky',
     'Основы информационной безопасности.',
     ['OK-1', 'OK-4', 'OK-7']),
    ('Конкурс «Студент года»',
     'Номинация «Лучший в профессии». Диплом финалиста.',
     ['OK-6', 'OK-7', 'OK-9']),
    ('Курс «Linux для начинающих»',
     'Командная строка, настройка сервера, Docker.',
     ['OK-1', 'OK-4']),
    ('День открытых дверей',
     'Экскурсии для абитуриентов по лабораториям.',
     ['OK-3', 'OK-6', 'OK-8']),
    ('Семинар «Искусственный интеллект»',
     'Сертификат участника от преподавателей МГУ.',
     ['OK-1', 'OK-4', 'OK-7']),
    ('Курс «Основы предпринимательства»',
     'Бизнес-план для стартапа от центра «Мой бизнес».',
     ['OK-2', 'OK-5', 'OK-9']),
    ('Турнир по киберспорту CS2',
     '1 место в локальном турнире среди групп.',
     ['OK-3', 'OK-8']),
    ('Курс «Data Science: введение в ML»',
     'Pandas, sklearn, визуализация данных на Python.',
     ['OK-1', 'OK-4']),
    ('Воркшоп по 3D-моделированию в Blender',
     'Создание 3D-модели интерьера помещения.',
     ['OK-1', 'OK-4']),
    ('Экологический проект «Чистый берег»',
     'Уборка мусора на берегу реки.',
     ['OK-3', 'OK-8']),
    ('Курс «Git и GitHub»',
     'Системы контроля версий, командная разработка.',
     ['OK-1', 'OK-2', 'OK-4']),
    ('Стажировка в Яндекс.Практикум',
     'Разработка образовательных продуктов. Сертификат.',
     ['OK-1', 'OK-2', 'OK-4', 'OK-9']),
]


def _make_certificate(title, student_name):
    w, h = 800, 600
    img = Image.new('RGB', (w, h), (random.randint(30,60), random.randint(30,60), random.randint(50,80)))
    draw = ImageDraw.Draw(img)
    b = 30
    draw.rectangle([b, b, w-b, h-b], outline=(220, 180, 100), width=4)
    draw.rectangle([b+10, b+10, w-b-10, h-b-10], outline=(200, 160, 80), width=1)
    try:
        ft = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
        fi = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    except Exception:
        ft = fb = fi = ImageFont.load_default()
    draw.text((w//2, 80), 'СЕРТИФИКАТ', fill=(220, 180, 100), font=ft, anchor='mt')
    draw.text((w//2, 150), student_name, fill=(255,255,255), font=fb, anchor='mt')
    draw.text((w//2, 230), title[:60], fill=(200,200,200), font=fi, anchor='mt')
    draw.line([w//4, h-120, 3*w//4, h-120], fill=(200,160,80), width=1)
    draw.text((w//2, h-90), 'подпись _______________', fill=(150,150,150), font=fi, anchor='mt')
    draw.text((w//2, h-50), datetime.now().strftime('%d.%m.%Y'), fill=(150,150,150), font=fi, anchor='mt')
    buf = BytesIO(); img.save(buf, format='PNG'); return buf.getvalue()


def _make_photo(title):
    w, h = 640, 480
    img = Image.new('RGB', (w, h), (random.randint(60,200), random.randint(60,200), random.randint(60,200)))
    draw = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
    except Exception:
        f = ImageFont.load_default()
    for _ in range(random.randint(3, 8)):
        x1 = random.randint(50, w-100); y1 = random.randint(50, h-100)
        x2 = x1 + random.randint(40, 200); y2 = y1 + random.randint(40, 200)
        c = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
        if random.choice([True, False]):
            draw.ellipse([x1,y1,x2,y2], fill=c, outline=(255,255,255), width=2)
        else:
            draw.rectangle([x1,y1,x2,y2], fill=c, outline=(255,255,255), width=2)
    draw.text((w//2, h-40), title[:40], fill=(255,255,255), font=f, anchor='mb')
    buf = BytesIO(); img.save(buf, format='PNG'); return buf.getvalue()


def _make_pdf(title, student_name):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page(); pdf.set_auto_page_break(auto=False)
    pdf.set_draw_color(180, 140, 60); pdf.set_line_width(2)
    pdf.rect(10, 10, 190, 277); pdf.set_line_width(0.5); pdf.rect(14, 14, 182, 269)
    pdf.set_font('Helvetica', 'B', 28); pdf.set_text_color(180, 140, 60)
    pdf.cell(0, 40, 'DIPLOMA', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', '', 18); pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 20, student_name, new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', 'I', 14); pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 15, f'for completing:', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.cell(0, 15, title[:60], new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', '', 12); pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 40, f'Date: {datetime.now().strftime("%d.%m.%Y")}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.cell(0, 10, 'Signature: _______________', new_x='LMARGIN', new_y='NEXT', align='C')
    return pdf.output()


def seed_events():
    init_db()
    db = SessionLocal()
    try:
        students = db.query(User).filter(User.role == 'student').all()
        if not students:
            print('Нет студентов. Сначала: python sql/load.py'); return
        random.shuffle(students)
        total_events = 0

        for idx, student in enumerate(students):
            num_events = random.randint(3, 8)
            selected = random.sample(EVENT_TEMPLATES, min(num_events, len(EVENT_TEMPLATES)))
            for title, desc, cats in selected:
                cat = random.choice(cats)
                r = random.random()
                if r < 0.15: status = EventStatus.REJECTED; score = None
                elif r < 0.25: status = EventStatus.PENDING; score = None
                else: status = EventStatus.APPROVED; score = random.randint(3, 5)
                created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                    days=random.randint(1, 365), hours=random.randint(0, 23))
                event = Event(student_id=student.id, title=title, description=desc,
                              category=cat, status=status, score=score, created_at=created_at)
                db.add(event); db.flush()
                safe_user = student.username.replace('/', '_')
                safe_t = title.replace('/', '_').replace(' ', '_')[:40]
                event_dir = os.path.join(BASE_UPLOAD_FOLDER, 'students', safe_user, f'{event.id}_{safe_t}')
                os.makedirs(event_dir, exist_ok=True)
                num_files = random.randint(1, 2)
                sname = f"{student.last_name or ''} {student.first_name or ''}".strip() or student.username
                for fi in range(num_files):
                    if fi == 0:
                        data = _make_certificate(title, sname)
                        fname = f'cert_{event.id}_{fi}.png'; ftype = 'png'
                    else:
                        data = _make_photo(title)
                        fname = f'photo_{event.id}_{fi}.png'; ftype = 'png'
                    with open(os.path.join(event_dir, fname), 'wb') as f: f.write(data)
                    db.add(EventFile(event_id=event.id, file_path=os.path.join(event_dir, fname), file_type=ftype))
                total_events += 1
                if total_events % 30 == 0: db.commit()

        db.commit()
        print(f'✅ Создано {total_events} мероприятий для {len(students)} студентов')
        print(f'   Одобрено: {db.query(Event).filter(Event.status == "approved").count()}')
        print(f'   На проверке: {db.query(Event).filter(Event.status == "pending").count()}')
        print(f'   Отклонено: {db.query(Event).filter(Event.status == "rejected").count()}')
        print(f'   Файлов: {db.query(EventFile).count()}')
    finally:
        db.close()


if __name__ == '__main__':
    seed_events()
