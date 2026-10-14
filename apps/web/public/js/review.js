// Review screens without inline code (CSP: script-src 'self', style-src 'self').
// - [data-box="x0,y0,x1,y1"]: positions a field box over its page image (fractions of the page).
// - [data-field-key]: hovering or focusing an element highlights every element with the same key.
// - [data-refresh="ms"]: reloads the page after the given delay (documents still processing).
(function () {
    'use strict';

    function place(el) {
        var parts = (el.getAttribute('data-box') || '').split(',').map(Number);
        if (parts.length !== 4 || parts.some(function (n) { return !isFinite(n); })) {
            return;
        }
        el.style.left = parts[0] * 100 + '%';
        el.style.top = parts[1] * 100 + '%';
        el.style.width = (parts[2] - parts[0]) * 100 + '%';
        el.style.height = (parts[3] - parts[1]) * 100 + '%';
    }

    function highlight(key, on) {
        document.querySelectorAll('[data-field-key="' + CSS.escape(key) + '"]').forEach(function (el) {
            el.classList.toggle('is-active', on);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-box]').forEach(place);

        document.querySelectorAll('[data-field-key]').forEach(function (el) {
            var key = el.getAttribute('data-field-key');
            ['mouseenter', 'focusin'].forEach(function (type) {
                el.addEventListener(type, function () { highlight(key, true); });
            });
            ['mouseleave', 'focusout'].forEach(function (type) {
                el.addEventListener(type, function () { highlight(key, false); });
            });
        });

        var refresh = document.querySelector('[data-refresh]');
        if (refresh) {
            var delay = parseInt(refresh.getAttribute('data-refresh'), 10);
            if (delay >= 1000) {
                setTimeout(function () { window.location.reload(); }, delay);
            }
        }
    });
})();
