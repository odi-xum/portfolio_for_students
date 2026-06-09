/**
 * app.js — Diplom Portfolio
 * CSRF, theme, lightbox, notifications, welcome modal, nav highlight
 */
(function () {
    'use strict';

    // ── CSRF token injection ────────────────────────────────────────────
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

    // ── Active nav highlight ────────────────────────────────────────────
    (function () {
        var path = window.location.pathname;
        document.querySelectorAll('.top-nav a').forEach(function (a) {
            var href = a.getAttribute('href');
            if (href && path.startsWith(href) && href !== '/') {
                a.classList.add('active-page');
            }
        });
    })();

    // ── Theme toggle ────────────────────────────────────────────────────
    var themeBtn = document.getElementById('themeToggle');
    var THEME_KEY = 'diplom_theme';

    function setTheme(mode) {
        var isLight = mode === 'light';
        document.body.classList.toggle('light-theme', isLight);
        if (themeBtn) themeBtn.textContent = isLight ? '🌙' : '☀️';
        localStorage.setItem(THEME_KEY, mode);
    }

    if (themeBtn) {
        themeBtn.addEventListener('click', function () {
            setTheme(document.body.classList.contains('light-theme') ? 'dark' : 'light');
        });
    }

    var saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light') setTheme('light');

    // ── Notifications (SSE + poll) ──────────────────────────────────────
    var isAuth = document.body.getAttribute('data-user-authenticated') === 'true';
    if (isAuth) {
        var badge = document.getElementById('unread-badge');
        if (!badge) return;

        function showBadge(n) {
            if (n > 0) {
                badge.textContent = n > 99 ? '99+' : n;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        }

        if (window.EventSource) {
            (function() {
                var es = new EventSource('/api/notifications/stream');
                es.addEventListener('message', function (e) {
                    try { showBadge(JSON.parse(e.data).unread); } catch (_) {}
                });
                es.addEventListener('error', function () { es.close(); });
            })();
        }

        function pollNotifications() {
            fetch('/api/notifications/count')
                .then(function (r) { return r.json(); })
                .then(function (d) { showBadge(d.unread); })
                .catch(function () {});
        }
        pollNotifications();
        setInterval(pollNotifications, 30000);
    }

    // ── Lightbox ────────────────────────────────────────────────────────
    var overlay = document.getElementById('lightbox-overlay');
    var img = document.getElementById('lightbox-img');
    var zoomed = false;

    if (overlay && img) {
        window.openLightbox = function (src) {
            img.src = src;
            img.classList.remove('zoomed');
            img.style.cursor = 'zoom-in';
            zoomed = false;
            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        };

        window.closeLightbox = function (e) {
            if (e && e.target !== overlay && e.target !== overlay.querySelector('button')) return;
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            img.src = '';
            zoomed = false;
            img.classList.remove('zoomed');
        };

        window.toggleZoom = function (e) {
            e.stopPropagation();
            zoomed = !zoomed;
            img.classList.toggle('zoomed', zoomed);
            img.style.cursor = zoomed ? 'zoom-out' : 'zoom-in';
        };

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && overlay.style.display === 'flex') closeLightbox();
        });
    }

    // ── Welcome modal ───────────────────────────────────────────────────
    var welcome = document.getElementById('welcome-modal');
    if (welcome) {
        var WELCOME_KEY = 'diplom_welcome_dismissed';
        if (localStorage.getItem(WELCOME_KEY) !== '1') {
            setTimeout(function () {
                welcome.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }, 400);
        }
    }

    window.closeWelcomeModal = function () {
        if (!welcome) return;
        welcome.style.display = 'none';
        document.body.style.overflow = '';
        var cb = document.getElementById('welcome-dont-show');
        if (cb && cb.checked) {
            localStorage.setItem('diplom_welcome_dismissed', '1');
        }
    };
})();
