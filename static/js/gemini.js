    // ============================================================
    // gemini.js — AI Quiz & Notes + Difficulty + Weak Topic Flow
    // ============================================================

    let currentQuizId    = null;
    let currentAnswers   = {};
    let currentQuestions = [];
    let currentQuizLevel = null;   // one level for the whole quiz: Easy / Medium / Hard
    let currentLevelBasis = '';

    // AI-generated text is inserted as plain text, never as HTML
    function escQ(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    // ── Generate Notes ────────────────────────────────────────
    async function generateNotes() {
        const btn     = document.getElementById('notesBtn');
        const section = document.getElementById('notesSection');
        const content = document.getElementById('notesContent');

        API.showLoading(btn, 'Generating Notes...');

        const data = await API.post('/gemini/generate-notes', {
            video_id   : currentVideo.id,
            video_title: currentVideo.title,
            topic      : currentVideo.topic
        });

        API.hideLoading(btn);

        if (data.success) {
            const html = escQ(data.notes)
                .replace(/## (.*)/g,
                    '<h6 class="fw-bold mt-3 mb-1" style="color:#2563eb;">$1</h6>')
                .replace(/- (.*)/g,
                    '<li style="margin-left:15px; font-size:0.83rem;">$1</li>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n\n/g, '<br>');

            content.innerHTML     = html;
            section.style.display = 'block';
            btn.innerHTML =
                '<i class="fas fa-check me-1"></i>Notes Ready ✅';
        } else {
            API.showAlert(
                data.message || 'Notes failed. Wait 1 min & retry.',
                'warning'
            );
            btn.innerHTML =
                '<i class="fas fa-sticky-note me-1"></i>Generate Notes';
        }
    }

    // ── Open Inline Quiz Modal Overlay ─────────────────────────
    function openQuizModal() {
        const modalEl = document.getElementById('quizInlineModal');
        if (!modalEl) {
            if (currentQuizId) window.open(`/quiz/page/${currentQuizId}`, '_blank');
            return;
        }
        let modalObj = bootstrap.Modal.getInstance(modalEl);
        if (!modalObj) {
            modalObj = new bootstrap.Modal(modalEl);
        }
        modalObj.show();
    }
    window.openQuizModal = openQuizModal;

    function closeQuizModal() {
        const modalEl = document.getElementById('quizInlineModal');
        if (modalEl) {
            const modalObj = bootstrap.Modal.getInstance(modalEl);
            if (modalObj) modalObj.hide();
        }
    }
    window.closeQuizModal = closeQuizModal;

    // ── Quiz level label: all three levels, this quiz's level highlighted ──
    const LEVEL_STYLE = {
        Easy  : {color: '#16a34a', soft: '#dcfce7', icon: 'fa-seedling'},
        Medium: {color: '#d97706', soft: '#fef3c7', icon: 'fa-fire'},
        Hard  : {color: '#dc2626', soft: '#fee2e2', icon: 'fa-bolt'},
    };

    function levelBar(level, basis) {
        if (!LEVEL_STYLE[level]) return '';
        const pills = Object.keys(LEVEL_STYLE).map(name => {
            const s = LEVEL_STYLE[name], on = name === level;
            return `<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:999px;
                        font-size:0.8rem;font-weight:700;border:1px solid ${on ? s.color : '#e2e8f0'};
                        background:${on ? s.color : '#ffffff'};color:${on ? '#ffffff' : '#94a3b8'};">
                        <i class="fas ${s.icon}"></i>${name}${on ? ' <i class="fas fa-check" style="font-size:0.7rem;"></i>' : ''}
                    </span>`;
        }).join('');
        return `
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;margin-bottom:16px;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
                    <span style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">Quiz level</span>
                    <div style="display:flex;gap:6px;flex-wrap:wrap;" role="img" aria-label="Quiz level: ${escQ(level)}">${pills}</div>
                </div>
                ${basis ? `<div style="font-size:0.74rem;color:#64748b;margin-top:8px;">Every question is ${escQ(level)}, chosen from ${escQ(basis)}.</div>` : ''}
            </div>`;
    }

    function levelTag(level) {
        const s = LEVEL_STYLE[level];
        return s ? `<span style="font-size:0.7rem;font-weight:700;color:${s.color};background:${s.soft};padding:3px 9px;border-radius:999px;">
                        <i class="fas ${s.icon} me-1"></i>${level}</span>` : '';
    }

    // ── Render Inline Quiz Modal Content ───────────────────────
    function renderQuizModalQuestions() {
        const modalBody = document.getElementById('quizModalBody');
        const modalFooter = document.getElementById('quizModalFooter');
        const modalTitle = document.getElementById('quizModalTitle');
        const modalSub = document.getElementById('quizModalSub');

        if (!modalBody) return;

        if (modalTitle && currentVideo) {
            modalTitle.textContent = `Interactive Quiz — ${currentVideo.topic || 'Video Topic'}`;
        }
        if (modalSub) {
            // The level itself is shown in the label at the top of the quiz
            modalSub.textContent = `${currentQuestions.length} questions`;
        }

        modalBody.innerHTML = `
            ${levelBar(currentQuizLevel, currentLevelBasis)}
            <div id="modalQuizContainer">
                ${currentQuestions.map((q, i) => `
                    <div class="quiz-modal-qitem mb-4 p-3" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="badge bg-primary text-white fw-bold">Question ${i + 1} of ${currentQuestions.length}</span>
                            ${levelTag(currentQuizLevel)}
                        </div>
                        <h6 class="fw-bold text-dark mb-3" style="font-size: 0.95rem; line-height:1.5;">${escQ(q.question)}</h6>
                        <div class="quiz-modal-options d-flex flex-column gap-2">
                            ${Object.entries(q.options).map(([key, val]) => `
                                <div class="quiz-modal-opt-card p-3 rounded-3 border d-flex align-items-center gap-3 ${currentAnswers[i] === key ? 'border-primary bg-light' : 'border-slate-200'}"
                                     style="cursor: pointer; transition: all 0.2s; background: ${currentAnswers[i] === key ? '#eff6ff' : '#ffffff'}; border-color: ${currentAnswers[i] === key ? '#3b82f6' : '#cbd5e1'} !important;"
                                     onclick="selectModalOption(${i}, '${key}', this)">
                                    <div class="opt-key-circle" style="width:28px; height:28px; border-radius:50%; background:${currentAnswers[i] === key ? '#2563eb' : '#f1f5f9'}; color:${currentAnswers[i] === key ? '#fff' : '#64748b'}; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.8rem;">
                                        ${key}
                                    </div>
                                    <div class="opt-val-text" style="font-size: 0.88rem; color:#1e293b; font-weight: 500;">
                                        ${escQ(val)}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        if (modalFooter) {
            modalFooter.innerHTML = `
                <button type="button" class="btn btn-outline-secondary px-4 fw-semibold" onclick="closeQuizModal()">Cancel</button>
                <button type="button" class="btn btn-primary px-4 fw-bold shadow-sm" onclick="submitModalQuiz()">
                    <i class="fas fa-paper-plane me-1"></i> Submit Quiz ✓
                </button>
            `;
        }
    }

    function selectModalOption(qIndex, key, el) {
        currentAnswers[qIndex] = key;
        const qContainer = el.closest('.quiz-modal-qitem');
        qContainer.querySelectorAll('.quiz-modal-opt-card').forEach(card => {
            card.style.background = '#ffffff';
            card.style.borderColor = '#cbd5e1';
            const circle = card.querySelector('.opt-key-circle');
            if (circle) {
                circle.style.background = '#f1f5f9';
                circle.style.color = '#64748b';
            }
        });
        el.style.background = '#eff6ff';
        el.style.borderColor = '#3b82f6';
        const circle = el.querySelector('.opt-key-circle');
        if (circle) {
            circle.style.background = '#2563eb';
            circle.style.color = '#ffffff';
        }
    }
    window.selectModalOption = selectModalOption;

    async function submitModalQuiz() {
        if (Object.keys(currentAnswers).length !== currentQuestions.length) {
            alert(`Please answer all ${currentQuestions.length} questions before submitting!`);
            return;
        }

        const modalBody = document.getElementById('quizModalBody');
        const modalFooter = document.getElementById('quizModalFooter');

        if (modalBody) {
            modalBody.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary mb-3" style="width:3rem; height:3rem;"></div>
                    <h5 class="fw-bold">Evaluating Quiz Answers...</h5>
                    <p class="text-muted">Updating your learning curve mastery level</p>
                </div>
            `;
        }

        try {
            const data = await API.post('/gemini/submit-quiz', {
                quiz_id: currentQuizId,
                answers: currentAnswers,
                topic  : currentVideo.topic
            });

            if (data.success) {
                const percentage = data.percentage || 0;
                const isPass = percentage >= 60;

                if (modalBody) {
                    modalBody.innerHTML = `
                        <div class="text-center p-4 mb-4 rounded-3" style="background:${isPass ? '#f0fdf4' : '#fef2f2'}; border: 1px solid ${isPass ? '#bbf7d0' : '#fecaca'};">
                            <div style="font-size: 3rem; margin-bottom: 8px;">${isPass ? '🎉' : '📚'}</div>
                            <h3 class="fw-bold mb-1" style="color:${isPass ? '#166534' : '#991b1b'};">Scored ${percentage}%</h3>
                            <p class="mb-2 fw-semibold" style="color:${isPass ? '#15803d' : '#b91c1c'};">${data.score} out of ${data.total} Correct</p>
                            <small class="d-block" style="color:#64748b;">${escQ((data.difficulty_msg && data.difficulty_msg.message) || ('Next quiz level: ' + (data.new_level || 'Medium')))}</small>
                        </div>

                        <h6 class="fw-bold mb-3">Question Breakdown & Explanations:</h6>
                        <div class="d-flex flex-column gap-3">
                            ${(data.results || []).map((res, i) => `
                                <div class="p-3 rounded-3 border" style="background: #ffffff; border-color: ${res.is_correct ? '#bbf7d0' : '#fecaca'} !important;">
                                    <div class="d-flex align-items-center justify-content-between mb-2">
                                        <span class="fw-bold" style="font-size:0.88rem; color:#1e293b;">Q${i+1}. ${escQ(res.question)}</span>
                                        <span class="badge ${res.is_correct ? 'bg-success' : 'bg-danger'}">${res.is_correct ? 'Correct ✓' : 'Incorrect ✗'}</span>
                                    </div>
                                    <div class="small mb-2">
                                        Your Answer: <strong class="${res.is_correct ? 'text-success' : 'text-danger'}">${res.user_answer || 'None'}</strong> 
                                        ${!res.is_correct ? `| Correct: <strong class="text-success">${res.correct}</strong>` : ''}
                                    </div>
                                    ${res.explanation ? `<div class="p-2 rounded bg-light small text-muted border-start border-3 border-info">${escQ(res.explanation)}</div>` : ''}
                                    ${res.evidence ? `<div class="small mt-2" style="color:#475569;"><i class="fas fa-quote-left me-1" style="color:#94a3b8;"></i>From the video: <em>"${escQ(res.evidence)}"</em></div>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    `;
                }

                if (modalFooter) {
                    modalFooter.innerHTML = `
                        <button type="button" class="btn btn-outline-secondary px-4 fw-semibold" onclick="closeQuizModal()">Close</button>
                        <button type="button" class="btn btn-success px-4 fw-bold" onclick="currentAnswers={}; renderQuizModalQuestions();">
                            <i class="fas fa-redo me-1"></i> Retake Quiz
                        </button>
                    `;
                }
            } else {
                alert(data.message || 'Submission error');
                renderQuizModalQuestions();
            }
        } catch(e) {
            alert('Failed to submit quiz. Please try again.');
            renderQuizModalQuestions();
        }
    }
    window.submitModalQuiz = submitModalQuiz;

    // ── Generate Quiz & Open Inline Modal ─────────────────────
    async function generateQuiz() {
        if (!currentVideo) return;

        openQuizModal();

        const modalBody = document.getElementById('quizModalBody');
        const modalFooter = document.getElementById('quizModalFooter');

        // If quiz is already ready, render directly in modal
        if (currentQuestions && currentQuestions.length > 0 && currentQuizId) {
            renderQuizModalQuestions();
            return;
        }

        // Display Loading State in Modal
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary mb-3" style="width:3rem; height:3rem;"></div>
                    <h5 class="fw-bold text-dark mb-1">Making your quiz...</h5>
                    <p class="text-muted small">Writing questions from what is said in the video. This can take up to a minute.</p>
                </div>
            `;
        }
        if (modalFooter) {
            modalFooter.innerHTML = `<button type="button" class="btn btn-secondary px-4" onclick="closeQuizModal()">Cancel</button>`;
        }

        const btn = document.getElementById('quizBtn');
        API.showLoading(btn, 'Generating Quiz...');

        try {
            // The server fetches the transcript itself; only identify the video here
            const data = await API.post('/gemini/generate-quiz', {
                video_id   : currentVideo.id,
                video_title: currentVideo.title,
                topic      : currentVideo.topic
            });

            API.hideLoading(btn);

            if (data.success && data.quiz_id) {
                currentQuizId    = data.quiz_id;
                currentQuestions = data.questions;
                currentAnswers   = {};
                currentQuizLevel = data.difficulty || null;
                currentLevelBasis = data.difficulty_basis || '';

                if (btn) btn.innerHTML = '<i class="fas fa-check me-1"></i>Quiz Ready ✅';

                renderQuizModalQuestions();
            } else {
                if (modalBody) {
                    modalBody.innerHTML = `
                        <div class="alert ${data.transcript_unavailable ? 'alert-secondary' : 'alert-warning'} text-center my-4">
                            <i class="fas ${data.transcript_unavailable ? 'fa-closed-captioning' : 'fa-exclamation-triangle'} fa-2x mb-2 d-block"></i>
                            <h6 class="fw-bold">${data.blocked ? "Couldn't reach this video's captions" : data.transcript_unavailable ? 'No transcript for this video' : "We couldn't make the quiz"}</h6>
                            <div class="small">${escQ(data.message || 'Quiz generation failed.')}</div>
                        </div>
                    `;
                }
                if (btn) btn.innerHTML = '<i class="fas fa-bolt me-1"></i>Take Quiz';
            }
        } catch (err) {
            API.hideLoading(btn);
            if (btn) btn.innerHTML = '<i class="fas fa-bolt me-1"></i>Take Quiz';
            if (modalBody) {
                modalBody.innerHTML = `
                    <div class="alert alert-danger text-center my-4">
                        <h6>Quiz generation error. Please check your connection and try again.</h6>
                    </div>
                `;
            }
        }
    }
    // ── Render Quiz ───────────────────────────────────────────
    function renderQuiz(questions, difficulty, attempts, lastScore) {
        document.getElementById('quizPlaceholder').style.display = 'none';
        document.getElementById('quizResult').style.display      = 'none';

        const container = document.getElementById('quizContainer');
        container.style.display = 'block';

        const diffStyles = {
            'Easy'  : { bg:'#f0fdf4', color:'#059669',
                        border:'#bbf7d0', icon:'🟢' },
            'Medium': { bg:'#fffbeb', color:'#d97706',
                        border:'#fde68a', icon:'🟡' },
            'Hard'  : { bg:'#fef2f2', color:'#dc2626',
                        border:'#fecaca', icon:'🔴' }
        };

        const style = diffStyles[difficulty] || diffStyles['Medium'];

        container.innerHTML = `
            <div class="p-3 border-bottom">
                <div class="d-flex justify-content-between
                            align-items-center mb-1">
                    <h6 class="fw-bold mb-0"
                        style="font-size:0.85rem;">
                        <i class="fas fa-brain me-1"
                        style="color:#2563eb;"></i>
                        ${escQ(currentVideo.topic || 'Quiz')}
                    </h6>
                    <span style="background:${style.bg};
                                color:${style.color};
                                border:1px solid ${style.border};
                                padding:3px 10px;
                                border-radius:12px;
                                font-size:0.72rem;
                                font-weight:700;">
                        ${style.icon} ${difficulty}
                    </span>
                </div>
                <small style="color:#94a3b8;">
                    ${questions.length} questions
                    ${attempts > 0 ?
                        `• Attempt #${attempts + 1}` :
                        '• First attempt'}
                    ${lastScore > 0 ? `• Last: ${lastScore}%` : ''}
                </small>
            </div>
            <div class="p-3">
                ${questions.map((q, i) => `
                    <div class="quiz-question-item">
                        <p class="fw-semibold mb-2"
                        style="font-size:0.84rem; color:#1e293b;">
                            Q${i+1}. ${q.question}
                        </p>
                        ${Object.entries(q.options).map(([key, val]) => `
                            <div class="quiz-option"
                                id="qopt-${i}-${key}"
                                onclick="selectQuizOption(
                                    ${i},'${key}',this)">
                                <strong>${key}.</strong> ${val}
                            </div>
                        `).join('')}
                    </div>
                `).join('')}
                <button class="btn btn-primary w-100 mt-2 fw-semibold"
                        style="font-size:0.85rem;"
                        onclick="submitVideoQuiz()">
                    <i class="fas fa-paper-plane me-1"></i>
                    Submit Quiz
                </button>
            </div>
        `;
    }

    // ── Select Option ─────────────────────────────────────────
    function selectQuizOption(qIndex, option, el) {
        currentAnswers[qIndex] = option;
        el.closest('.quiz-question-item')
        .querySelectorAll('.quiz-option')
        .forEach(o => o.classList.remove('selected'));
        el.classList.add('selected');
    }

    // ── Submit Quiz ───────────────────────────────────────────
    async function submitVideoQuiz() {
        if (Object.keys(currentAnswers).length !== currentQuestions.length) {
            alert(
                `Please answer all ${currentQuestions.length} questions!`
            );
            return;
        }

        const data = await API.post('/gemini/submit-quiz', {
            quiz_id: currentQuizId,
            answers: currentAnswers,
            topic  : currentVideo.topic
        });

        if (data.success) {
            renderQuizResult(data);
        } else {
            API.showAlert('Submission failed. Try again.', 'danger');
        }
    }

    // ── Render Result ─────────────────────────────────────────
    function renderQuizResult(data) {
        document.getElementById('quizContainer').style.display = 'none';

        const result = document.getElementById('quizResult');
        result.style.display = 'block';

        const emoji = data.percentage >= 70 ? '🎉' :
                    data.percentage >= 40 ? '😊' : '😔';
        const color = data.percentage >= 70 ? '#059669' :
                    data.percentage >= 40 ? '#d97706' : '#dc2626';
        const bg    = data.percentage >= 70 ? '#f0fdf4' :
                    data.percentage >= 40 ? '#fffbeb' : '#fef2f2';

        const diffStyles = {
            'Easy'  : { icon:'🟢', color:'#059669' },
            'Medium': { icon:'🟡', color:'#d97706' },
            'Hard'  : { icon:'🔴', color:'#dc2626' }
        };

        const newDiff   = data.new_difficulty || 'Medium';
        const diffStyle = diffStyles[newDiff]  || diffStyles['Medium'];
        const msg       = data.difficulty_msg  || {};

        // Escape topic for safe HTML use
        const safeTopic = escQ(JSON.stringify(data.topic || ''));   // a JS string inside onclick="..."

        result.innerHTML = `
            <!-- Score Section -->
            <div class="text-center p-3 border-bottom">
                <div style="font-size:2.5rem;">${emoji}</div>
                <h4 class="fw-bold mt-2 mb-0"
                    style="color:${color}; font-size:1.8rem;">
                    ${data.score}/${data.total}
                </h4>
                <p style="color:#64748b; font-size:0.82rem;
                        margin:4px 0 0;">
                    ${data.percentage}% Score
                </p>

                <!-- Difficulty Change -->
                ${msg.title ? `
                <div class="mt-3 p-3 rounded-3"
                    style="background:${bg};
                            border:1px solid ${color}22;
                            text-align:left;">
                    <div style="font-size:1.2rem; margin-bottom:4px;">
                        ${msg.icon}
                    </div>
                    <div style="font-size:0.82rem; font-weight:700;
                                color:#1e293b;">
                        ${escQ(msg.title)}
                    </div>
                    <div style="font-size:0.75rem; color:#64748b;
                                margin-top:2px;">
                        ${escQ(msg.message)}
                    </div>
                    <div class="mt-2 pt-2"
                        style="border-top:1px solid ${color}22;">
                        <span style="font-size:0.72rem; color:#94a3b8;">
                            Next quiz level:
                        </span>
                        <span style="font-size:0.78rem; font-weight:700;
                                    color:${diffStyle.color};">
                            ${diffStyle.icon} ${newDiff}
                        </span>
                    </div>
                </div>` : ''}

                <!-- Weak/Strong Alert -->
                ${data.is_weak ? `
                <div class="mt-2 p-2 rounded"
                    style="background:#fffbeb;
                            border:1px solid #fde68a;
                            font-size:0.75rem; color:#92400e;
                            text-align:left;">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    <strong>${escQ(data.topic)}</strong>
                    added to weak topics!
                </div>` : `
                <div class="mt-2 p-2 rounded"
                    style="background:#f0fdf4;
                            border:1px solid #bbf7d0;
                            font-size:0.75rem; color:#166534;
                            text-align:left;">
                    <i class="fas fa-check-circle me-1"></i>
                    Great job on <strong>${escQ(data.topic)}</strong>! 🌟
                </div>`}
            </div>

            <!-- Answers Review -->
            <div class="p-3"
                style="max-height:260px; overflow-y:auto;">
                ${data.results.map((r, i) => `
                <div class="p-2 mb-2 rounded"
                    style="background:${r.is_correct ?
                        'rgba(5,150,105,0.08)' :
                        'rgba(220,38,38,0.08)'};
                            border:1px solid ${r.is_correct ?
                        '#bbf7d0' : '#fecaca'};">
                    <small class="fw-semibold d-block"
                        style="color:#1e293b; font-size:0.78rem;">
                        Q${i+1}. ${r.question}
                    </small>
                    <small style="color:#64748b;">
                        Your: <strong>${r.user_answer || '?'}</strong> |
                        Correct: <strong>${r.correct}</strong>
                        ${r.is_correct ? '✅' : '❌'}
                    </small>
                    ${r.explanation ? `
                    <small class="d-block mt-1"
                        style="color:#94a3b8; font-size:0.72rem;">
                        💡 ${r.explanation}
                    </small>` : ''}
                </div>`).join('')}
            </div>

            <!-- Action Buttons -->
            <div class="p-3 pt-0"
                style="display:flex; flex-direction:column; gap:8px;">

                ${data.is_weak && data.related_search ? `
                <!-- Find Related Videos -->
                <button onclick="searchRelatedVideos(${safeTopic})"
                        style="width:100%; padding:10px;
                            background:linear-gradient(
                                135deg,#fef9c3,#fef08a);
                            color:#92400e;
                            border:1px solid #fde68a;
                            border-radius:8px;
                            font-size:0.82rem; font-weight:700;
                            cursor:pointer; display:flex;
                            align-items:center;
                            justify-content:center; gap:6px;">
                    <i class="fas fa-search"></i>
                    Find Videos for "${escQ(data.topic)}"
                </button>

                <!-- View in Weak Topics Page -->
                <a href="/weak-topics"
                style="width:100%; padding:10px;
                        background:#fef2f2;
                        color:#dc2626;
                        border:1px solid #fecaca;
                        border-radius:8px;
                        font-size:0.82rem; font-weight:700;
                        text-decoration:none; display:flex;
                        align-items:center;
                        justify-content:center; gap:6px;">
                    <i class="fas fa-exclamation-triangle"></i>
                    View "${escQ(data.topic)}" in Weak Topics
                </a>` : ''}

                <!-- AI Recommendations -->
                <button onclick="getAIRecommendations()"
                        style="width:100%; padding:10px;
                            background:#eff6ff; color:#2563eb;
                            border:1px solid #bfdbfe;
                            border-radius:8px;
                            font-size:0.82rem; font-weight:700;
                            cursor:pointer; display:flex;
                            align-items:center;
                            justify-content:center; gap:6px;">
                    <i class="fas fa-robot"></i>
                    Get AI Recommendations
                </button>
            </div>
        `;
    }

    // ── Search related videos for weak topic ─────────────────
    function searchRelatedVideos(topic) {
        // Close modal
        const modal = bootstrap.Modal.getInstance(
            document.getElementById('videoModal')
        );
        if (modal) modal.hide();

        // Redirect to dashboard search
        setTimeout(() => {
            window.location.href =
                `/dashboard?search=${encodeURIComponent(topic)}`;
        }, 400);
    }

    // ── Get AI Recommendations & close modal ─────────────────
    function getAIRecommendations() {
        loadRecommendations();
        const modal = bootstrap.Modal.getInstance(
            document.getElementById('videoModal')
        );
        if (modal) modal.hide();
    }

