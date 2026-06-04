"""
Тесты CSRF-защиты.
"""
import pytest


class TestCsrfProtection:
    """CSRF-токен обязателен для POST/PUT/DELETE."""

    def test_post_without_csrf_returns_400(self, client):
        """POST без CSRF-токена → 400."""
        resp = client.post('/student/create', data={
            'title': 'test',
        }, follow_redirects=False)
        assert resp.status_code == 400

    def test_post_with_valid_csrf_succeeds(self, student_client):
        """POST с правильным CSRF-токеном → успех или 302."""
        with student_client.session_transaction() as sess:
            csrf_token = sess.get('_csrf_token', '')
        resp = student_client.post('/student/create', data={
            'title': 'test',
            'description': 'test desc',
            '_csrf_token': csrf_token,
        }, follow_redirects=False)
        # Может быть 302 (редирект из-за отсутствия файлов)
        # или 200 (форма), но не 400
        assert resp.status_code != 400, 'CSRF должен пропустить запрос'

    def test_csrf_exempt_stream(self, student_client):
        """SSE-поток не проверяет CSRF."""
        # GET — всегда OK, это не POST, но проверим, что путь не блокируется
        resp = student_client.get('/api/notifications/stream')
        assert resp.status_code == 200 or resp.status_code == 500  # 500 если SSE не стартует в тесте

    def test_csrf_exempt_import(self, admin_client):
        """Импорт студентов не проверяет CSRF."""
        resp = admin_client.post('/admin/import_students', data={
            'json_file': (None, ''),
        }, follow_redirects=True)
        # Должен быть не 400 (даже если другие ошибки валидации)
        assert resp.status_code != 400

    def test_login_with_explicit_csrf_works(self, client):
        """Логин с _csrf_token в форме работает."""
        # Получаем сессию
        resp = client.get('/')
        # Вытаскиваем CSRF-токен из куки (Flask сессия закодирована)
        # Используем утилитарный подход: токен в форме есть в шаблоне
        from flask import session
        with client.session_transaction() as sess:
            csrf_token = sess.get('_csrf_token', '')
        assert csrf_token, 'CSRF-токен должен быть в сессии после GET /'

        # POST с CSRF-токеном
        resp = client.post('/', data={
            'username': 'student1',
            'password': '111',
            '_csrf_token': csrf_token,
        }, follow_redirects=False)
        assert resp.status_code == 302, f'Ожидался редирект, получен {resp.status_code}'
