"""
Тесты сервисного слоя.
"""
import pytest
from constants import EventStatus
from models import db, User, Event


class TestStudentService:
    """Сервис студента."""

    def test_get_student_event_stats(self, app):
        from services.student_service import get_student_event_stats
        stats = get_student_event_stats(4)
        assert stats['total'] == 3
        assert stats['approved'] == 1
        assert stats['pending'] == 1
        assert stats['rejected'] == 1

    def test_get_student_approved_events(self, app):
        from services.student_service import get_student_approved_events
        events = get_student_approved_events(4)
        assert len(events) == 1
        assert events[0].title == 'Олимпиада по Python'


class TestCuratorService:
    """Сервис куратора."""

    def test_get_curator_students(self, app):
        from services.curator_service import get_curator_students
        curator = db.session.get(User, 3)
        students = get_curator_students(curator)
        usernames = [s.username for s in students]
        assert 'student1' in usernames
        assert 'student2' in usernames
        assert 'orphan_student' not in usernames

    def test_get_curator_dashboard_stats(self, app):
        from services.curator_service import get_curator_dashboard_stats
        stats = get_curator_dashboard_stats(db.session.get(User, 3))
        assert stats['pending'] >= 1
        assert stats['approved'] >= 1
        assert stats['rejected'] >= 1

    def test_get_curator_events_pending(self, app):
        from services.curator_service import get_curator_events
        events = get_curator_events(db.session.get(User, 3), status_filter='pending')
        assert len(events) >= 1
        assert all(e.is_pending for e in events)

    def test_get_curator_events_resolved(self, app):
        from services.curator_service import get_curator_events
        events = get_curator_events(db.session.get(User, 3), status_filter='resolved')
        assert len(events) >= 1
        assert all(e.is_resolved for e in events)


class TestOkService:
    """Сервис общих компетенций."""

    def test_get_ok_stats(self, app):
        from services.ok_service import get_ok_stats
        stats = get_ok_stats(4)
        ok1 = next((s for s in stats if s['ok'] == 'OK-1'), None)
        assert ok1 is not None
        assert ok1['approved'] == 1

    def test_all_ok_not_completed(self, app):
        from services.ok_service import all_ok_completed
        assert all_ok_completed(4) is False

    def test_toggle_override(self, app):
        from services.ok_service import toggle_override
        assert toggle_override(4, 3, 'OK-9') is True
        assert toggle_override(4, 3, 'OK-9') is False


class TestNotificationService:
    """Сервис уведомлений."""

    def test_notify_user(self, app):
        from services.notification_service import notify_user
        n = notify_user(4, 'Тест', '/')
        assert n.message == 'Тест'
        assert n.link == '/'
        assert n.user_id == 4
        assert n.is_read is False or n.is_read is None

    def test_notify_student(self, app):
        from services.notification_service import notify_student
        n = notify_student(4, 'Привет')
        assert n.user_id == 4
        assert n.message == 'Привет'

    def test_notify_curators_of_group(self, app):
        from services.notification_service import notify_curators_of_group
        notifs = notify_curators_of_group(1, 'Новое мероприятие')
        assert len(notifs) == 1
        assert notifs[0].user_id == 3
