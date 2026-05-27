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

    // ─────────────────────────────────────────────────────
    // Load personalized recommendations for new users
    // ─────────────────────────────────────────────────────
    const personalizedContainer = document.getElementById('personalizedRecommendations');
    if (personalizedContainer) {
        loadPersonalizedRecommendations();
    }
});

// ─────────────────────────────────────────────────────────
// Load Personalized Recommendations for New Users
// ─────────────────────────────────────────────────────────
async function loadPersonalizedRecommendations() {
    const container = document.getElementById('personalizedRecommendations');
    if (!container) return;

    try {
        const data = await API.get('/recommend/videos');

        if (!data.success || !data.recommendations ||
            !data.recommendations.length) {
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div style="font-size:2.5rem; margin-bottom:10px;">🎯</div>
                    <p class="text-muted" style="font-size:0.85rem;">
                        Start exploring topics in your field!
                    </p>
                </div>`;
            return;
        }

        // Display top 6 recommendations in a clean grid
        let html = '';
        data.recommendations.slice(0, 6).forEach(video => {
            html += `
                <div class="col-lg-4 col-md-6">
                    <div class="vid-card" onclick="openVideo('${video.video_id}', '${video.title.replace(/'/g, "\\'")}', '${video.reason || 'Recommended'}')">
                        <div class="vid-thumb">
                            <img src="${video.thumbnail}" alt="" onerror="this.src='https://via.placeholder.com/320x180'">
                            <div class="vid-overlay">
                                <div class="vid-play-btn">
                                    <i class="fas fa-play ms-1"></i>
                                </div>
                            </div>
                            <div style="position:absolute; top:8px; right:8px; background:#7c3aed; color:white; padding:2px 8px; border-radius:12px; font-size:0.65rem; font-weight:600;">
                                ${video.expert === 'history' ? '🎯' : video.expert === 'weak_topic' ? '⚠️' : '📈'} ${video.expert.replace('_', ' ')}
                            </div>
                        </div>
                        <div class="vid-info">
                            <p class="vid-title">${video.title.substring(0, 50)}${video.title.length > 50 ? '...' : ''}</p>
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span class="vid-tag">${video.reason || 'Recommended'}</span>
                                <span style="font-size:0.65rem; color:#94a3b8;">${video.channel || 'YouTube'}</span>
                            </div>
                        </div>
                    </div>
                </div>`;
        });

        container.innerHTML = html;

    } catch (error) {
        console.error('Error loading personalized recommendations:', error);
        container.innerHTML = `
            <div class="col-12 text-center py-4">
                <div style="font-size:2rem; margin-bottom:10px;">⚡</div>
                <p class="text-muted" style="font-size:0.85rem;">
                    Recommendations will load shortly...
                </p>
            </div>`;
    }
}