// Applies the saved light/dark theme before first paint and wires [data-theme-toggle] buttons.
(function () {
    var key = 'renova-theme';
    var stored = null;
    try { stored = localStorage.getItem(key); } catch (e) { /* storage unavailable */ }
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-bs-theme', stored || (prefersDark ? 'dark' : 'light'));

    document.addEventListener('click', function (event) {
        var button = event.target.closest('[data-theme-toggle]');
        if (!button) return;
        var next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', next);
        try { localStorage.setItem(key, next); } catch (e) { /* storage unavailable */ }
    });
})();
