    // ============================================================
    // gemini.js — AI Quiz & Notes + Difficulty + Weak Topic Flow
    // ============================================================

    let currentQuizId    = null;
    let currentAnswers   = {};
    let currentQuestions = [];

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
            const html = data.notes
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

    // ── Generate Quiz ─────────────────────────────────────────
    async function generateQuiz() {
        const btn = document.getElementById('quizBtn');
        API.showLoading(btn, 'Generating Quiz...');

        const data = await API.post('/gemini/generate-quiz', {
            video_id   : currentVideo.id,
            video_title: currentVideo.title,
            topic      : currentVideo.topic
        });

        API.hideLoading(btn);

        if (data.success && data.quiz_id && data.quiz_id !== 'false' && data.quiz_id !== false) {
            currentQuizId    = data.quiz_id;
            currentQuestions = data.questions;
            currentAnswers   = {};

            btn.innerHTML =
                '<i class="fas fa-check me-1"></i>Quiz Ready ✅';

            // ── Open quiz in new page after 1 second ─────────
            setTimeout(() => {
                window.open(
                    `/quiz/page/${data.quiz_id}`,
                    '_blank'
                );
            }, 800);

        } else {
            API.showAlert(
                data.message || 'Quiz generation failed. Please try again.',
                'warning'
            );
            btn.innerHTML =
                '<i class="fas fa-bolt me-1"></i>Take Quiz';
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
                        ${currentVideo.topic || 'Quiz'}
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
        const safeTopic = (data.topic || '').replace(/'/g, "\\'");

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
                        ${msg.title}
                    </div>
                    <div style="font-size:0.75rem; color:#64748b;
                                margin-top:2px;">
                        ${msg.message}
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
                    <strong>${data.topic}</strong>
                    added to weak topics!
                </div>` : `
                <div class="mt-2 p-2 rounded"
                    style="background:#f0fdf4;
                            border:1px solid #bbf7d0;
                            font-size:0.75rem; color:#166534;
                            text-align:left;">
                    <i class="fas fa-check-circle me-1"></i>
                    Great job on <strong>${data.topic}</strong>! 🌟
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
                <button onclick="searchRelatedVideos('${safeTopic}')"
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
                    Find Videos for "${data.topic}"
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
                    View "${data.topic}" in Weak Topics
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

