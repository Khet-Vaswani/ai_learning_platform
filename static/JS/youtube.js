// ============================================================
// youtube.js — YouTube Player + Info + Related Videos
// ============================================================

let currentVideo    = {id:'', title:'', topic:''};
let videoWatched    = false;
let watchCheckTimer = null;
let descExpanded    = false;

// ── Search YouTube ────────────────────────────────────────
async function searchYouTube(query) {
    const container = document.getElementById('searchResults');
    if (!container) return;

    container.innerHTML = `
        <div class="col-12 text-center py-4">
            <div class="spinner-border text-primary"
                 style="width:2rem; height:2rem;"></div>
            <p class="mt-3 text-muted" style="font-size:0.85rem;">
                Searching <strong>"${query}"</strong>...
            </p>
        </div>`;

    const data = await API.get(
        `/youtube/search?q=${encodeURIComponent(query)}&limit=20`
    );

    if (!data.success || !data.videos || !data.videos.length) {
        container.innerHTML = `
            <div class="col-12 text-center py-4">
                <div style="font-size:2.5rem;">🔍</div>
                <p class="text-muted mt-2">
                    No videos found for "${query}"
                </p>
            </div>`;
        return;
    }

    container.innerHTML = data.videos.map(v => {
        const titleJson = JSON.stringify(v.title);
        const queryJson = JSON.stringify(data.query);
        return `
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="vid-card"
                 onclick='openVideo(
                     "${v.video_id}",
                     ${titleJson},
                     ${queryJson}
                 )'>
                <div class="vid-thumb">
                    <img src="${v.thumbnail}" alt="video"
                         onerror="this.src='https://via.placeholder.com/320x180'">
                    <div class="vid-overlay">
                        <div class="vid-play-btn">
                            <i class="fas fa-play"></i>
                        </div>
                    </div>
                </div>
                <div class="vid-info">
                    <p class="vid-title">
                        ${v.title.substring(0,60)}
                        ${v.title.length > 60 ? '...' : ''}
                    </p>
                    <span class="vid-tag">${v.channel}</span>
                </div>
            </div>
        </div>`;
    }).join('');
}

