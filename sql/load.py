#!/usr/bin/env python3
"""
Загрузка seed-данных в БД.
Запуск: python sql/load.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, SessionLocal
from dependencies import hash_password
from models import Department, Specialty, Group, User, Event, EventFile, Notification


def load_data():
    init_db()
    db = SessionLocal()
    try:
        # Уже есть данные?
        if db.query(User).count() > 0:
            print('⚠️  В БД уже есть данные. Очистите instance/database.db для перезагрузки.')
            return

        # ── Отделения ──────────────────────────────────────────────────
        dept_it = Department(name='Информационные технологии')
        dept_ino = Department(name='Иностранных языков')
        dept_economic = Department(name='Экономики и права')
        db.add_all([dept_it, dept_ino, dept_economic])
        db.flush()

        # ── Специальности ──────────────────────────────────────────────
        spec_is = Specialty(name='Информационные системы и программирование',
                            code='09.02.07', abbreviation='ИСП', department_id=dept_it.id)
        spec_iks = Specialty(name='Информационные системы и программирование (ИКС)',
                             code='09.02.07', abbreviation='ИКС', department_id=dept_it.id)
        spec_pd = Specialty(name='Правоохранительная деятельность',
                            code='40.02.02', abbreviation='ПД', department_id=dept_economic.id)
        spec_pravo = Specialty(name='Право и организация социального обеспечения',
                               code='40.02.01', abbreviation='ПСО', department_id=dept_economic.id)
        spec_isip = Specialty(name='Информационные системы и программирование (ИСиП)',
                              code='09.02.07', abbreviation='ИСиП', department_id=dept_it.id)
        spec_ekonom = Specialty(name='Экономика и бухгалтерский учёт',
                                code='38.02.01', abbreviation='ЭБУ', department_id=dept_economic.id)
        spec_inostr = Specialty(name='Иностранные языки',
                                code='45.02.01', abbreviation='ИНО', department_id=dept_ino.id)
        spec_prik_inf = Specialty(name='Прикладная информатика',
                                  code='09.02.05', abbreviation='ПИ', department_id=dept_it.id)
        db.add_all([spec_is, spec_iks, spec_pd, spec_pravo, spec_isip, spec_ekonom, spec_inostr, spec_prik_inf])
        db.flush()

        # ── Группы ─────────────────────────────────────────────────────
        groups_data = [
            Group(name='ИСП-Б-2022', group_number='1', specialty_id=spec_is.id, specialty_name=spec_is.name,
                  specialty_code=spec_is.code, budget_type='бюджет', start_year=2022, course=3,
                  department='Информационные технологии', form_of_study='очная'),
            Group(name='ИСП-Б-2023', group_number='2', specialty_id=spec_is.id, specialty_name=spec_is.name,
                  specialty_code=spec_is.code, budget_type='бюджет', start_year=2023, course=2,
                  department='Информационные технологии', form_of_study='очная'),
            Group(name='ИСП-Б-2024', group_number='3', specialty_id=spec_is.id, specialty_name=spec_is.name,
                  specialty_code=spec_is.code, budget_type='бюджет', start_year=2024, course=1,
                  department='Информационные технологии', form_of_study='очная'),
            Group(name='ИКС-Б-2023', group_number='4', specialty_id=spec_iks.id, specialty_name=spec_iks.name,
                  specialty_code=spec_iks.code, budget_type='бюджет', start_year=2023, course=2,
                  department='Информационные технологии', form_of_study='очная'),
            Group(name='ПД-Б-2022', group_number='5', specialty_id=spec_pd.id, specialty_name=spec_pd.name,
                  specialty_code=spec_pd.code, budget_type='бюджет', start_year=2022, course=3,
                  department='Экономики и права', form_of_study='очная'),
            Group(name='ПСО-Б-2023', group_number='6', specialty_id=spec_pravo.id, specialty_name=spec_pravo.name,
                  specialty_code=spec_pravo.code, budget_type='бюджет', start_year=2023, course=2,
                  department='Экономики и права', form_of_study='очная'),
            Group(name='ИСП-К-2022', group_number='7', specialty_id=spec_is.id, specialty_name=spec_is.name,
                  specialty_code=spec_is.code, budget_type='коммерция', start_year=2022, course=3,
                  department='Информационные технологии', form_of_study='очная'),
            Group(name='ИСП-К-2023', group_number='8', specialty_id=spec_is.id, specialty_name=spec_is.name,
                  specialty_code=spec_is.code, budget_type='коммерция', start_year=2023, course=2,
                  department='Информационные технологии', form_of_study='очная'),
        ]
        db.add_all(groups_data)
        db.flush()
        groups = {g.name: g for g in groups_data}

        # ── Кураторы ────────────────────────────────────────────────────
        curators = [
            User(username='cur1', password_hash=hash_password('111'), role='curator',
                 last_name='Швецова', first_name='Наталья', patronymic='Александровна'),
            User(username='cur2', password_hash=hash_password('111'), role='curator',
                 last_name='Немчинова', first_name='Наталья', patronymic='Владимировна'),
            User(username='cur3', password_hash=hash_password('111'), role='curator',
                 last_name='Козлова', first_name='Ольга', patronymic='Владимировна'),
            User(username='cur4', password_hash=hash_password('111'), role='curator',
                 last_name='Попова', first_name='Елена', patronymic='Валерьевна'),
            User(username='cur5', password_hash=hash_password('111'), role='curator',
                 last_name='Смирнова', first_name='Анна', patronymic='Ивановна'),
            User(username='cur6', password_hash=hash_password('111'), role='curator',
                 last_name='Михайлова', first_name='Елена', patronymic='Петровна'),
            User(username='cur7', password_hash=hash_password('111'), role='curator',
                 last_name='Сидорова', first_name='Ольга', patronymic='Алексеевна'),
        ]
        db.add_all(curators)
        db.flush()

        # Привязка кураторов к группам
        groups['ИСП-Б-2022'].curator_id = curators[0].id
        groups['ИСП-Б-2023'].curator_id = curators[1].id
        groups['ИСП-Б-2024'].curator_id = curators[2].id
        groups['ИКС-Б-2023'].curator_id = curators[3].id
        groups['ПД-Б-2022'].curator_id = curators[4].id
        groups['ПСО-Б-2023'].curator_id = curators[5].id
        groups['ИСП-К-2022'].curator_id = curators[6].id
        groups['ИСП-К-2023'].curator_id = curators[6].id

        # ── Админ ────────────────────────────────────────────────────────
        admin = User(username='admin', password_hash=hash_password('111'), role='admin',
                     last_name='Администратор', first_name='', patronymic='')
        db.add(admin)

        # ── Комиссия ─────────────────────────────────────────────────────
        commission = User(username='commission', password_hash=hash_password('111'), role='curator',
                          last_name='Председатель', first_name='Комиссии', patronymic='')
        db.add(commission)

        # ── Студенты (первая группа — с реальными ФИО) ─────────────────
        student_names = [
            ('ivanov', 'Иванов', 'Сергей', 'Александрович'),
            ('petrov', 'Петров', 'Алексей', 'Васильевич'),
            ('sidorov', 'Сидоров', 'Михаил', 'Сергеевич'),
            ('smirnov', 'Смирнов', 'Павел', 'Алексеевич'),
            ('kuznetsov', 'Кузнецов', 'Денис', 'Иванович'),
            ('popov', 'Попов', 'Николай', 'Петрович'),
            ('vasiliev', 'Васильев', 'Дмитрий', 'Андреевич'),
            ('zaytsev', 'Зайцев', 'Владислав', 'Евгеньевич'),
            ('sokolov', 'Соколов', 'Глеб', 'Владимирович'),
            ('mikhailov', 'Михайлов', 'Егор', 'Максимович'),
            ('fedorov', 'Фёдоров', 'Тимофей', 'Артёмович'),
            ('morozov', 'Морозов', 'Константин', 'Викторович'),
            ('volkov', 'Волков', 'Игорь', 'Борисович'),
            ('alekseev', 'Алексеев', 'Валентин', 'Алексеевич'),
            ('lebedev', 'Лебедев', 'Роман', 'Григорьевич'),
            ('kozlov', 'Козлов', 'Владимир', 'Фёдорович'),
            ('novikov', 'Новиков', 'Станислав', 'Олегович'),
            ('stepanov', 'Степанов', 'Арсений', 'Станиславович'),
            ('nikolaev', 'Николаев', 'Богдан', 'Геннадьевич'),
            ('orlov', 'Орлов', 'Виктор', 'Денисович'),
            ('andreev', 'Андреев', 'Ярослав', 'Эдуардович'),
            ('tarasov', 'Тарасов', 'Валерий', 'Игоревич'),
            ('grigoriev', 'Григорьев', 'Георгий', 'Витальевич'),
            ('samsonov', 'Самсонов', 'Лев', 'Тимурович'),
            ('zharov', 'Жаров', 'Тарас', 'Даниилович'),
        ]
        for uname, ln, fn, pt in student_names:
            grp_name = list(groups.keys())[0]
            grp = groups[grp_name]
            db.add(User(
                username=uname, password_hash=hash_password('111'), role='student',
                last_name=ln, first_name=fn, patronymic=pt,
                group_name=grp.name, group_id=grp.id,
            ))

        # ── student1..student25 ──────────────────────────────────────────
        student_full = [
            ('Иванов', 'Иван', 'Иванович'),
            ('Петров', 'Пётр', 'Петрович'),
            ('Сидоров', 'Сидор', 'Сидорович'),
            ('Смирнов', 'Алексей', 'Владимирович'),
            ('Кузнецов', 'Дмитрий', 'Сергеевич'),
            ('Попова', 'Анна', 'Михайловна'),
            ('Васильев', 'Андрей', 'Павлович'),
            ('Зайцева', 'Елена', 'Алексеевна'),
            ('Соколов', 'Сергей', 'Николаевич'),
            ('Михайлова', 'Ольга', 'Викторовна'),
            ('Фёдоров', 'Артём', 'Денисович'),
            ('Морозов', 'Егор', 'Тимофеевич'),
            ('Волкова', 'Татьяна', 'Сергеевна'),
            ('Алексеев', 'Максим', 'Игоревич'),
            ('Лебедева', 'Юлия', 'Владимировна'),
            ('Козлов', 'Владимир', 'Александрович'),
            ('Новикова', 'Мария', 'Евгеньевна'),
            ('Степанов', 'Никита', 'Романович'),
            ('Николаев', 'Кирилл', 'Вадимович'),
            ('Орлова', 'Наталья', 'Геннадьевна'),
            ('Андреев', 'Илья', 'Максимович'),
            ('Тарасов', 'Денис', 'Олегович'),
            ('Григорьева', 'Екатерина', 'Алексеевна'),
            ('Самсонов', 'Роман', 'Станиславович'),
            ('Жаров', 'Вадим', 'Борисович'),
        ]
        for i, (ln, fn, pt) in enumerate(student_full, 1):
            grp_name = list(groups.keys())[i % len(groups)]
            grp = groups[grp_name]
            db.add(User(
                username=f'student{i}', password_hash=hash_password('111'), role='student',
                last_name=ln, first_name=fn, patronymic=pt,
                group_name=grp.name, group_id=grp.id,
            ))

        db.commit()
        print(f'✅ Seed-данные загружены:')
        print(f'  👤 Пользователей: {db.query(User).count()}')
        print(f'  🏫 Групп:         {db.query(Group).count()}')
        print(f'  📚 Специальностей: {db.query(Specialty).count()}')
        print(f'  🏛 Отделений:     {db.query(Department).count()}')
        print(f'  🔑 Пароль: 111')
        print(f'  admin / commission / cur1..cur7 / student1..student25')

    finally:
        db.close()


if __name__ == '__main__':
    load_data()
