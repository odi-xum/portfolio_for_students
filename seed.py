"""
Инициализация тестовой базы данных (seed-данные).
Вызывается при первом запуске приложения.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash
from models import db, User, Event, EventFile, Notification, ScholarshipRequest, Group, Specialty, Department
from helpers import now_utc, ensure_upload_dir


def init_test_db(app):
    """Наполняет БД тестовыми данными при первом запуске."""
    with app.app_context():
        ensure_upload_dir()
        db.create_all()

        if User.query.filter_by(username='admin').first():
            return  # Уже инициализировано

        # ======================================================================
        # ОТДЕЛЕНИЯ И СПЕЦИАЛЬНОСТИ
        # ======================================================================
        dept_it = Department(name='ИТ-отделение')
        dept_econ = Department(name='Экономическое отделение')
        dept_mash = Department(name='Машиностроительное отделение')
        db.session.add_all([dept_it, dept_econ, dept_mash])
        db.session.commit()

        specialties = [
            Specialty(name='Информационные системы и программирование',
                      code='09.02.07', abbreviation='ИСП', department_id=dept_it.id),
            Specialty(name='Сетевое и системное администрирование',
                      code='09.02.06', abbreviation='ССА', department_id=dept_it.id),
            Specialty(name='Прикладная информатика (по отраслям)',
                      code='09.02.05', abbreviation='ПИ', department_id=dept_it.id),
            Specialty(name='Экономика и бухгалтерский учет (по отраслям)',
                      code='38.02.01', abbreviation='ЭБУ', department_id=dept_econ.id),
            Specialty(name='Операционная деятельность в логистике',
                      code='38.02.03', abbreviation='ОДЛ', department_id=dept_econ.id),
            Specialty(name='Коммерция (по отраслям)',
                      code='38.02.04', abbreviation='КМ', department_id=dept_econ.id),
            Specialty(name='Технология машиностроения',
                      code='15.02.08', abbreviation='ТМ', department_id=dept_mash.id),
            Specialty(name='Оснащение средствами автоматизации технологических процессов и производств',
                      code='15.02.14', abbreviation='ОСА', department_id=dept_mash.id),
        ]
        db.session.add_all(specialties)
        db.session.commit()

        specialty_isp = specialties[0]

        test_group = Group(
            name='ИСП-Б-2022',
            group_number='232',
            specialty_id=specialty_isp.id,
            specialty_name='Информационные системы и программирование',
            specialty_code='09.02.07',
            budget_type='бюджет',
            start_year=2022,
            course=4,
            department='ИТ-отделение',
            form_of_study='очная',
            start_date=datetime.strptime('2022-09-01', '%Y-%m-%d').date(),
            end_date=datetime.strptime('2026-06-30', '%Y-%m-%d').date()
        )
        db.session.add(test_group)
        db.session.commit()

        # ======================================================================
        # ПОЛЬЗОВАТЕЛИ
        # ======================================================================
        roles_config = [
            {'username': 'admin', 'role': 'admin', 'group': None,
             'last': 'Администраторов', 'first': 'Админ', 'patr': 'Админович'},
            {'username': 'student', 'role': 'student', 'group': 'ИСП-Б-2022',
             'last': 'Студентов', 'first': 'Студент', 'patr': 'Студентович'},
            {'username': 'curator', 'role': 'curator', 'group': 'ИСП-Б-2022',
             'last': 'Кураторова', 'first': 'Куратория', 'patr': 'Кураторовна'},
            {'username': 'commission', 'role': 'commission', 'group': None,
             'last': 'Комиссарова', 'first': 'Комиссия', 'patr': 'Комиссионна'},
            {'username': 'ivanov', 'role': 'student', 'group': 'ИСП-Б-2022',
             'last': 'Иванов', 'first': 'Иван', 'patr': 'Иванович'}
        ]
        users_map = {}
        for user_data in roles_config:
            group_id = test_group.id if user_data['group'] else None
            u = User(
                username=user_data['username'],
                password_hash=generate_password_hash('111'),
                role=user_data['role'],
                last_name=user_data.get('last'),
                first_name=user_data.get('first'),
                patronymic=user_data.get('patr'),
                group_name=user_data['group'],
                group_id=group_id
            )
            db.session.add(u)
            users_map[user_data['username']] = u
        db.session.commit()

        curator_user = users_map['curator']
        test_group.curator_id = curator_user.id
        db.session.commit()

        student = users_map['student']
        ivanov = users_map['ivanov']

        # ======================================================================
        # 20 ОДОБРЕННЫХ ПОСТОВ ДЛЯ СТИПЕНДИИ
        # ======================================================================
        for i in range(1, 21):
            ev = Event(
                student_id=student.id,
                title=f"Олимпиада/Мероприятие №{i}",
                description=f"Автоматически сгенерированное описание подтвержденного достижения №{i} для тестирования лимитов стипендии.",
                status='approved', score=5,
                curator_comment="Документы проверены, балл начислен.",
                created_at=now_utc()
            )
            db.session.add(ev)
            db.session.commit()
            db.session.add(EventFile(
                event_id=ev.id,
                file_path=f"{ensure_upload_dir()}/students/student/mock_cert_{i}.pdf",
                file_type="pdf"
            ))

        # ======================================================================
        # ДОПОЛНИТЕЛЬНЫЕ ТЕСТОВЫЕ ДАННЫЕ
        # ======================================================================

        # 5 новых постов на проверку (pending)
        for i in range(1, 6):
            ev = Event(
                student_id=ivanov.id,
                title=f"Новая заявка на проверку №{i}",
                description=f"Студент Иванов отправил этот пост на верификацию. Куратор должен его обработать.",
                status='pending', created_at=now_utc()
            )
            db.session.add(ev)
            db.session.commit()
            db.session.add(EventFile(
                event_id=ev.id,
                file_path=f"students/ivanov/pending_proof_{i}.jpg",
                file_type="jpg"
            ))

        # 5 спорных постов (disputed)
        for i in range(1, 6):
            ev = Event(
                student_id=ivanov.id,
                title=f"Спорная публикация №{i}",
                description=f"Описание достижения, которое вызвало сомнения у куратора.",
                status='disputed',
                curator_comment=f"Нечитаемый скан документа или некорректная дата в заявке №{i}.",
                created_at=now_utc()
            )
            db.session.add(ev)
            db.session.commit()
            db.session.add(EventFile(
                event_id=ev.id,
                file_path=f"students/ivanov/disputed_proof_{i}.png",
                file_type="png"
            ))

        # 3 архивных поста (resolved)
        for i in range(1, 4):
            db.session.add(Event(
                student_id=student.id,
                title=f"Архивный арбитраж №{i}",
                description="Старая запись, по которой комиссия уже вынесла окончательный вердикт.",
                status='rejected',
                curator_comment="Отклонено куратором за несоответствие профилю.",
                commission_comment=f"Комиссия подтверждает решение куратора. Протокол №{i}.",
                created_at=now_utc(),
                commission_reviewed_at=now_utc()
            ))

        # Заявки на стипендию
        db.session.add(ScholarshipRequest(
            student_id=student.id,
            status='under_curator_review',
            created_at=now_utc()
        ))
        for i in range(1, 4):
            db.session.add(ScholarshipRequest(
                student_id=ivanov.id,
                status='approved' if i % 2 == 0 else 'rejected',
                created_at=now_utc(),
                commission_reviewed_at=now_utc()
            ))

        db.session.commit()
