"""
Тесты маршрутов и авторизации.
"""
import pytest


def _has_text(data: bytes, text: str) -> bool:
    """Безопасная проверка наличия текста в байтовых данных (py3.14+)."""
    return text.encode('utf-8') in data


class TestPublicRoutes:
    """Публичные страницы, доступные без аутентификации."""

    def test_login_page_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert _has_text(resp.data, 'Вход')

    def test_login_page_redirect_when_authenticated(self, student_client):
        """Залогиненный студент редиректится со страницы логина."""
        resp = student_client.get('/', follow_redirects=False)
        assert resp.status_code == 302
        assert '/student/dashboard' in resp.location

    def test_portfolio_404_for_nonexistent(self, client):
        resp = client.get('/portfolio/nonexistent')
        assert resp.status_code == 404

    def test_portfolio_200_for_student(self, client):
        resp = client.get('/portfolio/student1')
        assert resp.status_code == 200
        assert _has_text(resp.data, 'Студентов') or _has_text(resp.data, 'student1')

    def test_static_css(self, client):
        resp = client.get('/static/css/style.css')
        assert resp.status_code == 200
        assert len(resp.data) > 0


class TestAuthRedirects:
    """Неаутентифицированные запросы должны редиректить на логин."""

    @pytest.mark.parametrize('url', [
        '/student/dashboard', '/student/create', '/student/history',
        '/curator/dashboard', '/curator/pending',
        '/admin/dashboard', '/admin/users', '/admin/groups',
        '/rating', '/profile', '/notifications',
    ])
    def test_redirects_to_login(self, client, url):
        resp = client.get(url, follow_redirects=False)
        assert resp.status_code == 302
        assert '/?next=' in resp.location or resp.location == '/' or 'login' in resp.location.lower()


class TestLoginFlow:
    """Полный цикл аутентификации."""

    def test_successful_login(self, client):
        # GET для установки сессии с CSRF-токеном
        client.get('/')
        with client.session_transaction() as sess:
            csrf_token = sess.get('_csrf_token', '')
        resp = client.post('/', data={
            'username': 'student1',
            'password': '111',
            '_csrf_token': csrf_token,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert '/student/dashboard' in resp.location

    def test_failed_login(self, client):
        client.get('/')
        with client.session_transaction() as sess:
            csrf_token = sess.get('_csrf_token', '')
        resp = client.post('/', data={
            'username': 'student1',
            'password': 'wrong_password',
            '_csrf_token': csrf_token,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert _has_text(resp.data, 'Неверный') or _has_text(resp.data, 'ошибк')

    def test_logout(self, student_client):
        resp = student_client.get('/logout', follow_redirects=False)
        assert resp.status_code == 302
        assert resp.location == '/'


class TestRoleAccess:
    """Проверка разграничения ролей."""

    ACCESS_MATRIX = [
        # (url, client_fixture, allowed_status)
        ('/admin/dashboard', 'admin_client', 200),
        ('/admin/dashboard', 'student_client', 403),
        ('/admin/dashboard', 'curator_client', 403),
        ('/student/dashboard', 'student_client', 200),
        ('/student/dashboard', 'admin_client', 403),
        ('/student/dashboard', 'curator_client', 403),
        ('/curator/dashboard', 'curator_client', 200),
        ('/curator/dashboard', 'student_client', 403),
        ('/curator/dashboard', 'admin_client', 403),
        ('/curator/pending', 'curator_client', 200),
        ('/curator/pending', 'student_client', 403),
        ('/curator/resolved', 'curator_client', 200),
        ('/rating', 'student_client', 200),
        ('/rating', 'curator_client', 200),
        ('/profile', 'student_client', 200),
        ('/profile', 'admin_client', 200),
        ('/notifications', 'student_client', 200),
        ('/student/portfolio_pdf', 'student_client', 200),  # PDF-портфолио
    ]

    @pytest.mark.parametrize('url,client_fixture,expected', ACCESS_MATRIX)
    def test_access(self, request, url, client_fixture, expected):
        cl = request.getfixturevalue(client_fixture)
        resp = cl.get(url)
        assert resp.status_code == expected, (
            f'{url} as {client_fixture}: expected {expected}, got {resp.status_code}'
        )


class TestApiRoutes:
    """API-эндпоинты."""

    def test_notification_count_authenticated(self, student_client):
        resp = student_client.get('/api/notifications/count')
        assert resp.status_code == 200
        assert _has_text(resp.data, 'unread')

    def test_event_detail_200_for_owner(self, student_client):
        resp = student_client.get('/event/1')
        assert resp.status_code == 200

    def test_event_detail_403_for_other_student(self, student_client):
        """Студент не может смотреть чужие мероприятия."""
        resp = student_client.get('/event/5')  # event 5 принадлежит orphan_student (id=6)
        assert resp.status_code == 403

    def test_student_api_events(self, student_client):
        resp = student_client.get('/student/api/events')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert 'events' in data

    def test_curator_api_events(self, curator_client):
        resp = curator_client.get('/curator/api/events')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert 'events' in data

    def test_student_api_forbidden_for_curator(self, curator_client):
        resp = curator_client.get('/student/api/events')
        assert resp.status_code == 403

    def test_curator_api_forbidden_for_student(self, student_client):
        resp = student_client.get('/curator/api/events')
        assert resp.status_code == 403