// ── Open Video Modal ──────────────────────────────────────
async function openVideo(videoId, title, topic) {
    currentVideo = {id: videoId, title: title, topic: topic};
    videoWatched = false;
    descExpanded = false;

    if (watchCheckTimer) {
        clearInterval(watchCheckTimer);
        watchCheckTimer = null;
    }

    // Set player
    const player = document.getElementById('youtubePlayer');
    if (player) {
        player.src =
            `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    }

    // Set titles
    const modalTitle = document.getElementById('videoModalTitle');
    const fullTitle  = document.getElementById('videoFullTitle');
    if (modalTitle) modalTitle.textContent = title;
    if (fullTitle)  fullTitle.textContent  = title;

    // Reset panels
    resetModalPanels();

    // Lock quiz
    lockQuizButton();

    // Show modal
    const modalEl = document.getElementById('videoModal');
    if (modalEl) {
        new bootstrap.Modal(modalEl).show();
    }

    // Load video details
    loadVideoDetails(videoId, topic);

    // Load related videos
    loadRelatedVideos(topic);

    // Save watch history
    try {
        await API.post('/youtube/watched', {
            video_id: videoId,
            title   : title,
            topic   : topic
        });
    } catch(e) {}

    // Start watch timer
    startWatchTimer();
}

// ── Load Video Details ────────────────────────────────────
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
            if (avatarEl) avatarEl.textContent = v.channel_title ? v.channel_title[0] : 'YT';

            if (dateEl && v.published_at) {
                const d = new Date(v.published_at);
                dateEl.textContent = d.toLocaleDateString('en-US', {
                    year:'numeric', month:'long', day:'numeric'
                });
            }

            if (descEl && v.description) {
                descEl.textContent = v.description.substring(0, 300) + '...';
            }
        }
    } catch(e) {
        console.log('Video details error:', e);
    }
}

// ── Load Related Videos ───────────────────────────────────
async function loadRelatedVideos(topic) {
    const container = document.getElementById('relatedVideosList');
    if (!container) return;

    try {
        const data = await API.get(
            `/youtube/search?q=${encodeURIComponent(topic)}&limit=6`
        );

        if (!data.success || !data.videos || !data.videos.length) {
            container.innerHTML =
                '<p style="font-size:0.75rem;color:#94a3b8;text-align:center;padding:10px;">No related videos</p>';
            return;
        }

        const videos = data.videos
            .filter(v => v.video_id !== currentVideo.id)
            .slice(0, 5);

        container.innerHTML = videos.map(v => {
            const titleJson = JSON.stringify(v.title);
            const topicJson = JSON.stringify(topic);
            return `
            <div onclick='openVideo("${v.video_id}",${titleJson},${topicJson})'
                 style="display:flex;gap:8px;padding:6px;border-radius:8px;
                        cursor:pointer;transition:background 0.2s;margin-bottom:8px;"
                 onmouseover="this.style.background='#f1f5f9'"
                 onmouseout="this.style.background='transparent'">
                <div style="width:90px;height:54px;border-radius:6px;
                            overflow:hidden;flex-shrink:0;background:#f1f5f9;">
                    <img src="${v.thumbnail}"
                         style="width:100%;height:100%;object-fit:cover;"
                         onerror="this.src='https://via.placeholder.com/90x54'">
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:0.75rem;font-weight:600;color:#1e293b;
                                line-height:1.3;display:-webkit-box;
                                -webkit-line-clamp:2;-webkit-box-orient:vertical;
                                overflow:hidden;">
                        ${v.title}
                    </div>
                    <div style="font-size:0.68rem;color:#94a3b8;margin-top:3px;">
                        ${v.channel}
                    </div>
                </div>
            </div>`;
        }).join('');

    } catch(e) {
        container.innerHTML = '';
    }
}

// ── Toggle Description ────────────────────────────────────
function toggleDescription() {
    const el = document.getElementById('videoDescription');
    if (!el) return;
    descExpanded       = !descExpanded;
    el.style.maxHeight = descExpanded ? 'none' : '80px';
    el.style.overflow  = descExpanded ? 'visible' : 'hidden';
}

// ── Format Numbers ────────────────────────────────────────
function formatNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
    if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
    return n.toString();
}

// ── Lock Quiz Button ──────────────────────────────────────
function lockQuizButton() {
    const btn = document.getElementById('quizBtn');
    if (!btn) return;
    btn.disabled      = true;
    btn.innerHTML     = '<i class="fas fa-lock me-1"></i>Watch to unlock';
    btn.style.opacity = '0.6';
    btn.style.cursor  = 'not-allowed';
    btn.onclick       = null;

    // Hide progress bar
    const progressEl = document.getElementById('watchProgress');
    if (progressEl) progressEl.style.display = 'none';
}

// ── Unlock Notification ───────────────────────────────────
function showUnlockNotification(msg) {
    const notif = document.createElement('div');
    notif.style.cssText = `
        position:fixed; bottom:30px; right:30px;
        background:linear-gradient(135deg,#059669,#047857);
        color:white; padding:14px 20px; border-radius:12px;
        font-size:0.85rem; font-weight:600; z-index:9999;
        box-shadow:0 8px 25px rgba(5,150,105,0.4);
        display:flex; align-items:center; gap:10px;
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

// ── Watch Timer ───────────────────────────────────────────
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

// ── Unlock + Auto Open Quiz ───────────────────────────────
async function unlockAndOpenQuiz() {
    videoWatched = true;

    // Update button
    const btn = document.getElementById('quizBtn');
    if (btn) {
        btn.disabled        = true;
        btn.innerHTML       = '<i class="fas fa-spinner fa-spin me-1"></i>Generating Quiz...';
        btn.style.opacity   = '1';
        btn.style.cursor    = 'wait';
        btn.style.background= '#f0fdf4';
        btn.style.color     = '#059669';
    }

    // Show notification
    showUnlockNotification('Video complete! Generating quiz...');

    // Auto generate quiz
    try {
        const data = await API.post('/gemini/generate-quiz', {
            video_id   : currentVideo.id,
            video_title: currentVideo.title,
            topic      : currentVideo.topic
        });

        if (data.success) {
            if (btn) {
                btn.disabled  = false;
                btn.innerHTML = '<i class="fas fa-check me-1"></i>Quiz Ready ✅';
                btn.style.cursor = 'pointer';
                btn.onclick   = () => window.open(
                    '/quiz/page/' + data.quiz_id, '_blank'
                );
            }

            // Auto open quiz in new tab
            setTimeout(() => {
                window.open('/quiz/page/' + data.quiz_id, '_blank');
            }, 800);

        } else {
            if (btn) {
                btn.disabled  = false;
                btn.innerHTML = '<i class="fas fa-clipboard-check me-1"></i>Take Quiz';
                btn.style.cursor = 'pointer';
                btn.onclick   = generateQuiz;
            }
        }

    } catch(e) {
        console.log('Quiz generation error:', e);
        if (btn) {
            btn.disabled  = false;
            btn.innerHTML = '<i class="fas fa-clipboard-check me-1"></i>Take Quiz';
            btn.style.cursor = 'pointer';
            btn.onclick   = generateQuiz;
        }
    }
}

// ── Reset Modal ───────────────────────────────────────────
function resetModalPanels() {
    ['quizContainer', 'quizResult', 'notesSection', 'watchProgress']
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

    // Reset stats
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

// ── Stop Video ────────────────────────────────────────────
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
    if (modal) {
        modal.addEventListener('hidden.bs.modal', stopVideo);
    }
});
