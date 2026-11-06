// ============================================================
// youtube.js — YouTube Player + Transcript + Notes + Quiz
// ============================================================

let currentVideo    = { id: '', title: '', topic: '' };
let videoWatched    = false;
let watchCheckTimer = null;
let descExpanded    = false;
let currentTranscript = '';

// ── API helper (uses existing api.js) ─────────────────────
const _api = window.API || {
    get : async (url) => { const r = await fetch(url); return r.json(); },
    post: async (url, body) => {
        const r = await fetch(url, {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify(body)
        });
        return r.json();
    }
};


// ══════════════════════════════════════════════════════════
//  OPEN VIDEO MODAL
// ══════════════════════════════════════════════════════════
async function openVideo(videoId, title, topic) {
    title = decodeEntitiesYT(title);
    currentVideo      = { id: videoId, title: title, topic: topic };
    videoWatched      = false;
    descExpanded      = false;
    currentTranscript = '';
    // Forget any quiz from the previously opened video
    if (typeof currentQuizId !== 'undefined') {
        currentQuizId = null; currentQuestions = []; currentAnswers = {};
        if (typeof currentQuizLevel !== "undefined") { currentQuizLevel = null; currentLevelBasis = ""; }
    }

    if (watchCheckTimer) {
        clearInterval(watchCheckTimer);
        watchCheckTimer = null;
    }

    // ── Load iframe ───────────────────────────────────────
    const player = document.getElementById('ytPlayer');
    if (player) {
        player.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1&iv_load_policy=3&enablejsapi=1`;
    }

    // ── Set titles ────────────────────────────────────────
    const mt = document.getElementById('modalTitle');
    const vt = document.getElementById('vidTitle');
    if (mt) mt.textContent = title;
    if (vt) vt.textContent = title;

    resetModalPanels();
    lockQuizButton();

    // ── Show modal ────────────────────────────────────────
    const modalEl = document.getElementById('videoModal');
    if (modalEl) new bootstrap.Modal(modalEl).show();

    // ── Load details, related ─────────────────────────────
    loadVideoDetails(videoId, topic);
    loadRelatedVideos(topic);

    // ── Fetch transcript first; notes are only made from it ──
    await fetchTranscript(videoId);
    startWatchTimer();
    if (currentVideo.id !== videoId) return;   // user opened another video meanwhile
    if (currentTranscript) {
        loadOrCreateNotes(videoId, title, topic);
    } else {
        showNoTranscriptNotice();
    }

    // ── Mark as watched ───────────────────────────────────
    try {
        await (_api.post || API.post)('/youtube/watched', {
            video_id: videoId,
            title   : title,
            topic   : topic
        });
    } catch(e) {}
}


// Open the AI assistant on this video. It only answers about watched videos,
// so make sure this one is saved first.
async function askAboutVideo() {
    const { id, title, topic } = currentVideo;
    if (!id) return;
    try {
        await (_api.post || API.post)('/youtube/watched', { video_id: id, title: title, topic: topic });
    } catch(e) {}
    window.location.href = '/chatbot?video=' + encodeURIComponent(id);
}


// ══════════════════════════════════════════════════════════
//  FETCH TRANSCRIPT FROM YOUTUBE
// ══════════════════════════════════════════════════════════
async function fetchTranscript(videoId) {
    const srcBadge = document.getElementById('notesSourceBadge');

    try {
        // Try backend transcript endpoint with videoId and title
        const titleParam = encodeURIComponent(currentVideo.title || '');
        const data = await fetch(`/youtube/transcript?video_id=${videoId}&title=${titleParam}`)
            .then(r => r.json());

        if (data.success && data.transcript && data.source !== 'metadata' && data.source !== 'description' && data.transcript.trim().length > 80) {
            currentTranscript = data.transcript;
            window.currentTranscript = data.transcript;
            console.log('✅ Authentic transcript loaded:', currentTranscript.length, 'chars');

            // Show transcript indicator
            if (srcBadge) {
                srcBadge.textContent = data.language
                    ? `📄 Transcript (${data.language})`
                    : '📄 From Transcript';
                srcBadge.style.background = '#f0fdf4';
                srcBadge.style.color = '#059669';
            }

            // Unlock quiz immediately if transcript available
            unlockQuizWithTranscript();
            return;
        }
    } catch(e) {
        console.log('Transcript API extraction notice:', e);
    }

    currentTranscript = '';
    window.currentTranscript = '';
    if (srcBadge) {
        srcBadge.textContent = 'No transcript';
        srcBadge.style.background = '#fef2f2';
        srcBadge.style.color = '#b91c1c';
    }
}

// Shown when the video has no captions and its audio couldn't be transcribed
function showNoTranscriptNotice() {
    const msg = "This video has no transcript we can use (no captions, and the audio couldn't be transcribed). " +
                "AI notes and quizzes are only made from what is said in the video, so they aren't available for this one.";
    const notesSection = document.getElementById('notesSection');
    const notesContent = document.getElementById('notesContent');
    const loading      = document.getElementById('aiLoadingSection');
    if (loading) loading.style.display = 'none';
    if (notesContent) notesContent.innerHTML = '<div style="color:#64748b;">' + escapeHtmlYT(msg) + '</div>';
    if (notesSection) notesSection.style.display = 'block';
    const locked = document.getElementById('quizLockedBanner');
    if (locked) {
        locked.style.display = 'block';
        locked.innerHTML = '<div style="font-weight:700;color:#334155;margin-bottom:4px;">Quiz not available</div>' +
                           '<div style="font-size:0.8rem;color:#64748b;">' + escapeHtmlYT(msg) + '</div>';
    }
    const ready = document.getElementById('quizReadyBanner');
    if (ready) ready.style.display = 'none';
}

// YouTube sends titles HTML-encoded (e.g. "What&#39;s"); decode before escaping.
// A textarea decodes entities only: tags stay as text and nothing runs.
const _decoderYT = document.createElement('textarea');
function decodeEntitiesYT(str) {
    str = String(str == null ? '' : str);
    if (str.indexOf('&') === -1) return str;
    _decoderYT.innerHTML = str;
    return _decoderYT.value;
}

function escapeHtmlYT(str) {
    return decodeEntitiesYT(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// A JS argument inside a double-quoted onclick="..." attribute
function jsArgYT(value) {
    return escapeHtmlYT(JSON.stringify(decodeEntitiesYT(value)));
}

function switchAiTab(tabName) {
    const notesTabBtn = document.getElementById('aiTabNotesBtn');
    const quizTabBtn  = document.getElementById('aiTabQuizBtn');
    const notesSec    = document.getElementById('notesSection');
    const quizSec     = document.getElementById('quizTabSection');

    if (!notesTabBtn || !quizTabBtn || !notesSec || !quizSec) return;

    if (tabName === 'notes') {
        notesSec.style.display = 'block';
        quizSec.style.display  = 'none';

        notesTabBtn.style.background  = '#ffffff';
        notesTabBtn.style.border      = '1px solid #cbd5e1';
        notesTabBtn.style.color       = '#4f46e5';
        notesTabBtn.style.fontWeight  = '700';
        notesTabBtn.style.boxShadow   = '0 1px 3px rgba(0,0,0,0.05)';

        quizTabBtn.style.background   = 'transparent';
        quizTabBtn.style.border       = '1px solid transparent';
        quizTabBtn.style.color        = '#64748b';
        quizTabBtn.style.fontWeight   = '600';
        quizTabBtn.style.boxShadow    = 'none';
    } else if (tabName === 'quiz') {
        notesSec.style.display = 'none';
        quizSec.style.display  = 'block';

        quizTabBtn.style.background   = '#ffffff';
        quizTabBtn.style.border       = '1px solid #cbd5e1';
        quizTabBtn.style.color        = '#059669';
        quizTabBtn.style.fontWeight   = '700';
        quizTabBtn.style.boxShadow    = '0 1px 3px rgba(0,0,0,0.05)';

        notesTabBtn.style.background  = 'transparent';
        notesTabBtn.style.border      = '1px solid transparent';
        notesTabBtn.style.color       = '#64748b';
        notesTabBtn.style.fontWeight  = '600';
        notesTabBtn.style.boxShadow   = 'none';
    }
}
window.switchAiTab = switchAiTab;

function unlockQuizWithTranscript() {
    const btn      = document.getElementById('quizBtn');
    const lockIcon = document.getElementById('quizLockIcon');
    const btnLabel = document.getElementById('quizBtnLabel');

    if (btn) {
        btn.disabled = false;
        if (lockIcon) lockIcon.className = 'fas fa-bolt me-1';
        if (btnLabel) btnLabel.textContent = 'Take Quiz';
        btn.style.opacity = '1';
        btn.style.cursor  = 'pointer';
        btn.onclick       = () => {
            if (window.generateQuiz) window.generateQuiz();
        };
    }

    // Update quiz ready banner
    const readyBanner  = document.getElementById('quizReadyBanner');
    const lockedBanner = document.getElementById('quizLockedBanner');
    const readyBtn     = document.getElementById('quizReadyBtn');

    if (readyBanner)  readyBanner.style.display  = 'block';
    if (lockedBanner) lockedBanner.style.display = 'none';

    if (readyBtn) {
        readyBtn.onclick = () => {
            if (window.generateQuiz) window.generateQuiz();
        };
    }
}

async function loadOrCreateNotes(videoId, title, topic) {
    const notesSection   = document.getElementById('notesSection');
    const notesContent   = document.getElementById('notesContent');
    const srcBadge       = document.getElementById('notesSourceBadge');
    const loadingSection = document.getElementById('aiLoadingSection');
    const loadingTitle   = document.getElementById('aiLoadingTitle');
    const loadingSub     = document.getElementById('aiLoadingSubtitle');

    if (notesSection) notesSection.style.display = 'none';
    if (notesContent) notesContent.innerHTML = '';

    // Show notes loading spinner inside the notes area
    if (loadingSection) {
        if (loadingTitle) loadingTitle.textContent = "Curating AI Notes...";
        if (loadingSub) loadingSub.textContent = "Checking database cache or generating study guide...";
        loadingSection.style.display = 'flex';
    }

    try {
        const notesRes = await fetch('/gemini/generate-notes', {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify({ video_id: videoId, video_title: title, topic: topic })
        }).then(r => r.json());

        if (loadingSection) loadingSection.style.display = 'none';

        if (notesRes.success) {
            if (notesContent) notesContent.innerHTML = formatNotesNotion(notesRes.notes);
            if (srcBadge) {
                srcBadge.textContent = "From the video's transcript";
                srcBadge.style.background = '#f0fdf4';
                srcBadge.style.color = '#059669';
            }
            if (notesSection) notesSection.style.display = 'block';
        } else {
            if (notesSection) {
                notesSection.style.display = 'block';
                if (notesContent) notesContent.innerHTML = '<div style="color:#b91c1c;">' + escapeHtmlYT(notesRes.message || "We couldn't generate notes. Try again.") + '</div>';
            }
        }
    } catch (e) {
        if (loadingSection) loadingSection.style.display = 'none';
        console.error('Error loading notes:', e);
    }
}

function formatNotesNotion(text) {
    if (!text) return '';
    let formatted = escapeHtmlYT(text);   // AI output is plain text; escape before formatting
    
    // Replace Headers
    formatted = formatted.replace(/## 📌 Topic Overview/g, '<h6 class="notion-h2">📌 Topic Overview</h6>');
    formatted = formatted.replace(/## 🔑 Key Concepts/g, '<h6 class="notion-h2">🔑 Key Concepts</h6>');
    formatted = formatted.replace(/## 📖 Important Definitions/g, '<h6 class="notion-h2">📖 Important Definitions</h6>');
    formatted = formatted.replace(/## 💡 Examples & Applications/g, '<h6 class="notion-h2">💡 Examples & Applications</h6>');
    formatted = formatted.replace(/## ⚡ Key Takeaways/g, '<h6 class="notion-h2">⚡ Key Takeaways</h6>');
    formatted = formatted.replace(/## 📝 Summary/g, '<h6 class="notion-h2">📝 Summary</h6>');
    
    // General H2s & H3s
    formatted = formatted.replace(/## (.*)/g, '<h6 class="notion-h2">$1</h6>');
    formatted = formatted.replace(/### (.*)/g, '<strong style="color:#1f2937; margin-top:12px; display:block; font-size:0.88rem;">$1</strong>');
    
    // Bullet points with Notion list item styling
    formatted = formatted.replace(/^- (.*)/gm, '<div class="notion-list-item">$1</div>');
    
    // Bold text
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Newlines to breaks
    formatted = formatted.replace(/\n\n/g, '<br>');
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}


// ══════════════════════════════════════════════════════════
//  VIDEO DETAILS
// ══════════════════════════════════════════════════════════
async function loadVideoDetails(videoId, topic) {
    try {
        const data = await fetch(`/youtube/video-details?video_id=${videoId}`)
            .then(r => r.json());

        if (data.success && data.video) {
            const v = data.video;
            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            };

            set('viewCount',  v.view_count   ? formatNum(v.view_count)   + ' views'    : '—');
            set('likeCount',  v.like_count   ? formatNum(v.like_count)   + ' likes'    : '—');
            set('chanName',   v.channel_title || '');

            const av = document.getElementById('chanAvatar');
            if (av) av.textContent = v.channel_title ? v.channel_title[0].toUpperCase() : 'YT';

            const dt = document.getElementById('pubDate');
            if (dt && v.published_at) {
                dt.textContent = new Date(v.published_at)
                    .toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric' });
            }

            const de = document.getElementById('vidDesc');
            if (de && v.description) {
                de.textContent = v.description.substring(0, 320) +
                    (v.description.length > 320 ? '...' : '');
            }
        }
    } catch(e) {}
}


// ══════════════════════════════════════════════════════════
//  RELATED VIDEOS (right sidebar)
// ══════════════════════════════════════════════════════════
async function loadRelatedVideos(topic) {
    const container = document.getElementById('relatedList');
    if (!container) return;

    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-secondary"></div>
        </div>`;

    try {
        const data = await fetch(
            `/youtube/search?q=${encodeURIComponent(topic)}&limit=8`
        ).then(r => r.json());

        if (!data.success || !data.videos || !data.videos.length) {
            container.innerHTML = `
                <p style="font-size:0.73rem;color:#94a3b8;
                          text-align:center;padding:12px 0;">
                    No related videos found
                </p>`;
            return;
        }

        const videos = data.videos
            .filter(v => v.video_id !== currentVideo.id)
            .slice(0, 6);

        const avatarColors = [
            'linear-gradient(135deg,#2563eb,#7c3aed)',
            'linear-gradient(135deg,#059669,#047857)',
            'linear-gradient(135deg,#dc2626,#991b1b)',
            'linear-gradient(135deg,#d97706,#b45309)',
            'linear-gradient(135deg,#0891b2,#0e7490)',
        ];

        container.innerHTML = videos.map((v, i) => {
            const tj     = jsArgYT(v.title || '');
            const topicJ = jsArgYT(topic || '');
            const thumb  = v.thumbnail ||
                `https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`;
            const avBg   = avatarColors[i % avatarColors.length];

            return `
            <div onclick="openVideo(${jsArgYT(v.video_id)},${tj},${topicJ})"
                 style="display:flex;gap:9px;padding:7px 8px;
                        border-radius:10px;cursor:pointer;
                        transition:all 0.2s;margin-bottom:5px;
                        border:1px solid transparent;"
                 onmouseover="this.style.background='#f1f5f9';this.style.borderColor='#e2e8f0';"
                 onmouseout="this.style.background='transparent';this.style.borderColor='transparent';">

                <!-- Thumb -->
                <div style="width:92px;min-width:92px;height:55px;
                            border-radius:8px;overflow:hidden;
                            background:#f1f5f9;position:relative;flex-shrink:0;">
                    <img src="${escapeHtmlYT(thumb)}"
                         style="width:100%;height:100%;object-fit:cover;"
                         onerror="this.src='https://via.placeholder.com/92x55/1e293b/475569?text=V'">
                    <div style="position:absolute;inset:0;background:rgba(0,0,0,0.3);
                                display:flex;align-items:center;justify-content:center;
                                opacity:0;transition:opacity 0.2s;"
                         onmouseover="this.style.opacity='1'"
                         onmouseout="this.style.opacity='0'">
                        <i class="fas fa-play" style="color:white;font-size:0.7rem;"></i>
                    </div>
                    <div style="position:absolute;top:4px;right:4px;
                                background:rgba(0,0,0,.72);color:white;
                                padding:1px 5px;border-radius:3px;
                                font-size:0.55rem;font-weight:700;">
                        #${i+1}
                    </div>
                </div>

                <!-- Info -->
                <div style="flex:1;min-width:0;">
                    <div style="font-size:0.74rem;font-weight:600;color:#1e293b;
                                line-height:1.35;
                                display:-webkit-box;-webkit-line-clamp:2;
                                -webkit-box-orient:vertical;overflow:hidden;
                                margin-bottom:4px;">
                        ${escapeHtmlYT(v.title || 'Video')}
                    </div>
                    <div style="display:flex;align-items:center;gap:5px;">
                        <div style="width:18px;height:18px;border-radius:50%;
                                    background:${avBg};flex-shrink:0;
                                    display:flex;align-items:center;justify-content:center;
                                    color:white;font-size:0.58rem;font-weight:700;">
                            ${escapeHtmlYT((v.channel || 'Y')[0].toUpperCase())}
                        </div>
                        <span style="font-size:0.64rem;color:#94a3b8;
                                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                            ${escapeHtmlYT(v.channel || 'YouTube')}
                        </span>
                    </div>
                </div>
            </div>`;
        }).join('');

    } catch(e) {
        container.innerHTML = '';
    }
}


// ══════════════════════════════════════════════════════════
//  SEARCH YOUTUBE (search results page)
// ══════════════════════════════════════════════════════════
async function searchYouTube(query) {
    const container = document.getElementById('searchResults');
    if (!container) return;

    // Skeleton loader
    container.innerHTML = Array(5).fill(`
        <div style="display:flex;gap:14px;padding:10px;margin-bottom:4px;">
            <div style="width:246px;min-width:246px;height:138px;border-radius:10px;
                        background:linear-gradient(90deg,#f1f5f9 25%,#f8fafc 50%,#f1f5f9 75%);
                        background-size:200% 100%;animation:shimmer 1.4s infinite;flex-shrink:0;">
            </div>
            <div style="flex:1;padding-top:4px;">
                <div style="height:14px;border-radius:4px;margin-bottom:10px;width:90%;
                            background:linear-gradient(90deg,#f1f5f9 25%,#f8fafc 50%,#f1f5f9 75%);
                            background-size:200% 100%;animation:shimmer 1.4s infinite;"></div>
                <div style="height:12px;border-radius:4px;margin-bottom:8px;width:55%;
                            background:linear-gradient(90deg,#f1f5f9 25%,#f8fafc 50%,#f1f5f9 75%);
                            background-size:200% 100%;animation:shimmer 1.4s infinite;"></div>
                <div style="height:11px;border-radius:4px;width:35%;
                            background:linear-gradient(90deg,#f1f5f9 25%,#f8fafc 50%,#f1f5f9 75%);
                            background-size:200% 100%;animation:shimmer 1.4s infinite;"></div>
            </div>
        </div>
    `).join('') + `<style>@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}</style>`;

    try {
        const data = await fetch(
            `/youtube/search?q=${encodeURIComponent(query)}&limit=20`
        ).then(r => r.json());

        if (!data.success || !data.videos || !data.videos.length) {
            if (data.is_educational_only) {
                container.innerHTML = `
                    <div style="max-width: 680px; margin: 40px auto; padding: 32px 28px; background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); text-align: center;">
                        <div style="width: 64px; height: 64px; margin: 0 auto 16px; background: rgba(79, 70, 229, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; color: #4f46e5;">
                            🎓
                        </div>
                        <h4 style="font-size: 1.25rem; font-weight: 700; color: #1e293b; margin-bottom: 8px;">
                            Educational Content Only
                        </h4>
                        <p style="font-size: 0.9rem; color: #64748b; line-height: 1.6; margin-bottom: 20px;">
                            ${escapeHtmlYT(data.message || 'This system is strictly for education. Searching for movies, dramas, or entertainment videos is not allowed.')}
                        </p>
                        <div style="border-top: 1px dashed #cbd5e1; padding-top: 20px; margin-top: 10px;">
                            <div style="font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 12px;">
                                Try searching for popular educational topics:
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;">
                                <button onclick="searchAndLoad('Python Programming')" style="background: #eef2ff; color: #4f46e5; border: 1px solid #c7d2fe; border-radius: 20px; padding: 6px 14px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                    🐍 Python
                                </button>
                                <button onclick="searchAndLoad('Machine Learning')" style="background: #eef2ff; color: #4f46e5; border: 1px solid #c7d2fe; border-radius: 20px; padding: 6px 14px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                    🤖 Machine Learning
                                </button>
                                <button onclick="searchAndLoad('Web Development')" style="background: #eef2ff; color: #4f46e5; border: 1px solid #c7d2fe; border-radius: 20px; padding: 6px 14px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                    💻 Web Development
                                </button>
                                <button onclick="searchAndLoad('Data Science')" style="background: #eef2ff; color: #4f46e5; border: 1px solid #c7d2fe; border-radius: 20px; padding: 6px 14px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                    📊 Data Science
                                </button>
                                <button onclick="searchAndLoad('Algorithms')" style="background: #eef2ff; color: #4f46e5; border: 1px solid #c7d2fe; border-radius: 20px; padding: 6px 14px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                    ⚡ Algorithms
                                </button>
                            </div>
                        </div>
                    </div>`;
                return;
            }

            container.innerHTML = `
                <div style="text-align:center;padding:56px 20px;">
                    <div style="font-size:3rem;margin-bottom:14px;">🔍</div>
                    <div style="font-size:1rem;font-weight:600;color:#1e293b;margin-bottom:6px;">
                        No educational results for "${escapeHtmlYT(query)}"
                    </div>
                    <div style="font-size:0.82rem;color:#94a3b8;">
                        Try different educational keywords or check spelling
                    </div>
                </div>`;
            return;
        }

        const header = `
            <div style="display:flex;align-items:center;justify-content:space-between;
                        flex-wrap:wrap;gap:10px;padding-bottom:14px;margin-bottom:6px;
                        border-bottom:1px solid #e2e8f0;">
                <div>
                    <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:3px;">Search results</div>
                    <div style="font-size:1rem;font-weight:700;color:#1e293b;">
                        "${escapeHtmlYT(query)}"
                        <span style="font-size:0.75rem;font-weight:400;
                                     color:#94a3b8;margin-left:8px;">
                            ${data.videos.length} videos found
                        </span>
                    </div>
                </div>
                <a href="/dashboard"
                   style="font-size:0.75rem;color:#94a3b8;text-decoration:none;
                          font-weight:600;padding:6px 14px;border-radius:8px;
                          border:1px solid #e2e8f0;background:white;
                          display:inline-flex;align-items:center;gap:5px;">
                    ✕ Clear search
                </a>
            </div>`;

        const avatarColors = [
            'linear-gradient(135deg,#2563eb,#7c3aed)',
            'linear-gradient(135deg,#059669,#047857)',
            'linear-gradient(135deg,#dc2626,#991b1b)',
            'linear-gradient(135deg,#d97706,#b45309)',
            'linear-gradient(135deg,#0891b2,#0e7490)',
        ];

        const cards = data.videos.map((v, i) => {
            const tj    = jsArgYT(v.title || '');
            const qj    = jsArgYT(data.query || query);
            const thumb = v.thumbnail ||
                `https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`;
            const views = v.view_count ? formatNum(v.view_count) + ' views' : '';
            const ago   = v.published_at ? timeAgo(v.published_at) : '';
            const desc  = v.description ? v.description.substring(0, 140) + '...' : '';
            const pct   = v.final_score
                ? Math.round(v.final_score * 100)
                : Math.max(60, 97 - i * 3);
            const avBg  = avatarColors[i % avatarColors.length];

            return `
            <div style="display:flex;gap:14px;padding:10px;margin-bottom:2px;
                        border-radius:12px;cursor:pointer;
                        border:1px solid transparent;transition:all 0.2s;"
                 onmouseover="this.style.background='#f8fafc';this.style.borderColor='#e2e8f0';"
                 onmouseout="this.style.background='transparent';this.style.borderColor='transparent';"
                 onclick="openVideo(${jsArgYT(v.video_id)},${tj},${qj})">

                <!-- Thumbnail -->
                <div style="position:relative;width:246px;min-width:246px;
                            height:138px;border-radius:10px;overflow:hidden;
                            background:#0f172a;flex-shrink:0;">
                    <img src="${escapeHtmlYT(thumb)}" alt=""
                         style="width:100%;height:100%;object-fit:cover;
                                display:block;transition:transform 0.35s;"
                         onerror="this.src='https://via.placeholder.com/246x138'"
                         onmouseover="this.style.transform='scale(1.05)'"
                         onmouseout="this.style.transform='scale(1)'">
                    <div style="position:absolute;inset:0;background:rgba(0,0,0,0.3);
                                display:flex;align-items:center;justify-content:center;
                                opacity:0;transition:opacity 0.2s;"
                         onmouseover="this.style.opacity='1'"
                         onmouseout="this.style.opacity='0'">
                        <div style="width:46px;height:46px;border-radius:50%;
                                    background:rgba(255,255,255,0.95);
                                    display:flex;align-items:center;
                                    justify-content:center;">
                            <svg width="16" height="16" fill="#2563eb"><polygon points="4,2 14,8 4,14"/></svg>
                        </div>
                    </div>
                    ${v.duration ? `
                    <div style="position:absolute;bottom:7px;right:7px;
                                background:rgba(0,0,0,.82);color:white;
                                padding:2px 6px;border-radius:4px;
                                font-size:11px;font-weight:700;">
                        ${escapeHtmlYT(v.duration)}
                    </div>` : ''}
                </div>

                <!-- Info -->
                <div style="flex:1;min-width:0;display:flex;
                            flex-direction:column;gap:6px;padding-top:2px;">
                    <p style="font-size:0.9rem;font-weight:600;color:#1e293b;
                              margin:0;line-height:1.45;
                              display:-webkit-box;-webkit-line-clamp:2;
                              -webkit-box-orient:vertical;overflow:hidden;">
                        ${escapeHtmlYT(v.title || 'Untitled')}
                    </p>
                    <div style="display:flex;align-items:center;gap:5px;
                                font-size:0.72rem;color:#94a3b8;">
                        ${views ? `<span>${views}</span>` : ''}
                        ${views && ago ? `<span style="width:3px;height:3px;border-radius:50%;background:#94a3b8;display:inline-block;"></span>` : ''}
                        ${ago  ? `<span>${ago}</span>` : ''}
                    </div>
                    <div style="display:flex;align-items:center;gap:7px;">
                        <div style="width:22px;height:22px;border-radius:50%;
                                    background:${avBg};display:flex;align-items:center;
                                    justify-content:center;color:white;
                                    font-size:10px;font-weight:700;flex-shrink:0;">
                            ${escapeHtmlYT((v.channel || 'Y')[0].toUpperCase())}
                        </div>
                        <span style="font-size:0.75rem;font-weight:600;color:#475569;">
                            ${escapeHtmlYT(v.channel || 'YouTube')}
                        </span>
                    </div>
                    ${desc ? `
                    <p style="font-size:0.74rem;color:#94a3b8;margin:0;
                              line-height:1.55;display:-webkit-box;
                              -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
                        ${escapeHtmlYT(desc)}
                    </p>` : ''}
                    <div style="display:flex;align-items:center;
                                gap:7px;flex-wrap:wrap;margin-top:auto;">
                        <span style="font-size:0.67rem;font-weight:600;
                                     padding:3px 9px;border-radius:20px;
                                     background:#eeedfe;color:#3c3489;">
                            AI Sorted
                        </span>
                        <span style="margin-left:auto;font-size:0.7rem;
                                     font-weight:600;color:#534ab7;">
                            ⭐ ${pct}% match
                        </span>
                    </div>
                </div>
            </div>`;
        }).join('');

        container.innerHTML = header + cards;

    } catch(e) {
        container.innerHTML = `
            <div style="text-align:center;padding:40px;color:#94a3b8;">
                <div style="font-size:2rem;margin-bottom:8px;">⚠️</div>
                <div style="font-size:0.82rem;">Search failed. Please try again.</div>
            </div>`;
    }
}


// ══════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════
function formatNotes(text) {
    return text
        .replace(/## (.*)/g, '<h6 style="font-weight:700;color:#2563eb;margin:14px 0 6px;">$1</h6>')
        .replace(/### (.*)/g, '<strong style="color:#475569;display:block;margin:8px 0 3px;">$1</strong>')
        .replace(/- (.*)/g, '<li style="margin-left:16px;font-size:0.82rem;margin-bottom:2px;">$1</li>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '<br>')
        .replace(/\n/g, '<br>');
}

function toggleDesc(el) {
    if (!el) return;
    descExpanded       = !descExpanded;
    el.style.maxHeight = descExpanded ? 'none' : '56px';
    el.style.overflow  = descExpanded ? 'visible' : 'hidden';
}

function formatNum(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000)    return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

function timeAgo(dateStr) {
    try {
        const days = Math.floor((Date.now() - new Date(dateStr)) / 86400000);
        if (days < 1)   return 'Today';
        if (days < 7)   return days + ' days ago';
        if (days < 30)  return Math.floor(days / 7)   + ' weeks ago';
        if (days < 365) return Math.floor(days / 30)  + ' months ago';
        return Math.floor(days / 365) + ' years ago';
    } catch(e) { return ''; }
}

function showToast(msg, type) {
    const colors = {
        warning: { bg:'#fffbeb', color:'#92400e', border:'#fde68a' },
        danger : { bg:'#fef2f2', color:'#991b1b', border:'#fecaca' },
        success: { bg:'#f0fdf4', color:'#166534', border:'#bbf7d0' },
    };
    const c = colors[type] || colors.success;
    const t = document.createElement('div');
    t.style.cssText = `
        position:fixed;bottom:28px;right:28px;z-index:9999;
        padding:12px 18px;border-radius:10px;font-size:0.82rem;font-weight:600;
        background:${c.bg};color:${c.color};border:1px solid ${c.border};
        box-shadow:0 6px 20px rgba(0,0,0,.12);
        animation:slideUp 0.3s ease;`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0'; t.style.transition = 'opacity 0.3s';
        setTimeout(() => t.remove(), 300);
    }, 3500);
}

function lockQuizButton() {
    unlockQuizWithTranscript();
}

function startWatchTimer() {
    unlockQuizWithTranscript();
}

function resetModalPanels() {
    ['quizContainer','quizResult'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    
    const progressWrap = document.getElementById('watchProgressWrap');
    if (progressWrap) progressWrap.style.display = 'none';

    const readyBanner  = document.getElementById('quizReadyBanner');
    const lockedBanner = document.getElementById('quizLockedBanner');
    if (readyBanner)  readyBanner.style.display  = 'none';
    if (lockedBanner) lockedBanner.style.display = 'block';

    if (window.switchAiTab) window.switchAiTab('notes');

    const nb = document.getElementById('notesBtn');
    if (nb) {
        nb.disabled  = false;
        nb.innerHTML = '<i class="fas fa-sticky-note me-1"></i><span>Notes</span>';
        nb.onclick   = () => {
            switchAiTab('notes');
            if (window.generateNotes) window.generateNotes();
        };
    }

    ['viewCount','likeCount'].forEach(id => {
        const el = document.getElementById(id); if (el) el.textContent = '—';
    });

    const rl = document.getElementById('relatedList');
    if (rl) rl.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-secondary"></div>
        </div>`;

    const nc = document.getElementById('notesContent');
    if (nc) nc.innerHTML = '';
}

function stopVideo() {
    const player = document.getElementById('ytPlayer');
    if (player) player.src = '';
    if (watchCheckTimer) { clearInterval(watchCheckTimer); watchCheckTimer = null; }
    videoWatched = false;
    currentTranscript = '';
    window.currentTranscript = '';
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('videoModal');
    if (modal) modal.addEventListener('hidden.bs.modal', stopVideo);
});