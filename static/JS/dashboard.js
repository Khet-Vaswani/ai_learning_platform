// ============================================================
// dashboard.js — Dashboard Dynamic Updates
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

    // ── Animate Stat Numbers ──────────────────────────────
    animateNumbers();

    // ── Animate Progress Bars ─────────────────────────────
    animateProgressBars();

    // ── Auto-refresh recommendations every 5 mins ─────────
    // setInterval(loadRecommendations, 300000);

    // ─────────────────────────────────────────────────────
    // Animate counting numbers (e.g. 0 → 42)
    // ─────────────────────────────────────────────────────
    function animateNumbers() {
        const statNumbers = document.querySelectorAll('.stat-info h4');

        statNumbers.forEach(el => {
            const text    = el.textContent.trim();
            const hasSlash = text.includes('/');

            if (hasSlash) {
                // e.g. "7/10" — animate left number only
                const parts  = text.split('/');
                const target = parseInt(parts[0]);
                const max    = parts[1];
                if (isNaN(target)) return;

                animateCount(el, 0, target, 800, `/${max}`);
            } else {
                const target = parseInt(text);
                if (isNaN(target)) return;
                animateCount(el, 0, target, 800, '');
            }
        });
    }

    function animateCount(el, start, end, duration, suffix) {
        const range    = end - start;
        const stepTime = Math.abs(Math.floor(duration / range)) || 50;
        let   current  = start;

        const timer = setInterval(() => {
            current += 1;
            el.textContent = current + suffix;
            if (current >= end) {
                el.textContent = end + suffix;
                clearInterval(timer);
            }
        }, stepTime);
    }

    // ─────────────────────────────────────────────────────
    // Animate progress bars on load
    // ─────────────────────────────────────────────────────
    function animateProgressBars() {
        const bars = document.querySelectorAll('.progress-bar');

        bars.forEach(bar => {
            const targetWidth = bar.style.width;
            bar.style.width   = '0%';

            setTimeout(() => {
                bar.style.transition = 'width 1s ease';
                bar.style.width      = targetWidth;
            }, 300);
        });
    }

    // ─────────────────────────────────────────────────────
    // Highlight active nav link
    // ─────────────────────────────────────────────────────
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});