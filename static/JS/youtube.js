// ============================================================
// youtube.js — YouTube-style Search + Player + Related Videos
// ============================================================

let currentVideo    = {id:'', title:'', topic:''};
let videoWatched    = false;
let watchCheckTimer = null;
let descExpanded    = false;

// ── Helper: dark mode check ───────────────────────────────
function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
}

// ══════════════════════════════════════════════════════════
//  SEARCH YOUTUBE — YouTube-style layout
// ══════════════════════════════════════════════════════════
// ============================================================
// youtube.js — UPDATED searchYouTube() function
// Sirf is function ko apne youtube.js mein replace karo
// Baaki sab functions same rahenge
// ============================================================

async function searchYouTube(query) {
    const container = document.getElementById('searchResults');
    if (!container) return;

    // ── Skeleton loading — YouTube style ─────────────────
    container.innerHTML = Array(5).fill(`
        <div style="display:flex;gap:14px;padding:10px;margin-bottom:4px;">
            <div style="width:246px;min-width:246px;height:138px;border-radius:10px;
                        background:linear-gradient(90deg,
                            var(--bg-tertiary,#f1f5f9) 25%,
                            var(--bg-secondary,#f8fafc) 50%,
                            var(--bg-tertiary,#f1f5f9) 75%);
                        background-size:200% 100%;
                        animation:yt-shimmer 1.4s infinite;flex-shrink:0;">
            </div>
            <div style="flex:1;padding-top:4px;">
                <div style="height:14px;border-radius:4px;margin-bottom:10px;
                            background:linear-gradient(90deg,
                                var(--bg-tertiary,#f1f5f9) 25%,
                                var(--bg-secondary,#f8fafc) 50%,
                                var(--bg-tertiary,#f1f5f9) 75%);
                            background-size:200% 100%;
                            animation:yt-shimmer 1.4s infinite;">
                </div>
                <div style="height:12px;width:55%;border-radius:4px;margin-bottom:8px;
                            background:linear-gradient(90deg,
                                var(--bg-tertiary,#f1f5f9) 25%,
                                var(--bg-secondary,#f8fafc) 50%,
                                var(--bg-tertiary,#f1f5f9) 75%);
                            background-size:200% 100%;
                            animation:yt-shimmer 1.4s infinite;">
                </div>
                <div style="height:11px;width:35%;border-radius:4px;
                            background:linear-gradient(90deg,
                                var(--bg-tertiary,#f1f5f9) 25%,
                                var(--bg-secondary,#f8fafc) 50%,
                                var(--bg-tertiary,#f1f5f9) 75%);
                            background-size:200% 100%;
                            animation:yt-shimmer 1.4s infinite;">
                </div>
            </div>
        </div>`
    ).join('');

    const data = await API.get(
        `/youtube/search?q=${encodeURIComponent(query)}&limit=20`
    );

    if (!data.success || !data.videos || !data.videos.length) {
        container.innerHTML = `
            <div style="text-align:center;padding:56px 20px;">
                <div style="font-size:3rem;margin-bottom:14px;">🔍</div>
                <div style="font-size:1rem;font-weight:600;
                            color:var(--text-primary,#1e293b);margin-bottom:6px;">
                    No results for "${query}"
                </div>
                <div style="font-size:0.82rem;color:var(--text-muted,#94a3b8);">
                    Try different keywords or check spelling
                </div>
            </div>`;
        return;
    }

    // ── Header ────────────────────────────────────────────
    const header = `
        <div style="display:flex;align-items:center;
                    justify-content:space-between;flex-wrap:wrap;gap:10px;
                    padding-bottom:14px;margin-bottom:6px;
                    border-bottom:1px solid var(--border-color,#e2e8f0);">
            <div>
                <div style="font-size:0.82rem;
                            color:var(--text-muted,#94a3b8);margin-bottom:3px;">
                    Search results
                </div>
                <div style="font-size:1rem;font-weight:700;
                            color:var(--text-primary,#1e293b);">
                    "${query}"
                    <span style="font-size:0.75rem;font-weight:400;
                                 color:var(--text-muted,#94a3b8);margin-left:8px;">
                        ${data.videos.length} videos found
                    </span>
                </div>
            </div>
            <a href="/dashboard"
               style="font-size:0.75rem;color:var(--text-muted,#94a3b8);
                      text-decoration:none;font-weight:600;
                      padding:6px 14px;border-radius:8px;
                      border:1px solid var(--border-color,#e2e8f0);
                      background:var(--bg-card,white);
                      display:inline-flex;align-items:center;gap:5px;
                      transition:all 0.2s;"
               onmouseover="this.style.background='var(--bg-secondary,#f8fafc)'"
               onmouseout="this.style.background='var(--bg-card,white)'">
                ✕ Clear search
            </a>
        </div>`;

    // ── Badge config per expert type ──────────────────────
    const expertBadge = {
        'weak_topic' : { bg:'#FCEBEB', color:'#A32D2D', label:'Weak Topic'  },
        'cognitive'  : { bg:'#EEEDFE', color:'#3C3489', label:'AI Picked'   },
        'history'    : { bg:'#EAF3DE', color:'#27500A', label:'New Topic'   },
        'performance': { bg:'#E1F5EE', color:'#085041', label:'Top Scorer'  },
    };

    // ── Cards ─────────────────────────────────────────────
    const cards = data.videos.map((v, i) => {
        const titleJson = JSON.stringify(v.title  || '');
        const queryJson = JSON.stringify(data.query || query);
        const title     = v.title    || 'Untitled';
        const channel   = v.channel  || 'YouTube';
        const thumb     = v.thumbnail ||
            `https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`;
        const views     = v.view_count
            ? formatNumber(v.view_count) + ' views' : '';
        const ago       = v.published_at ? timeAgo(v.published_at) : '';
        const duration  = v.duration || '';
        const desc      = v.description
            ? v.description.substring(0, 140) + '...' : '';
        const matchPct  = v.final_score
            ? Math.round(v.final_score * 100)
            : Math.max(60, 97 - i * 3);

        // Expert badge (from MoE) or default
        const eb = expertBadge[v.expert] ||
            { bg:'#EEEDFE', color:'#3C3489', label:'AI Sorted' };

        // Verified channel tick for top results
        const verified = i < 3
            ? `<svg width="13" height="13" viewBox="0 0 24 24"
                    fill="#2563eb" style="flex-shrink:0;">
                   <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
               </svg>` : '';

        // Avatar initial + color
        const avatarColors = [
            'linear-gradient(135deg,#2563eb,#7c3aed)',
            'linear-gradient(135deg,#059669,#047857)',
            'linear-gradient(135deg,#dc2626,#991b1b)',
            'linear-gradient(135deg,#d97706,#b45309)',
            'linear-gradient(135deg,#0891b2,#0e7490)',
        ];
        const avatarBg = avatarColors[i % avatarColors.length];

        return `
        <div style="display:flex;gap:14px;padding:10px;margin-bottom:2px;
                    border-radius:12px;cursor:pointer;
                    border:1px solid transparent;
                    transition:all 0.2s ease;"
             onmouseover="this.style.background='var(--bg-secondary,#f8fafc)';
                          this.style.borderColor='var(--border-color,#e2e8f0)';"
             onmouseout="this.style.background='transparent';
                         this.style.borderColor='transparent';"
             onclick='openVideo("${v.video_id}",${titleJson},${queryJson})'>

            <!-- ── Thumbnail ── -->
            <div style="position:relative;width:246px;min-width:246px;
                        height:138px;border-radius:10px;overflow:hidden;
                        background:#0f172a;flex-shrink:0;">
                <img src="${thumb}" alt=""
                     style="width:100%;height:100%;object-fit:cover;
                            display:block;transition:transform 0.35s ease;"
                     onerror="this.src='https://via.placeholder.com/246x138/1e293b/475569?text=Video'"
                     onmouseover="this.style.transform='scale(1.05)'"
                     onmouseout="this.style.transform='scale(1)'">

                <!-- Play overlay -->
                <div style="position:absolute;inset:0;
                            background:rgba(0,0,0,0.3);
                            display:flex;align-items:center;
                            justify-content:center;
                            opacity:0;transition:opacity 0.2s;"
                     onmouseover="this.style.opacity='1'"
                     onmouseout="this.style.opacity='0'">
                    <div style="width:46px;height:46px;border-radius:50%;
                                background:rgba(255,255,255,0.95);
                                display:flex;align-items:center;
                                justify-content:center;
                                box-shadow:0 4px 16px rgba(0,0,0,0.3);">
                        <svg width="16" height="16" viewBox="0 0 16 16"
                             fill="#2563eb">
                            <polygon points="4,2 14,8 4,14"/>
                        </svg>
                    </div>
                </div>

                <!-- Duration badge -->
                ${duration ? `
                <div style="position:absolute;bottom:7px;right:7px;
                            background:rgba(0,0,0,0.82);color:white;
                            padding:2px 6px;border-radius:4px;
                            font-size:11px;font-weight:700;
                            letter-spacing:0.03em;">
                    ${duration}
                </div>` : ''}
            </div>

            <!-- ── Info ── -->
            <div style="flex:1;min-width:0;display:flex;
                        flex-direction:column;gap:7px;padding-top:2px;">

                <!-- Title -->
                <p style="font-size:0.9rem;font-weight:600;
                          color:var(--text-primary,#1e293b);
                          margin:0;line-height:1.45;
                          display:-webkit-box;-webkit-line-clamp:2;
                          -webkit-box-orient:vertical;overflow:hidden;">
                    ${title}
                </p>

                <!-- Views · Time ago -->
                <div style="display:flex;align-items:center;gap:6px;
                            font-size:0.72rem;
                            color:var(--text-muted,#94a3b8);">
                    ${views ? `<span>${views}</span>` : ''}
                    ${views && ago ? `<span style="width:3px;height:3px;border-radius:50%;background:var(--text-muted,#94a3b8);display:inline-block;"></span>` : ''}
                    ${ago  ? `<span>${ago}</span>`   : ''}
                </div>

                <!-- Channel row -->
                <div style="display:flex;align-items:center;gap:7px;">
                    <div style="width:22px;height:22px;border-radius:50%;
                                background:${avatarBg};
                                display:flex;align-items:center;
                                justify-content:center;color:white;
                                font-size:10px;font-weight:700;
                                flex-shrink:0;">
                        ${channel[0].toUpperCase()}
                    </div>
                    <span style="font-size:0.75rem;font-weight:600;
                                 color:var(--text-secondary,#475569);">
                        ${channel}
                    </span>
                    ${verified}
                </div>

                <!-- Description -->
                ${desc ? `
                <p style="font-size:0.74rem;
                          color:var(--text-muted,#94a3b8);
                          margin:0;line-height:1.55;
                          display:-webkit-box;-webkit-line-clamp:2;
                          -webkit-box-orient:vertical;overflow:hidden;">
                    ${desc}
                </p>` : ''}

                <!-- Badges row -->
                <div style="display:flex;align-items:center;
                            gap:7px;flex-wrap:wrap;margin-top:auto;">
                    <span style="font-size:0.67rem;font-weight:600;
                                 padding:3px 9px;border-radius:20px;
                                 background:${eb.bg};color:${eb.color};">
                        ${eb.label}
                    </span>
                    <span style="margin-left:auto;font-size:0.7rem;
                                 font-weight:600;color:#534AB7;
                                 display:flex;align-items:center;gap:3px;">
                        <svg width="11" height="11" viewBox="0 0 12 12"
                             fill="#534AB7">
                            <polygon points="6,1 7.5,4.5 11,5 8.5,7.5 9,11 6,9.5 3,11 3.5,7.5 1,5 4.5,4.5"/>
                        </svg>
                        ${matchPct}% match
                    </span>
                </div>

            </div>
        </div>`;
    }).join('');

    container.innerHTML = header + cards;
}

// ── Time Ago helper ───────────────────────────────────────
function timeAgo(dateStr) {
    try {
        const diff = Date.now() - new Date(dateStr).getTime();
        const days = Math.floor(diff / 86400000);
        if (days < 1)   return 'Today';
        if (days < 7)   return days + ' days ago';
        if (days < 30)  return Math.floor(days / 7)  + ' weeks ago';
        if (days < 365) return Math.floor(days / 30) + ' months ago';
        return Math.floor(days / 365) + ' years ago';
    } catch(e) { return ''; }
}

// ══════════════════════════════════════════════════════════
//  OPEN VIDEO MODAL
// ══════════════════════════════════════════════════════════
async function openVideo(videoId, title, topic) {
    currentVideo = {id: videoId, title: title, topic: topic};
    videoWatched = false;
    descExpanded = false;

    if (watchCheckTimer) {
        clearInterval(watchCheckTimer);
        watchCheckTimer = null;
    }

    const player = document.getElementById('youtubePlayer');
    if (player) {
        player.src =
            `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    }

    const modalTitle = document.getElementById('videoModalTitle');
    const fullTitle  = document.getElementById('videoFullTitle');
    if (modalTitle) modalTitle.textContent = title;
    if (fullTitle)  fullTitle.textContent  = title;

    resetModalPanels();
    lockQuizButton();

    const modalEl = document.getElementById('videoModal');
    if (modalEl) new bootstrap.Modal(modalEl).show();

    loadVideoDetails(videoId, topic);
    loadRelatedVideos(topic);

    try {
        await API.post('/youtube/watched', {
            video_id: videoId,
            title   : title,
            topic   : topic
        });
    } catch(e) {}

    startWatchTimer();
}

// ══════════════════════════════════════════════════════════
//  VIDEO DETAILS
// ══════════════════════════════════════════════════════════
async function loadVideoDetails(videoId, topic) {
    try {
        const data = await API.get(
            `/youtube/video-details?video_id=${videoId}`
        );

        if (data.success && data.video) {
            const v = data.video;

            const viewEl   = document.getElementById('viewCount');
            const likeEl   = document.getElementById('likeCount');
            const commEl   = document.getElementById('commentCount');
            const chanEl   = document.getElementById('channelName');
            const avatarEl = document.getElementById('channelAvatar');
            const dateEl   = document.getElementById('publishDate');
            const descEl   = document.getElementById('videoDescription');

            if (viewEl)   viewEl.textContent   = formatNumber(v.view_count) + ' views';
            if (likeEl)   likeEl.textContent   = formatNumber(v.like_count) + ' likes';
            if (commEl)   commEl.textContent   = formatNumber(v.comment_count) + ' comments';
            if (chanEl)   chanEl.textContent   = v.channel_title || '';
            if (avatarEl) avatarEl.textContent = v.channel_title
                ? v.channel_title[0].toUpperCase() : 'YT';

            if (dateEl && v.published_at) {
                const d = new Date(v.published_at);
                dateEl.textContent = d.toLocaleDateString('en-US', {
                    year:'numeric', month:'long', day:'numeric'
                });
            }

            if (descEl && v.description) {
                descEl.textContent =
                    v.description.substring(0, 300) +
                    (v.description.length > 300 ? '...' : '');
            }
        }
    } catch(e) {
        console.log('Video details error:', e);
    }
}

// ══════════════════════════════════════════════════════════
//  RELATED VIDEOS — upgraded cards
// ══════════════════════════════════════════════════════════
async function loadRelatedVideos(topic) {
    const container = document.getElementById('relatedVideosList');
    if (!container) return;

    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-secondary"></div>
        </div>`;

    try {
        const data = await API.get(
            `/youtube/search?q=${encodeURIComponent(topic)}&limit=8`
        );

        if (!data.success || !data.videos || !data.videos.length) {
            container.innerHTML =
                `<p style="font-size:0.75rem;color:#94a3b8;
                           text-align:center;padding:10px;">
                    No related videos
                 </p>`;
            return;
        }

        const videos = data.videos
            .filter(v => v.video_id !== currentVideo.id)
            .slice(0, 5);

        container.innerHTML = videos.map((v, i) => {
            const titleJson = JSON.stringify(v.title);
            const topicJson = JSON.stringify(topic);
            const thumb     = v.thumbnail ||
                `https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`;

            return `
            <div onclick='openVideo("${v.video_id}",${titleJson},${topicJson})'
                 style="display:flex;gap:9px;padding:7px 8px;border-radius:10px;
                        cursor:pointer;transition:background 0.2s;margin-bottom:6px;
                        border:1px solid transparent;"
                 onmouseover="this.style.background='var(--bg-tertiary,#f1f5f9)';
                              this.style.borderColor='var(--border-color,#e2e8f0)';"
                 onmouseout="this.style.background='transparent';
                             this.style.borderColor='transparent';">

                <!-- Thumb -->
                <div style="width:90px;height:54px;border-radius:8px;
                            overflow:hidden;flex-shrink:0;
                            background:var(--bg-tertiary,#f1f5f9);
                            position:relative;">
                    <img src="${thumb}"
                         style="width:100%;height:100%;object-fit:cover;"
                         onerror="this.src='https://via.placeholder.com/90x54/1e293b/475569?text=Video'">
                    <div style="position:absolute;inset:0;
                                display:flex;align-items:center;
                                justify-content:center;
                                background:rgba(0,0,0,0.35);
                                opacity:0;transition:opacity 0.2s;"
                         onmouseover="this.style.opacity='1'"
                         onmouseout="this.style.opacity='0'">
                        <i class="fas fa-play"
                           style="color:white;font-size:0.75rem;"></i>
                    </div>
                </div>

                <!-- Info -->
                <div style="flex:1;min-width:0;">
                    <div style="font-size:0.74rem;font-weight:600;
                                color:var(--text-primary,#1e293b);
                                line-height:1.35;
                                display:-webkit-box;-webkit-line-clamp:2;
                                -webkit-box-orient:vertical;overflow:hidden;
                                margin-bottom:4px;">
                        ${v.title}
                    </div>
                    <div style="display:flex;align-items:center;
                                justify-content:space-between;">
                        <div style="font-size:0.65rem;
                                    color:var(--text-muted,#94a3b8);">
                            ${v.channel || ''}
                        </div>
                        <div style="font-size:0.58rem;
                                    color:#7c3aed;
                                    background:rgba(124,58,237,0.08);
                                    padding:1px 6px;border-radius:5px;
                                    font-weight:600;">
                            #${i+1}
                        </div>
                    </div>
                </div>
            </div>`;
        }).join('');

    } catch(e) {
        container.innerHTML = '';
    }
}

// ══════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════
function toggleDescription() {
    const el = document.getElementById('videoDescription');
    if (!el) return;
    descExpanded       = !descExpanded;
    el.style.maxHeight = descExpanded ? 'none' : '80px';
    el.style.overflow  = descExpanded ? 'visible' : 'hidden';
}

function formatNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
    if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
    return n.toString();
}

function lockQuizButton() {
    const btn = document.getElementById('quizBtn');
    if (!btn) return;
    btn.disabled      = true;
    btn.innerHTML     = '<i class="fas fa-lock me-1"></i>Watch to unlock';
    btn.style.opacity = '0.6';
    btn.style.cursor  = 'not-allowed';
    btn.onclick       = null;
    const progressEl = document.getElementById('watchProgress');
    if (progressEl) progressEl.style.display = 'none';
}

function showUnlockNotification(msg) {
    const notif = document.createElement('div');
    notif.style.cssText = `
        position:fixed; bottom:30px; right:30px;
        background:linear-gradient(135deg,#059669,#047857);
        color:white; padding:14px 20px; border-radius:12px;
        font-size:0.85rem; font-weight:600; z-index:9999;
        box-shadow:0 8px 25px rgba(5,150,105,0.4);
        display:flex; align-items:center; gap:10px;
        animation: slideUp 0.3s ease;
    `;
    notif.innerHTML = `
        <i class="fas fa-unlock" style="font-size:1.1rem;"></i>
        ${msg || 'Quiz unlocked! Generating quiz...'}
    `;
    document.body.appendChild(notif);
    setTimeout(() => {
        notif.style.opacity    = '0';
        notif.style.transition = 'opacity 0.3s';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

function startWatchTimer() {
    let watchSecs = 0;
    const needed  = 60;
    watchCheckTimer = setInterval(() => {
        watchSecs++;
        if (watchSecs >= needed && !videoWatched) {
            clearInterval(watchCheckTimer);
            unlockAndOpenQuiz();
        }
    }, 1000);
}

async function unlockAndOpenQuiz() {
    videoWatched = true;
    const btn = document.getElementById('quizBtn');
    if (btn) {
        btn.disabled        = true;
        btn.innerHTML       = '<i class="fas fa-spinner fa-spin me-1"></i>Generating Quiz...';
        btn.style.opacity   = '1';
        btn.style.cursor    = 'wait';
        btn.style.background= '#f0fdf4';
        btn.style.color     = '#059669';
    }
    showUnlockNotification('Video complete! Generating quiz...');
    try {
        const data = await API.post('/gemini/generate-quiz', {
            video_id   : currentVideo.id,
            video_title: currentVideo.title,
            topic      : currentVideo.topic
        });
        if (data.success) {
            if (btn) {
                btn.disabled     = false;
                btn.innerHTML    = '<i class="fas fa-check me-1"></i>Quiz Ready ✅';
                btn.style.cursor = 'pointer';
                btn.onclick      = () => window.open('/quiz/page/' + data.quiz_id, '_blank');
            }
            setTimeout(() => {
                window.open('/quiz/page/' + data.quiz_id, '_blank');
            }, 800);
        } else {
            if (btn) {
                btn.disabled     = false;
                btn.innerHTML    = '<i class="fas fa-clipboard-check me-1"></i>Take Quiz';
                btn.style.cursor = 'pointer';
                btn.onclick      = generateQuiz;
            }
        }
    } catch(e) {
        console.log('Quiz generation error:', e);
        if (btn) {
            btn.disabled     = false;
            btn.innerHTML    = '<i class="fas fa-clipboard-check me-1"></i>Take Quiz';
            btn.style.cursor = 'pointer';
            btn.onclick      = generateQuiz;
        }
    }
}

function resetModalPanels() {
    ['quizContainer','quizResult','notesSection','watchProgress']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    const placeholder = document.getElementById('quizPlaceholder');
    if (placeholder) placeholder.style.display = 'block';

    const notesBtn = document.getElementById('notesBtn');
    if (notesBtn) {
        notesBtn.disabled  = false;
        notesBtn.innerHTML = '<i class="fas fa-sticky-note me-1"></i>Notes';
        notesBtn.onclick   = generateNotes;
    }

    ['viewCount','likeCount','commentCount',
     'channelName','videoDescription'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = id === 'viewCount' ? 'Loading...' : '—';
    });

    const relatedList = document.getElementById('relatedVideosList');
    if (relatedList) {
        relatedList.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border spinner-border-sm text-secondary"></div>
            </div>`;
    }
}

function stopVideo() {
    const player = document.getElementById('youtubePlayer');
    if (player) player.src = '';
    if (watchCheckTimer) {
        clearInterval(watchCheckTimer);
        watchCheckTimer = null;
    }
    videoWatched = false;
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('videoModal');
    if (modal) modal.addEventListener('hidden.bs.modal', stopVideo);
});