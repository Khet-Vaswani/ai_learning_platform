// ============================================================
// recommend.js — Recommendation Display + Post-Quiz Refresh
// ============================================================

// Video titles and channels come from YouTube, where anyone can name a video:
// escape everything that goes into HTML.
function escR(str) {
    return String(str == null ? '' : str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// A JS argument inside a double-quoted onclick="..." attribute
function jsArgR(value) {
    return escR(JSON.stringify(value == null ? '' : value));
}

// ── Load MoE recommendations ──────────────────────────────
async function loadRecommendations() {
    const container = document.getElementById('recommendedVideos');
    if (!container) return;

    container.innerHTML = `
        <div class="col-12 text-center py-4">
            <div class="spinner-border"
                 style="width:2rem;height:2rem;color:#7c3aed;"></div>
            <p class="mt-3 text-muted" style="font-size:0.82rem;">
                AI analyzing your profile...
            </p>
        </div>`;

    try {
        const data = await API.get('/recommend/videos');

        if (!data.success || !data.recommendations || !data.recommendations.length) {
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div style="font-size:2.5rem;margin-bottom:10px;">🤖</div>
                    <p class="text-muted" style="font-size:0.85rem;">
                        No recommendations yet. Search a topic or take a quiz!
                    </p>
                </div>`;
            return;
        }

        renderVideoCards(container, data.recommendations);

    } catch(e) {
        console.error('loadRecommendations error:', e);
        container.innerHTML = `
            <div class="col-12 text-center py-4 text-muted">
                <p style="font-size:0.82rem;">
                    Could not load recommendations. Try refreshing.
                </p>
            </div>`;
    }
}

// ── Load preference videos (new users) ────────────────────
async function loadPreferenceVideos() {
    const container = document.getElementById('preferenceVideos');
    if (!container) return;

    container.innerHTML = `
        <div class="col-12 text-center py-4">
            <div class="spinner-border"
                 style="width:2rem;height:2rem;color:#7c3aed;"></div>
            <p class="mt-2 text-muted" style="font-size:0.82rem;">
                Loading videos for your field...
            </p>
        </div>`;

    try {
        const data = await API.get('/recommend/preference-videos');

        if (!data.success || !data.videos || !data.videos.length) {
            container.innerHTML = `
                <div class="col-12 text-center py-4 text-muted">
                    <p style="font-size:0.82rem;">
                        No videos found for your preferences.
                        Try searching a topic!
                    </p>
                </div>`;
            return;
        }

        // Render with field label
        renderPreferenceCards(container, data.videos, data.field, data.skill_level);

    } catch(e) {
        console.error('loadPreferenceVideos error:', e);
        container.innerHTML = `
            <div class="col-12 text-center py-4 text-muted">
                <p style="font-size:0.82rem;">Could not load videos.</p>
            </div>`;
    }
}

// ── Render preference video cards ─────────────────────────
function renderPreferenceCards(container, videos, field, skillLevel) {
    const expertStyle = {
        bg   : '#faf5ff',
        color: '#7c3aed',
        label: '🎯 ' + (field || 'Your Field'),
    };

    container.innerHTML = videos.map(function(v) {
        const titleJson = jsArgR(v.title || '');
        const topicJson = jsArgR(v.topic || field || '');
        const thumb     = v.thumbnail ||
            'https://img.youtube.com/vi/' + v.video_id + '/mqdefault.jpg';

        return `
        <div class="col-md-4 col-sm-6 mb-3">
            <div class="vid-card"
                 onclick="openVideo(${jsArgR(v.video_id)}, ${titleJson}, ${topicJson})">
                <div class="vid-thumb">
                    <img src="${escR(thumb)}" alt=""
                         onerror="this.src='https://via.placeholder.com/320x180?text=Video'">
                    <div class="vid-overlay">
                        <div class="vid-play-btn">
                            <i class="fas fa-play ms-1"></i>
                        </div>
                    </div>
                    <div style="position:absolute;top:7px;left:7px;
                                background:${expertStyle.bg};
                                color:${expertStyle.color};
                                padding:2px 8px;border-radius:10px;
                                font-size:0.62rem;font-weight:700;
                                border:1px solid ${expertStyle.color}33;">
                        ${escR(expertStyle.label)}
                    </div>
                    <div style="position:absolute;bottom:7px;right:7px;
                                background:rgba(0,0,0,0.7);color:white;
                                padding:2px 8px;border-radius:5px;
                                font-size:0.62rem;font-weight:700;">
                        ${escR(skillLevel || 'Beginner')}
                    </div>
                </div>
                <div class="vid-info">
                    <p class="vid-title">
                        ${escR((v.title || '').substring(0, 60))}${(v.title || '').length > 60 ? '...' : ''}
                    </p>
                    <div style="display:flex;justify-content:space-between;
                                align-items:center;">
                        <span class="vid-tag">${escR(v.topic || field || '')}</span>
                        <span style="font-size:0.65rem;color:#7c3aed;font-weight:600;">
                            ${escR(v.channel || 'YouTube')}
                        </span>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');
}

// ── Render MoE recommendation cards ───────────────────────
function renderVideoCards(container, recommendations) {
    const expertStyle = {
        'weak_topic' : {bg:'#fef2f2', color:'#dc2626', label:'⚠️ Weak Topic'},
        'performance': {bg:'#f0fdf4', color:'#059669', label:'📊 Performance'},
        'history'    : {bg:'#faf5ff', color:'#7c3aed', label:'🎯 Recommended'},
        'post_quiz'  : {bg:'#fffbeb', color:'#d97706', label:'📝 Post Quiz'},
    };

    container.innerHTML = recommendations.map(function(v) {
        const titleJson  = jsArgR(v.title  || '');
        const reasonJson = jsArgR(v.reason || '');
        const es         = expertStyle[v.expert] ||
                           {bg:'#f8fafc', color:'#64748b', label:'🤖 AI'};
        const matchPct   = v.final_score ? Math.round(v.final_score * 100) : 0;
        const thumb      = v.thumbnail ||
            'https://img.youtube.com/vi/' + v.video_id + '/mqdefault.jpg';

        return `
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="vid-card"
                 onclick="openVideo(${jsArgR(v.video_id)}, ${titleJson}, ${reasonJson})">
                <div class="vid-thumb">
                    <img src="${escR(thumb)}" alt=""
                         onerror="this.src='https://via.placeholder.com/320x180?text=Video'">
                    <div class="vid-overlay">
                        <div class="vid-play-btn">
                            <i class="fas fa-play"></i>
                        </div>
                    </div>
                    <div style="position:absolute;top:7px;left:7px;
                                background:${es.bg};color:${es.color};
                                border:1px solid ${es.color}33;
                                padding:2px 8px;border-radius:10px;
                                font-size:0.62rem;font-weight:700;">
                        ${escR(es.label)}
                    </div>
                    ${matchPct > 0 ? `
                    <div style="position:absolute;bottom:7px;right:7px;
                                background:rgba(0,0,0,0.75);color:white;
                                padding:2px 7px;border-radius:6px;
                                font-size:0.62rem;font-weight:600;">
                        ${matchPct}% match
                    </div>` : ''}
                </div>
                <div class="vid-info">
                    <p class="vid-title">
                        ${escR((v.title || '').substring(0, 60))}${(v.title || '').length > 60 ? '...' : ''}
                    </p>
                    <div style="display:flex;justify-content:space-between;
                                align-items:center;flex-wrap:wrap;gap:4px;">
                        <span class="vid-tag">${escR(v.channel || 'YouTube')}</span>
                    </div>
                    ${v.reason ? `
                    <div style="font-size:0.68rem;color:#94a3b8;
                                margin-top:5px;line-height:1.3;
                                display:-webkit-box;-webkit-line-clamp:2;
                                -webkit-box-orient:vertical;overflow:hidden;">
                        ${escR(v.reason)}
                    </div>` : ''}
                </div>
            </div>
        </div>`;
    }).join('');
}

// ── Show post-quiz recommendations ────────────────────────
// Called from quiz_page.html after submit
function showPostQuizRecommendations(videos, reason, difficulty, topic) {
    if (!videos || !videos.length) return;

    // Create or find container
    let container = document.getElementById('postQuizRecs');
    if (!container) {
        container = document.createElement('div');
        container.id = 'postQuizRecs';
        container.style.cssText = `
            margin-top: 20px;
            padding: 20px;
            background: white;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        `;

        // Find quiz result container and append after it
        const resultEl = document.getElementById('quizResultContainer') ||
                         document.querySelector('.quiz-result') ||
                         document.body;
        resultEl.appendChild(container);
    }

    const diffColors = {
        'beginner'    : {bg:'#fef2f2', color:'#dc2626', icon:'🔴'},
        'intermediate': {bg:'#fffbeb', color:'#d97706', icon:'🟡'},
        'advanced'    : {bg:'#f0fdf4', color:'#059669', icon:'🟢'},
    };
    const dc = diffColors[difficulty] || diffColors['intermediate'];

    container.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;
                    margin-bottom:14px;padding-bottom:12px;
                    border-bottom:1px solid #f1f5f9;">
            <h6 style="margin:0;font-size:0.9rem;font-weight:700;color:#1e293b;
                       display:flex;align-items:center;gap:8px;">
                <span style="background:${dc.bg};color:${dc.color};
                             padding:4px 10px;border-radius:10px;
                             font-size:0.78rem;">
                    ${dc.icon} ${escR(difficulty)} videos
                </span>
                Recommended for you
            </h6>
            <span style="font-size:0.75rem;color:#94a3b8;">${escR(reason)}</span>
        </div>
        <div class="row g-3">
            ${videos.map(function(v) {
                const titleJson = jsArgR(v.title || '');
                const topicJson = jsArgR(topic || '');
                const thumb     = v.thumbnail ||
                    'https://img.youtube.com/vi/' + v.video_id + '/mqdefault.jpg';
                return `
                <div class="col-md-4">
                    <div class="vid-card"
                         onclick="openVideoNewTab(${jsArgR(v.video_id)}, ${titleJson}, ${topicJson})">
                        <div class="vid-thumb">
                            <img src="${escR(thumb)}" alt=""
                                 onerror="this.src='https://via.placeholder.com/320x180'">
                            <div class="vid-overlay">
                                <div class="vid-play-btn">
                                    <i class="fas fa-play ms-1"></i>
                                </div>
                            </div>
                        </div>
                        <div class="vid-info">
                            <p class="vid-title">
                                ${escR((v.title || '').substring(0, 55))}...
                            </p>
                            <span class="vid-tag">${escR(v.channel || 'YouTube')}</span>
                        </div>
                    </div>
                </div>`;
            }).join('')}
        </div>
        <div style="margin-top:12px;text-align:center;">
            <a href="/dashboard"
               style="font-size:0.8rem;color:#2563eb;font-weight:600;
                      text-decoration:none;display:inline-flex;
                      align-items:center;gap:5px;">
                View all recommendations on dashboard →
            </a>
        </div>`;
}

// Open video in new tab (from quiz page)
function openVideoNewTab(videoId, title, topic) {
    const url = 'https://www.youtube.com/watch?v=' + encodeURIComponent(videoId);
    window.open(url, '_blank');
}