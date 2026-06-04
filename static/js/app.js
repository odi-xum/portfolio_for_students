/**
 * app.js — общие скрипты ИС Портфолио
 * Lightbox, CSRF-токен, уведомления (SSE + poll), тема
 */
(function () {
    'use strict';

    var csrfToken = document.body.getAttribute('data-csrf-token') || '';
    if (csrfToken) {
        var csrfInput = '<input type="hidden" name="_csrf_token" value="' + csrfToken + '">';
        document.addEventListener('DOMContentLoaded', function () {
            document.querySelectorAll('form').forEach(function (f) {
                if (!f.querySelector('input[name="_csrf_token"]')) {
                    f.insertAdjacentHTML('beforeend', csrfInput);
                }
            });
        });
    }

    var isAuthenticated = document.body.getAttribute('data-user-authenticated') === 'true';

    if (isAuthenticated) {
        var badge = document.getElementById('unread-badge');

        function showBadge(n) {
            if (n > 0) {
                badge.textContent = n > 99 ? '99+' : n;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        }

        // SSE
        if (window.EventSource) {
            var es = new EventSource('/api/notifications/stream');
            es.addEventListener('message', function (e) {
                try { showBadge(JSON.parse(e.data).unread); } catch (_) {}
            });
            es.addEventListener('error', function () { es.close(); });
        }

        // Poll fallback
        function pollNotifications() {
            fetch('/api/notifications/count')
                .then(function (r) { return r.json(); })
                .then(function (d) { showBadge(d.unread); })
                .catch(function () {});
        }
        pollNotifications();
        setInterval(pollNotifications, 30000);
    }

    // Lightbox
    var overlay = document.getElementById('lightbox-overlay');
    var img = document.getElementById('lightbox-img');
    var zoomed = false;

    if (overlay && img) {
        window.openLightbox = function (src) {
            img.src = src;
            img.style.maxWidth = '90vw';
            img.style.maxHeight = '90vh';
            img.style.width = '';
            img.style.height = '';
            img.style.cursor = 'zoom-in';
            zoomed = false;
            overlay.style.display = 'block';
            document.body.style.overflow = 'hidden';
        };

        window.closeLightbox = function (e) {
            if (e && e.target !== overlay && e.target !== overlay.querySelector('button')) return;
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            img.src = '';
            zoomed = false;
        };

        window.toggleZoom = function (e) {
            e.stopPropagation();
            if (!zoomed) {
                img.style.maxWidth = 'none';
                img.style.maxHeight = 'none';
                img.style.width = 'auto';
                img.style.height = 'auto';
                img.style.cursor = 'zoom-out';
                zoomed = true;
            } else {
                img.style.maxWidth = '90vw';
                img.style.maxHeight = '90vh';
                img.style.width = '';
                img.style.height = '';
                img.style.cursor = 'zoom-in';
                zoomed = false;
            }
        };

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && overlay.style.display === 'block') closeLightbox();
        });
    }

    // Theme toggle
    var themeBtns = document.querySelectorAll('.theme-toggle');
    if (themeBtns.length) {
        var STORAGE_KEY = 'diplom_theme';

        function setTheme(mode) {
            var isLight = mode === 'light';
            document.body.classList.toggle('light-theme', isLight);
            themeBtns.forEach(function (b) {
                b.textContent = isLight ? '🌙' : '☀️';
                b.title = isLight ? 'Тёмная тема' : 'Светлая тема';
            });
            localStorage.setItem(STORAGE_KEY, mode);
        }

        themeBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                setTheme(document.body.classList.contains('light-theme') ? 'dark' : 'light');
            });
        });

        var saved = localStorage.getItem(STORAGE_KEY);
        if (saved === 'light') setTheme('light');
    }
})();
