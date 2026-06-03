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
    currentVideo      = { id: videoId, title: title, topic: topic };
    videoWatched      = false;
    descExpanded      = false;
    currentTranscript = '';

    if (watchCheckTimer) {
        clearInterval(watchCheckTimer);
        watchCheckTimer = null;
    }

    // ── Load iframe ───────────────────────────────────────
    const player = document.getElementById('ytPlayer');
    if (player) {
        player.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&enablejsapi=1`;
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

    // ── Load details, related, transcript ─────────────────
    loadVideoDetails(videoId, topic);
    loadRelatedVideos(topic);
    fetchTranscript(videoId);

    // ── Mark as watched ───────────────────────────────────
    try {
        await (_api.post || API.post)('/youtube/watched', {
            video_id: videoId,
            title   : title,
            topic   : topic
        });
    } catch(e) {}

    startWatchTimer();
}


// ══════════════════════════════════════════════════════════
//  FETCH TRANSCRIPT FROM YOUTUBE
// ══════════════════════════════════════════════════════════
async function fetchTranscript(videoId) {
    const srcEl = document.getElementById('notesSource');

    try {
        // Try backend transcript endpoint
        const data = await fetch(`/youtube/transcript?video_id=${videoId}`)
            .then(r => r.json());

        if (data.success && data.transcript && data.transcript.trim().length > 100) {
            currentTranscript = data.transcript;
            console.log('✅ Transcript loaded:', currentTranscript.length, 'chars');

            // Show transcript indicator
            if (srcEl) {
                srcEl.textContent = '📄 From Transcript';
                srcEl.style.background = '#f0fdf4';
                srcEl.style.color = '#059669';
            }

            // Unlock quiz immediately if transcript available
            unlockQuizWithTranscript();
            return;
        }
    } catch(e) {
        console.log('Transcript API not available, using title-based generation');
    }

    // Fallback — use video title
    currentTranscript = '';
    if (srcEl) {
        srcEl.textContent = '📝 From Video Title';
        srcEl.style.background = '#eff6ff';
        srcEl.style.color = '#2563eb';
    }
}


// ══════════════════════════════════════════════════════════
//  UNLOCK QUIZ (transcript available)
// ══════════════════════════════════════════════════════════
function unlockQuizWithTranscript() {
    const btn       = document.getElementById('quizBtn');
    const lockIcon  = document.getElementById('quizLockIcon');
    const btnLabel  = document.getElementById('quizBtnLabel');

    if (!btn) return;

    btn.disabled = false;
    if (lockIcon) lockIcon.className = 'fas fa-clipboard-check me-1';
    if (btnLabel) btnLabel.textContent = 'Generate Quiz';
    btn.style.opacity = '1';
    btn.style.cursor  = 'pointer';
    btn.onclick = generateQuiz;

    // Update quiz placeholder
    const placeholder = document.getElementById('quizPlaceholder');
    if (placeholder) {
        placeholder.innerHTML = `
            <div style="font-size:1.4rem;margin-bottom:8px;">📝</div>
            <div style="font-size:0.74rem;font-weight:700;color:#059669;margin-bottom:4px;">
                Quiz Ready!
            </div>
            <div style="font-size:0.65rem;color:#94a3b8;margin-bottom:12px;">
                Generated from video transcript
            </div>
            <button onclick="generateQuiz()"
                    style="background:linear-gradient(135deg,#059669,#047857);
                           color:white;border:none;padding:8px 16px;
                           border-radius:8px;font-size:0.75rem;font-weight:700;
                           cursor:pointer;font-family:inherit;">
                <i class="fas fa-play me-1"></i>Start Quiz
            </button>`;
    }
}


// ══════════════════════════════════════════════════════════
//  GENERATE NOTES (transcript-based)
// ══════════════════════════════════════════════════════════
async function generateNotes() {
    const btn     = document.getElementById('notesBtn');
    const section = document.getElementById('notesSection');
    const content = document.getElementById('notesContent');
    const srcEl   = document.getElementById('notesSource');

    if (!btn) return;

    // Loading state
    const orig = btn.innerHTML;
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';

    try {
        const payload = {
            video_id   : currentVideo.id,
            video_title: currentVideo.title,
            topic      : currentVideo.topic,
        };

        // Add transcript if available
        if (currentTranscript && currentTranscript.length > 100) {
            payload.transcript = currentTranscript.substring(0, 4000);
            if (srcEl) srcEl.textContent = '📄 From Transcript';
        } else {
            if (srcEl) srcEl.textContent = '📝 From Video Title';
        }

        const data = await fetch('/gemini/generate-notes', {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify(payload)
        }).then(r => r.json());

        if (data.success) {
            // Format notes
            const html = formatNotes(data.notes);
            content.innerHTML     = html;
            section.style.display = 'block';
            btn.innerHTML = '<i class="fas fa-check me-1"></i>Notes Ready ✅';
            btn.disabled  = false;

            // Scroll into view
            section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            btn.innerHTML = orig;
            btn.disabled  = false;
            showToast('Notes failed. Please try again.', 'warning');
        }
    } catch(e) {
        btn.innerHTML = orig;
        btn.disabled  = false;
        showToast('Error generating notes.', 'danger');
    }
}


// ══════════════════════════════════════════════════════════
//  GENERATE QUIZ (transcript-based)
// ══════════════════════════════════════════════════════════
async function generateQuiz() {
    const btn       = document.getElementById('quizBtn');
    const lockIcon  = document.getElementById('quizLockIcon');
    const btnLabel  = document.getElementById('quizBtnLabel');

    if (!btn) return;

    // Loading
    btn.disabled = true;
    if (lockIcon) lockIcon.className = 'fas fa-spinner fa-spin me-1';
    if (btnLabel) btnLabel.textContent = 'Generating Quiz...';

    try {
        const payload = {
            video_id   : currentVideo.id,
            video_title: currentVideo.title,
            topic      : currentVideo.topic,
        };

        // Transcript-based quiz
        if (currentTranscript && currentTranscript.length > 100) {
            payload.transcript = currentTranscript.substring(0, 4000);
        }

        const data = await fetch('/gemini/generate-quiz', {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify(payload)
        }).then(r => r.json());

        if (data.success) {
            btn.disabled = false;
            if (lockIcon) lockIcon.className = 'fas fa-check me-1';
            if (btnLabel) btnLabel.textContent = 'Quiz Ready ✅';

            // Show quiz inline in modal
            renderQuizInModal(data);

            // Also open in new tab
            setTimeout(() => {
                window.open(`/quiz/page/${data.quiz_id}`, '_blank');
            }, 600);
        } else {
            btn.disabled = false;
            if (lockIcon) lockIcon.className = 'fas fa-clipboard-check me-1';
            if (btnLabel) btnLabel.textContent = 'Retry Quiz';
            showToast(data.message || 'Quiz failed. Try again.', 'warning');
        }
    } catch(e) {
        btn.disabled = false;
        if (lockIcon) lockIcon.className = 'fas fa-clipboard-check me-1';
        if (btnLabel) btnLabel.textContent = 'Retry Quiz';
        showToast('Error generating quiz.', 'danger');
    }
}


// ══════════════════════════════════════════════════════════
//  RENDER QUIZ INLINE IN MODAL (below related videos)
// ══════════════════════════════════════════════════════════
function renderQuizInModal(data) {
    const placeholder = document.getElementById('quizPlaceholder');
    const container   = document.getElementById('quizContainer');

    if (placeholder) placeholder.style.display = 'none';
    if (!container)  return;

    container.style.display = 'block';

    const diff = data.difficulty || 'Medium';
    const diffConfig = {
        Easy  : { icon: '🟢', color: '#059669', bg: '#f0fdf4', border: '#bbf7d0' },
        Medium: { icon: '🟡', color: '#d97706', bg: '#fffbeb', border: '#fde68a' },
        Hard  : { icon: '🔴', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
    };
    const dc = diffConfig[diff] || diffConfig.Medium;
    const source = currentTranscript ? '📄 Transcript-based' : '📝 Title-based';

    container.innerHTML = `
        <!-- Quiz Header -->
        <div style="background:linear-gradient(135deg,#0f172a,#1e1b4b);
                    color:white;padding:10px 14px;border-radius:10px 10px 0 0;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-size:0.78rem;font-weight:700;">
                    <i class="fas fa-brain me-2"></i>${currentVideo.topic || 'Quiz'}
                </div>
                <span style="background:${dc.bg};color:${dc.color};
                             padding:2px 9px;border-radius:9px;
                             font-size:0.66rem;font-weight:700;">
                    ${dc.icon} ${diff}
                </span>
            </div>
            <div style="font-size:0.63rem;color:rgba(255,255,255,0.45);margin-top:3px;">
                ${data.total} questions • ${source}
                ${data.attempts > 0 ? ` • Attempt #${data.attempts + 1}` : ' • First attempt'}
            </div>
        </div>

        <!-- Questions -->
        <div style="max-height:320px;overflow-y:auto;padding:10px 12px;" id="quizQWrap">
            ${(data.questions || []).map((q, i) => `
                <div style="margin-bottom:14px;padding-bottom:12px;
                            border-bottom:1px solid #f1f5f9;">
                    <p style="font-size:0.79rem;font-weight:600;
                              color:#1e293b;margin:0 0 7px;line-height:1.45;">
                        Q${i+1}. ${q.question}
                    </p>
                    ${Object.entries(q.options || {}).map(([key, val]) => `
                        <div id="opt_${i}_${key}"
                             onclick="pickOpt(${i},'${key}',this)"
                             style="display:flex;align-items:center;gap:7px;
                                    padding:6px 10px;border-radius:7px;
                                    border:1.5px solid #f1f5f9;
                                    cursor:pointer;margin-bottom:4px;
                                    transition:all 0.18s;background:white;
                                    font-size:0.76rem;color:#475569;">
                            <span style="width:20px;height:20px;border-radius:50%;
                                         border:1.5px solid #cbd5e1;
                                         display:flex;align-items:center;
                                         justify-content:center;
                                         font-size:0.62rem;font-weight:700;
                                         flex-shrink:0;color:#64748b;"
                                  id="optBadge_${i}_${key}">
                                ${key}
                            </span>
                            ${val}
                        </div>
                    `).join('')}
                </div>
            `).join('')}

            <button onclick="submitInlineQuiz()"
                    style="width:100%;padding:10px;
                           background:linear-gradient(135deg,#2563eb,#7c3aed);
                           color:white;border:none;border-radius:9px;
                           font-size:0.8rem;font-weight:700;cursor:pointer;
                           font-family:inherit;margin-top:4px;">
                <i class="fas fa-paper-plane me-1"></i>Submit Quiz
            </button>

            <a href="/quiz/page/${data.quiz_id}" target="_blank"
               style="display:block;text-align:center;margin-top:8px;
                      font-size:0.7rem;color:#7c3aed;font-weight:600;
                      text-decoration:none;">
                <i class="fas fa-external-link-alt me-1"></i>Open full quiz page
            </a>
        </div>`;

    // Store quiz data for submission
    window._inlineQuiz = {
        quiz_id  : data.quiz_id,
        questions: data.questions || [],
        answers  : {},
        topic    : currentVideo.topic
    };

    // Scroll to quiz section
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


// ── Pick option in inline quiz ────────────────────────────
function pickOpt(qIdx, key, el) {
    if (!window._inlineQuiz) return;
    window._inlineQuiz.answers[qIdx] = key;

    // Update visuals for this question
    const q = window._inlineQuiz.questions[qIdx];
    if (!q) return;

    Object.keys(q.options || {}).forEach(k => {
        const optEl   = document.getElementById(`opt_${qIdx}_${k}`);
        const badgeEl = document.getElementById(`optBadge_${qIdx}_${k}`);
        if (!optEl) return;

        if (k === key) {
            optEl.style.borderColor   = '#2563eb';
            optEl.style.background    = '#eff6ff';
            optEl.style.color         = '#1e40af';
            if (badgeEl) {
                badgeEl.style.background  = '#2563eb';
                badgeEl.style.borderColor = '#2563eb';
                badgeEl.style.color       = 'white';
            }
        } else {
            optEl.style.borderColor   = '#f1f5f9';
            optEl.style.background    = 'white';
            optEl.style.color         = '#475569';
            if (badgeEl) {
                badgeEl.style.background  = 'transparent';
                badgeEl.style.borderColor = '#cbd5e1';
                badgeEl.style.color       = '#64748b';
            }
        }
    });
}


// ── Submit inline quiz ─────────────────────────────────────
async function submitInlineQuiz() {
    const iq = window._inlineQuiz;
    if (!iq) return;

    const totalQ = iq.questions.length;
    const answered = Object.keys(iq.answers).length;

    if (answered < totalQ) {
        showToast(`Please answer all ${totalQ} questions! (${answered}/${totalQ} done)`, 'warning');
        return;
    }

    const container = document.getElementById('quizContainer');
    if (container) {
        container.innerHTML = `
            <div style="text-align:center;padding:24px;">
                <div class="spinner-border" style="width:1.6rem;height:1.6rem;color:#7c3aed;"></div>
                <div style="font-size:0.76rem;color:#94a3b8;margin-top:8px;">Submitting...</div>
            </div>`;
    }

    try {
        const data = await fetch('/gemini/submit-quiz', {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify({
                quiz_id: iq.quiz_id,
                answers: iq.answers,
                topic  : iq.topic
            })
        }).then(r => r.json());

        if (data.success) {
            renderInlineResult(data);
        } else {
            showToast('Submission failed. Try again.', 'danger');
        }
    } catch(e) {
        showToast('Error submitting quiz.', 'danger');
    }
}


// ── Render inline quiz result ─────────────────────────────
function renderInlineResult(data) {
    const container = document.getElementById('quizContainer');
    if (!container) return;

    const pct   = data.percentage || 0;
    const emoji = pct >= 70 ? '🎉' : pct >= 40 ? '😊' : '😔';
    const color = pct >= 70 ? '#059669' : pct >= 40 ? '#d97706' : '#dc2626';
    const bg    = pct >= 70 ? '#f0fdf4' : pct >= 40 ? '#fffbeb' : '#fef2f2';
    const border= pct >= 70 ? '#bbf7d0' : pct >= 40 ? '#fde68a' : '#fecaca';

    const newDiff = data.new_difficulty || 'Medium';
    const diffIco = { Easy:'🟢', Medium:'🟡', Hard:'🔴' };
    const safeTopic = (data.topic || '').replace(/'/g, "\\'");

    container.innerHTML = `
        <div style="padding:16px 14px;">

            <!-- Score circle -->
            <div style="text-align:center;margin-bottom:14px;">
                <div style="font-size:2.2rem;margin-bottom:6px;">${emoji}</div>
                <div style="font-size:2rem;font-weight:900;color:${color};line-height:1;">
                    ${data.score}/${data.total}
                </div>
                <div style="font-size:0.78rem;color:#64748b;margin-top:3px;">
                    ${pct}% — ${pct >= 70 ? 'Excellent!' : pct >= 40 ? 'Good Job!' : 'Keep Practicing!'}
                </div>
            </div>

            <!-- Status cards -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
                <div style="background:${bg};border:1px solid ${border};
                            border-radius:8px;padding:9px;text-align:center;">
                    <div style="font-size:0.62rem;color:#94a3b8;margin-bottom:2px;">RESULT</div>
                    <div style="font-size:0.82rem;font-weight:700;color:${color};">
                        ${data.is_weak ? '⚠️ Weak Topic' : '✅ Strong!'}
                    </div>
                </div>
                <div style="background:#faf5ff;border:1px solid #e9d5ff;
                            border-radius:8px;padding:9px;text-align:center;">
                    <div style="font-size:0.62rem;color:#94a3b8;margin-bottom:2px;">NEXT LEVEL</div>
                    <div style="font-size:0.82rem;font-weight:700;color:#7c3aed;">
                        ${diffIco[newDiff] || '🟡'} ${newDiff}
                    </div>
                </div>
            </div>

            <!-- Review answers -->
            <div style="max-height:180px;overflow-y:auto;margin-bottom:12px;">
                ${(data.results || []).map((r, i) => `
                    <div style="padding:7px 9px;border-radius:7px;margin-bottom:5px;
                                background:${r.is_correct ? 'rgba(5,150,105,0.07)' : 'rgba(220,38,38,0.07)'};
                                border:1px solid ${r.is_correct ? '#bbf7d0' : '#fecaca'};">
                        <div style="font-size:0.73rem;font-weight:600;color:#1e293b;margin-bottom:2px;">
                            Q${i+1}. ${r.question.substring(0, 60)}${r.question.length > 60 ? '...' : ''}
                        </div>
                        <div style="font-size:0.67rem;color:#64748b;">
                            You: <strong>${r.user_answer || '?'}</strong> |
                            Ans: <strong>${r.correct}</strong>
                            ${r.is_correct ? '✅' : '❌'}
                        </div>
                        ${r.explanation ? `
                        <div style="font-size:0.63rem;color:#94a3b8;margin-top:2px;">
                            💡 ${r.explanation.substring(0, 80)}${r.explanation.length > 80 ? '...' : ''}
                        </div>` : ''}
                    </div>
                `).join('')}
            </div>

            <!-- Action buttons -->
            <div style="display:flex;flex-direction:column;gap:6px;">
                ${data.is_weak ? `
                <button onclick="findVideosForTopic('${safeTopic}')"
                        style="width:100%;padding:9px;
                               background:linear-gradient(135deg,#fef9c3,#fef08a);
                               color:#92400e;border:1px solid #fde68a;
                               border-radius:8px;font-size:0.77rem;font-weight:700;
                               cursor:pointer;font-family:inherit;">
                    <i class="fas fa-search me-1"></i>Find Easier Videos for "${data.topic}"
                </button>` : `
                <button onclick="findNextLevelVideos('${safeTopic}')"
                        style="width:100%;padding:9px;
                               background:linear-gradient(135deg,#eff6ff,#faf5ff);
                               color:#2563eb;border:1px solid #bfdbfe;
                               border-radius:8px;font-size:0.77rem;font-weight:700;
                               cursor:pointer;font-family:inherit;">
                    <i class="fas fa-arrow-up me-1"></i>Find Advanced Videos
                </button>`}

                <button onclick="retakeQuiz()"
                        style="width:100%;padding:9px;
                               background:#f8fafc;color:#64748b;
                               border:1.5px solid #e2e8f0;
                               border-radius:8px;font-size:0.77rem;font-weight:700;
                               cursor:pointer;font-family:inherit;">
                    <i class="fas fa-redo me-1"></i>Retake Quiz
                </button>
            </div>
        </div>`;

    // If weak — also load simpler videos in related section
    if (data.is_weak && data.topic) {
        loadRelatedVideos(data.topic + ' simplified beginners');
    }
}


// ── Find videos after quiz ────────────────────────────────
function findVideosForTopic(topic) {
    const modal = bootstrap.Modal.getInstance(document.getElementById('videoModal'));
    if (modal) modal.hide();
    setTimeout(() => {
        window.location.href = `/dashboard?search=${encodeURIComponent(topic + ' simplified beginners')}`;
    }, 300);
}

function findNextLevelVideos(topic) {
    const modal = bootstrap.Modal.getInstance(document.getElementById('videoModal'));
    if (modal) modal.hide();
    setTimeout(() => {
        window.location.href = `/dashboard?search=${encodeURIComponent(topic + ' advanced')}`;
    }, 300);
}

function retakeQuiz() {
    if (window._inlineQuiz) {
        window._inlineQuiz.answers = {};
        generateQuiz();
    }
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
            const tj     = JSON.stringify(v.title);
            const topicJ = JSON.stringify(topic);
            const thumb  = v.thumbnail ||
                `https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`;
            const avBg   = avatarColors[i % avatarColors.length];

            return `
            <div onclick='openVideo("${v.video_id}",${tj},${topicJ})'
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
                    <img src="${thumb}"
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
                        ${v.title || 'Video'}
                    </div>
                    <div style="display:flex;align-items:center;gap:5px;">
                        <div style="width:18px;height:18px;border-radius:50%;
                                    background:${avBg};flex-shrink:0;
                                    display:flex;align-items:center;justify-content:center;
                                    color:white;font-size:0.58rem;font-weight:700;">
                            ${(v.channel || 'Y')[0].toUpperCase()}
                        </div>
                        <span style="font-size:0.64rem;color:#94a3b8;
                                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                            ${v.channel || 'YouTube'}
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
            container.innerHTML = `
                <div style="text-align:center;padding:56px 20px;">
                    <div style="font-size:3rem;margin-bottom:14px;">🔍</div>
                    <div style="font-size:1rem;font-weight:600;color:#1e293b;margin-bottom:6px;">
                        No results for "${query}"
                    </div>
                    <div style="font-size:0.82rem;color:#94a3b8;">
                        Try different keywords or check spelling
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
                        "${query}"
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
            const tj    = JSON.stringify(v.title || '');
            const qj    = JSON.stringify(data.query || query);
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
                 onclick='openVideo("${v.video_id}",${tj},${qj})'>

                <!-- Thumbnail -->
                <div style="position:relative;width:246px;min-width:246px;
                            height:138px;border-radius:10px;overflow:hidden;
                            background:#0f172a;flex-shrink:0;">
                    <img src="${thumb}" alt=""
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
                        ${v.duration}
                    </div>` : ''}
                </div>

                <!-- Info -->
                <div style="flex:1;min-width:0;display:flex;
                            flex-direction:column;gap:6px;padding-top:2px;">
                    <p style="font-size:0.9rem;font-weight:600;color:#1e293b;
                              margin:0;line-height:1.45;
                              display:-webkit-box;-webkit-line-clamp:2;
                              -webkit-box-orient:vertical;overflow:hidden;">
                        ${v.title || 'Untitled'}
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
                            ${(v.channel || 'Y')[0].toUpperCase()}
                        </div>
                        <span style="font-size:0.75rem;font-weight:600;color:#475569;">
                            ${v.channel || 'YouTube'}
                        </span>
                    </div>
                    ${desc ? `
                    <p style="font-size:0.74rem;color:#94a3b8;margin:0;
                              line-height:1.55;display:-webkit-box;
                              -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
                        ${desc}
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
    const btn      = document.getElementById('quizBtn');
    const lockIcon = document.getElementById('quizLockIcon');
    const btnLabel = document.getElementById('quizBtnLabel');
    if (!btn) return;
    btn.disabled = true;
    if (lockIcon) lockIcon.className = 'fas fa-lock me-1';
    if (btnLabel) btnLabel.textContent = 'Watch to unlock';
    btn.style.opacity = '0.55';
    btn.style.cursor  = 'not-allowed';
    btn.onclick       = null;
}

function startWatchTimer() {
    let secs = 0;
    watchCheckTimer = setInterval(() => {
        secs++;
        // After 60 seconds, auto-unlock
        if (secs >= 60 && !videoWatched) {
            clearInterval(watchCheckTimer);
            videoWatched = true;
            // Only unlock if transcript not already loaded
            if (!currentTranscript) {
                unlockQuizWithTranscript();
            }
        }
    }, 1000);
}

function resetModalPanels() {
    ['quizContainer','quizResult','notesSection'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    const ph = document.getElementById('quizPlaceholder');
    if (ph) {
        ph.style.display = 'block';
        ph.innerHTML = `
            <div style="font-size:1.5rem;margin-bottom:5px;">📝</div>
            <div style="font-size:0.72rem;font-weight:600;color:#64748b;">Auto Quiz</div>
            <div style="font-size:0.64rem;margin-top:2px;">Watch video to unlock</div>`;
    }

    const nb = document.getElementById('notesBtn');
    if (nb) {
        nb.disabled  = false;
        nb.innerHTML = '<i class="fas fa-sticky-note me-1"></i>Notes';
        nb.onclick   = generateNotes;
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
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('videoModal');
    if (modal) modal.addEventListener('hidden.bs.modal', stopVideo);
});