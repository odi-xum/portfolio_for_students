"""
Тесты моделей данных.
"""
import pytest
from constants import UserRole, EventStatus
from models import db, User, Event, EventFile, Group, Department


class TestUser:
    """Модель User."""

    def test_create_user(self, app):
        user = User(username='testuser', password_hash='hash',
                    role=UserRole.STUDENT, last_name='Тестов', first_name='Тест')
        db.session.add(user)
        db.session.commit()
        assert user.id is not None

    def test_full_name_with_patronymic(self, app):
        user = User(username='ivanov', password_hash='hash', role=UserRole.STUDENT,
                    last_name='Иванов', first_name='Иван', patronymic='Иванович')
        assert user.full_name == 'Иванов Иван Иванович'

    def test_full_name_partial(self, app):
        user = User(username='ivanov', password_hash='hash', role=UserRole.STUDENT,
                    last_name='Иванов')
        assert user.full_name == 'Иванов'

    def test_full_name_fallback_to_username(self, app):
        user = User(username='ivanov', password_hash='hash', role=UserRole.STUDENT)
        assert user.full_name == 'ivanov'

    def test_role_helpers(self, app):
        admin = User(role=UserRole.ADMIN)
        student = User(role=UserRole.STUDENT)
        curator = User(role=UserRole.CURATOR)
        assert admin.is_admin()
        assert not admin.is_student()
        assert student.is_student()
        assert curator.is_curator()

    def test_student_event_relationship(self, app):
        """Удаление студента каскадно удаляет его мероприятия."""
        user = User(username='todelete', password_hash='hash', role=UserRole.STUDENT)
        db.session.add(user)
        db.session.flush()
        event = Event(student_id=user.id, title='To delete', status=EventStatus.PENDING)
        db.session.add(event)
        db.session.commit()

        db.session.delete(user)
        db.session.commit()
        assert db.session.get(Event, event.id) is None


class TestEvent:
    """Модель Event."""

    def test_create_event(self, app):
        event = Event(student_id=4, title='Тестовое мероприятие',
                      description='Описание', status=EventStatus.PENDING)
        db.session.add(event)
        db.session.commit()
        assert event.id is not None
        assert event.status_label == 'На проверке'

    def test_status_labels(self, app):
        assert Event(student_id=4, title='T', status=EventStatus.APPROVED).status_label == 'Одобрено'
        assert Event(student_id=4, title='T', status=EventStatus.REJECTED).status_label == 'Отклонено'
        # Старый статус disputed всё ещё показывается как Отклонено
        assert Event(student_id=4, title='T', status='disputed').status_label == 'Отклонено'

    def test_is_resolved_property(self, app):
        assert Event(student_id=4, title='T', status=EventStatus.APPROVED).is_resolved is True
        assert Event(student_id=4, title='T', status=EventStatus.REJECTED).is_resolved is True
        assert Event(student_id=4, title='T', status=EventStatus.PENDING).is_resolved is False

    def test_category_label(self, app):
        assert Event(student_id=4, title='T', category='OK-1').category_label == 'OK-1'
        assert Event(student_id=4, title='T').category_label == 'Без категории'


class TestEventFile:
    """Модель EventFile."""

    def test_is_image(self, app):
        assert EventFile(file_type='png').is_image is True
        assert EventFile(file_type='jpg').is_image is True
        assert EventFile(file_type='pdf').is_image is False


class TestGroup:
    """Модель Group."""

    def test_group_relations(self, app):
        grp = db.session.get(Group, 1)
        assert grp.name == 'ИСП-Б-2022'
        assert grp.specialty_rel.abbreviation == 'ИСП'

    def test_curator_relation(self, app):
        grp = db.session.get(Group, 1)
        assert grp.curator.username == 'cur1'


class TestSpecialtyAndDepartment:
    """Связи специальности и отделения."""

    def test_department_specialties(self, app):
        dept = db.session.get(Department, 1)
        assert len(dept.specialties) == 1
        assert dept.specialties[0].abbreviation == 'ИСП'
