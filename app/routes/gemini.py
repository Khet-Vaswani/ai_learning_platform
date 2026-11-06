# ============================================================
# gemini.py — AI Quiz, Notes, Chatbot Routes
# Uses: notes_generator.py + quiz_generator.py (pipeline)
# Primary AI: Groq | Fallback: Gemini
# ============================================================

from flask import (Blueprint, request, jsonify,
                   session, render_template, redirect, url_for)
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query

import os, json, time, re, html

gemini_bp = Blueprint('gemini', __name__)

TRANSCRIPT_UNAVAILABLE = {
    'success': False,
    'transcript_unavailable': True,
    'message': ("We couldn't get a transcript for this video (it has no captions and the audio "
                "couldn't be transcribed), so we can't make a quiz for it. "
                "Quizzes and notes are only made from what is said in the video."),
}


TRANSCRIPT_BLOCKED = {
    **TRANSCRIPT_UNAVAILABLE,
    'blocked': True,
    'message': ("YouTube didn't let our server read this video's captions right now, so we can't "
                "make a quiz for it yet. Try another video, or try this one again later."),
}


def _json_body():
    """The request's JSON object, or {} for a missing or malformed body."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _server_transcript(video_id: str):
    """
    Get the video's real transcript server-side: verified cache -> YouTube captions
    -> yt-dlp subtitles -> speech-to-text. Returns (text, source), ('', 'blocked')
    when YouTube refused this server, or ('', None).
    """
    from app.ai.transcript_extractor import (
        extract_transcript_full_pipeline, is_valid_transcript, VALID_TRANSCRIPT_SOURCES)
    result = extract_transcript_full_pipeline(video_id=video_id, use_whisper=True)
    text, source = result.get('transcript', ''), result.get('source')
    if source in VALID_TRANSCRIPT_SOURCES and is_valid_transcript(text):
        return text, source
    return '', ('blocked' if result.get('blocked') else None)


def _no_transcript_response(source, what='a quiz'):
    body = TRANSCRIPT_BLOCKED if source == 'blocked' else TRANSCRIPT_UNAVAILABLE
    return jsonify({**body, 'message': body['message'].replace('a quiz', what)})

# ── Groq client ───────────────────────────────────────────
from groq import Groq
# A missing key must not stop the whole site from starting; only AI replies fail
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY')) if os.getenv('GROQ_API_KEY') else None

GROQ_MODELS = [
    'openai/gpt-oss-120b',
    'qwen/qwen3.8-27b',
    'openai/gpt-oss-20b',
]

# ── Gemini client ─────────────────────────────────────────
try:
    from google import genai
    gemini_client    = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

GEMINI_MODELS = [
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-flash-latest',
]


# ============================================================
# SHARED AI GENERATE — used by chatbot only
# (notes/quiz use their own generators)
# ============================================================
def _generate_ai(prompt: str, max_tokens: int = 1200) -> str:
    """Groq → Gemini fallback for chatbot."""
    last_error = None

    for model in (GROQ_MODELS if groq_client else []):
        try:
            resp = groq_client.chat.completions.create(
                model       = model,
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = max_tokens,
                temperature = 0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            last_error = err
            if '429' in err or 'rate' in err.lower():
                time.sleep(1); continue
            elif '401' in err or 'invalid_api_key' in err.lower():
                break
            continue

    if GEMINI_AVAILABLE:
        for model in GEMINI_MODELS:
            try:
                resp = gemini_client.models.generate_content(
                    model    = model,
                    contents = prompt
                )
                return resp.text.strip()
            except Exception as e:
                err = str(e)
                if '429' in err or 'quota' in err.lower():
                    time.sleep(3); continue
                continue

    raise Exception(f"All AI models unavailable. Last: {last_error}")


# ============================================================
# STUDENT PROGRESS CONTEXT — for the chatbot
# ============================================================
def _student_context(user_id: int) -> str:
    """
    Plain-text summary of THIS student's own learning data (profile, quiz
    scores, weak topics, next quiz levels, activity, study plan), so the
    chatbot can answer questions about their progress. Never includes
    other students' data.
    """
    from app.ai.quiz_generator import choose_quiz_level
    lines = []

    u = execute_query(
        """SELECT full_name, education_category, field_of_interest, skill_level, created_at
           FROM users WHERE id=%s""", (user_id,), fetch=True) or []
    if u:
        u = u[0]
        lines.append(f"Name: {u['full_name']}")
        lines.append(f"Education level: {u.get('education_category') or 'not set'} | "
                     f"Field: {u.get('field_of_interest') or 'not set'} | Skill level: {u.get('skill_level') or 'not set'}")

    stats = (execute_query(
        """SELECT COUNT(*) AS n, ROUND(AVG(score/total*100),1) AS avg, ROUND(MAX(score/total*100),1) AS best
           FROM video_quizzes WHERE user_id=%s AND attempted=1 AND total>0""",
        (user_id,), fetch=True) or [{}])[0]
    if stats.get('n'):
        lines.append(f"Quizzes completed: {stats['n']} | Average score: {stats['avg']}% | Best score: {stats['best']}%")
        recent = execute_query(
            """SELECT topic, ROUND(score/total*100) AS pct, score, total, difficulty, created_at
               FROM video_quizzes WHERE user_id=%s AND attempted=1 AND total>0
               ORDER BY created_at DESC LIMIT 5""", (user_id,), fetch=True) or []
        lines.append("Recent quizzes (newest first):")
        for q in recent:
            when = q['created_at'].strftime('%d %b %Y') if q.get('created_at') else ''
            lvl = f", {q['difficulty']} level" if q.get('difficulty') else ''
            lines.append(f"  - {q['topic'] or 'Quiz'}: {q['pct']}% ({q['score']}/{q['total']}{lvl}) on {when}")
        topics = execute_query(
            """SELECT topic, COUNT(*) AS n, ROUND(AVG(score/total*100)) AS avg
               FROM video_quizzes WHERE user_id=%s AND attempted=1 AND total>0 AND topic IS NOT NULL
               GROUP BY topic ORDER BY avg ASC LIMIT 8""", (user_id,), fetch=True) or []
        if topics:
            lines.append("Average score by topic (weakest first):")
            for t in topics:
                nxt = choose_quiz_level(user_id, t['topic'])['level']
                lines.append(f"  - {t['topic']}: {t['avg']}% over {t['n']} quiz(zes); next quiz on it will be {nxt}")
    else:
        lines.append("Quizzes completed: none yet")

    weak = execute_query(
        """SELECT topic, fail_count FROM weak_topics WHERE user_id=%s AND fail_count>0
           ORDER BY fail_count DESC LIMIT 6""", (user_id,), fetch=True) or []
    lines.append("Weak topics (topics with at least one quiz scored under 50%; see the averages above): " +
                 (', '.join(f"{w['topic']} (missed {w['fail_count']}x)" for w in weak) if weak else 'none'))

    watched = (execute_query("SELECT COUNT(*) AS n FROM watched_videos WHERE user_id=%s", (user_id,), fetch=True) or [{'n': 0}])[0]['n']
    week = (execute_query(
        """SELECT COALESCE(SUM(duration_min),0) AS m FROM study_sessions
           WHERE user_id=%s AND session_date >= CURDATE() - INTERVAL 6 DAY""", (user_id,), fetch=True) or [{'m': 0}])[0]['m']
    lines.append(f"Videos watched: {watched} | Study time in the last 7 days: {week} minutes")

    plans = execute_query(
        """SELECT topic, study_date, duration FROM study_schedule
           WHERE user_id=%s AND completed=0 AND study_date >= CURDATE()
           ORDER BY study_date LIMIT 5""", (user_id,), fetch=True) or []
    if plans:
        lines.append("Upcoming study plan: " + '; '.join(f"{p['topic']} on {p['study_date']} ({p['duration']} min)" for p in plans))

    return '\n'.join(lines)


def _with_progress(prompt: str, progress: str) -> str:
    """Prefix a chatbot prompt with the student's own progress data and how to use it."""
    return f"""You are the AI learning assistant inside LearnNova. You can answer general questions on any subject,
and you also know this student's own progress on the platform (below).

=== THIS STUDENT'S PROGRESS ON LEARNAI ===
{progress}
=== END OF PROGRESS DATA ===

How to use the progress data:
- Use it when the student asks about their scores, progress, weak topics, what to study next, quiz levels, or a study plan.
- Quote the numbers exactly as given. Never invent scores, topics, or dates. If something isn't in the data, say you don't have it.
- For general questions that aren't about their progress, just answer normally; you may briefly connect the answer to a weak topic if it is clearly relevant.

{prompt}"""


# ============================================================
# GENERATE NOTES
# ============================================================
@gemini_bp.route('/gemini/generate-notes', methods=['POST'])
@login_required
def generate_notes_route():
    """
    Generate AI study notes from transcript or video title.
    Frontend sends: video_id, video_title, topic, transcript (optional)
    """
    data        = _json_body()
    video_id    = str(data.get('video_id', '')).strip()
    video_title = str(data.get('video_title', '')).strip()   # stored for display only
    topic       = str(data.get('topic', '')).strip()
    user_id     = session['user_id']

    if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', video_id):
        return jsonify({'success': False, 'message': 'A valid video_id is required.'}), 400

    try:
        from app.ai.notes_generator import generate_notes, get_saved_notes

        cached = get_saved_notes(user_id, video_id)
        if cached.get('success'):
            print("✅ Notes from cache")
            return jsonify(cached)

        transcript, source = _server_transcript(video_id)
        if not transcript:
            return _no_transcript_response(source, 'notes')

        print(f"\n📝 Notes: video={video_id} | source={source} | {len(transcript.split())} words")
        return jsonify(generate_notes(
            video_id    = video_id,
            video_title = video_title,
            topic       = topic,
            user_id     = user_id,
            transcript  = transcript,
            source      = source,
        ))

    except Exception as e:
        print(f"❌ Notes route error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': "Something went wrong while making notes. Try again."})


# ============================================================
# GENERATE QUIZ
# ============================================================
@gemini_bp.route('/gemini/generate-quiz', methods=['POST'])
@login_required
def generate_quiz_route():
    """
    Generate MCQ quiz strictly from authentic YouTube video transcript.
    If transcript is unavailable, reliably extracts it via multi-layered pipeline.
    Never generates questions from titles or external knowledge.
    """
    data        = _json_body()
    video_id    = str(data.get('video_id', '')).strip()
    video_title = str(data.get('video_title', '')).strip()   # stored for display only
    topic       = str(data.get('topic', '')).strip()         # used for progress tracking only
    user_id     = session['user_id']

    if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', video_id):
        return jsonify({'success': False, 'message': 'A valid video_id is required.'}), 400

    try:
        from app.ai.quiz_generator import generate_quiz, get_saved_quiz, choose_quiz_level

        # One level for the whole quiz, from the student's past scores
        level_info = choose_quiz_level(user_id, topic)
        level      = level_info['level']

        # Reuse an unattempted quiz for this video only if it's at the same level
        saved = get_saved_quiz(user_id, video_id, level)
        if saved.get('success'):
            print(f"✅ Loaded saved {level} quiz for video {video_id}")
            return jsonify({**saved, 'difficulty_basis': level_info['basis']})

        # The transcript always comes from the server (captions or speech-to-text),
        # never from the request body, so nothing else can be passed off as one.
        transcript, source = _server_transcript(video_id)
        if not transcript:
            return _no_transcript_response(source)

        print(f"\n📋 Quiz generation: video={video_id} | source={source} | {len(transcript.split())} words")
        result = generate_quiz(
            video_id    = video_id,
            video_title = video_title,
            topic       = topic,
            user_id     = user_id,
            transcript  = transcript,
            source      = source,
            difficulty  = level,
        )
        if result.get('success'):
            result['difficulty_basis'] = level_info['basis']
        return jsonify(result)

    except Exception as e:
        print(f"❌ Quiz route error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': "Something went wrong while making the quiz. Try again."})


# ============================================================
# SUBMIT QUIZ
# ============================================================
@gemini_bp.route('/gemini/submit-quiz', methods=['POST'])
@login_required
def submit_quiz_route():
    """
    Submit quiz answers. Updates learning data.
    Frontend sends: quiz_id, answers {0: 'A', 1: 'C', ...}, topic
    """
    data    = _json_body()
    quiz_id = data.get('quiz_id')
    answers = data.get('answers', {})
    topic   = data.get('topic', '')
    user_id = session['user_id']

    if not quiz_id:
        return jsonify({'success': False, 'message': 'quiz_id required'})

    try:
        from app.ai.quiz_generator import submit_quiz

        result = submit_quiz(
            quiz_id = quiz_id,
            user_id = user_id,
            answers = answers,
            topic   = topic,
        )

        # Get post-quiz video recommendations
        if result.get('success'):
            try:
                from app.utils.notifications import create_notification
                pct = result.get('percentage', 0)
                sc = result.get('score', 0)
                tot = result.get('total', 0)
                create_notification(
                    user_id,
                    f"Quiz Completed: {topic}",
                    f"You scored {pct}% ({sc}/{tot}) on your {topic} interactive quiz! 🎉",
                    notif_type="quiz",
                    icon="fa-check-circle"
                )
            except Exception:
                pass

            try:
                video_suggestions = _get_postquiz_recommendations(
                    topic      = topic,
                    percentage = result['percentage'],
                    user_id    = user_id,
                )
                result['video_suggestions']     = video_suggestions.get('recommendations', [])
                result['suggestion_reason']     = video_suggestions.get('reason', '')
                result['suggestion_difficulty'] = video_suggestions.get('difficulty_level', '')
                result['suggestion_count']      = video_suggestions.get('count', 0)
            except Exception as e:
                print(f"⚠️ Post-quiz recs error: {e}")
                result['video_suggestions']     = []
                result['suggestion_reason']     = ''
                result['suggestion_difficulty'] = ''
                result['suggestion_count']      = 0

        return jsonify(result)

    except Exception as e:
        print(f"❌ Submit quiz error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# GET DIFFICULTY
# ============================================================
@gemini_bp.route('/gemini/get-difficulty', methods=['GET'])
@login_required
def get_difficulty():
    """Level the student's next quiz on a topic will have (Easy / Medium / Hard)."""
    from app.ai.quiz_generator import choose_quiz_level
    info = choose_quiz_level(session['user_id'], request.args.get('topic', '').strip())
    return jsonify({'success': True, 'difficulty': info['level'],
                    'average': info['average'], 'basis': info['basis']})


# ============================================================
# QUIZ PAGE — render template
# ============================================================
@gemini_bp.route('/quiz/page/<int:quiz_id>')
@login_required
def quiz_page(quiz_id):
    user_id = session['user_id']

    quiz = execute_query(
        "SELECT * FROM video_quizzes WHERE id=%s AND user_id=%s",
        (quiz_id, user_id), fetch=True
    )
    if not quiz:
        return redirect(url_for('dashboard.index'))

    q         = quiz[0]
    questions = json.loads(q['questions'])

    # The level this quiz was created at (older quizzes have none recorded)
    from app.ai.quiz_generator import DB_TO_LEVEL
    difficulty = DB_TO_LEVEL.get(q.get('difficulty') or '', None)

    curve = execute_query(
        "SELECT curve_stage FROM learning_curves WHERE user_id=%s AND topic=%s",
        (user_id, q['topic']), fetch=True
    )
    curve_stage = curve[0]['curve_stage'] if curve else 'Not Started'

    return render_template(
        'quiz_page.html',
        quiz_id     = quiz_id,
        quiz_topic  = q['topic'],
        quiz_title  = q['video_title'],
        questions   = questions,
        total       = len(questions),
        difficulty  = difficulty,
        curve_stage = curve_stage,
        source      = q.get('notes_source', 'title'),
    )


# ============================================================
# CHATBOT — questions about a video the student watched
# ============================================================
_no_transcript_until = {}   # video_id -> time to retry, so follow-ups don't re-run the slow extraction


def _chat_video(user_id: int, message: str, video_id=None):
    """
    The watched video this message is about: the one picked in the chat, else
    (if the student refers to "the video" or "the teacher") the best match
    among their watched videos. Only the student's own watched videos are used.
    """
    from app.ai.video_qa import refers_to_video, pick_watched_video
    if video_id:
        rows = execute_query(
            "SELECT video_id, video_title, topic FROM watched_videos WHERE user_id=%s AND video_id=%s",
            (user_id, str(video_id)), fetch=True) or []
        if rows:
            return rows[0]
    if not refers_to_video(message):
        return None
    watched = execute_query(
        """SELECT video_id, video_title, topic FROM watched_videos
           WHERE user_id=%s ORDER BY watched_at DESC LIMIT 50""", (user_id,), fetch=True) or []
    return pick_watched_video(message, watched)


def _video_reply(message: str, history: list, video: dict):
    from app.ai.video_qa import answer_from_video, answer_without_transcript
    title = html.unescape(video.get('video_title') or 'This video')
    video_id = video['video_id']

    transcript = ''
    if time.time() >= _no_transcript_until.get(video_id, 0):
        transcript, _ = _server_transcript(video_id)
        if not transcript:
            _no_transcript_until[video_id] = time.time() + 600
    if not transcript:
        return answer_without_transcript(
            message, history, title,
            "I couldn't get this video's transcript, so I can't tell you what the teacher said about this.")
    return answer_from_video(message, history, title, transcript)


# ============================================================
# CHATBOT
# ============================================================
@gemini_bp.route('/chatbot/ask', methods=['POST'])
@login_required
def chatbot_ask():
    data      = _json_body()
    message   = data.get('message', '')
    history   = data.get('history', [])
    file_data = data.get('file_data')
    file_type = data.get('file_type', '')
    file_name = data.get('file_name', '')
    user_id   = session['user_id']

    try:
        progress = _student_context(user_id)
    except Exception as e:
        print(f"⚠️ Progress context error: {e}")
        progress = 'Progress data is temporarily unavailable.'

    # ── Image / PDF / Doc analysis ──────────────────────────────
    if file_data:
        try:
            import base64
            file_bytes = base64.b64decode(file_data)
            fname_lower = (file_name or '').lower()

            # 1. Image analysis via Gemini Vision
            if file_type.startswith('image/') and GEMINI_AVAILABLE:
                from google.genai import types
                img_part = types.Part.from_bytes(
                    data      = file_bytes,
                    mime_type = file_type
                )
                txt_part = types.Part.from_text(
                    text = _with_progress('Student request: ', progress) + (message or (
                        'Analyze this image and explain what you see. '
                        'If it contains code or a problem, solve it. '
                        'If it contains text or notes, explain the concepts.'
                    ))
                )
                resp = gemini_client.models.generate_content(
                    model    = 'gemini-3.6-flash',
                    contents = [img_part, txt_part]
                )
                return jsonify({'success': True, 'reply': resp.text.strip()})

            # 2. PDF analysis via PyPDF2
            elif file_type == 'application/pdf' or fname_lower.endswith('.pdf'):
                pdf_text = ''
                try:
                    import io
                    import PyPDF2
                    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                    for page in reader.pages[:15]:
                        txt = page.extract_text()
                        if txt:
                            pdf_text += txt + '\n'
                except Exception as ex:
                    print(f"⚠️ PDF parse error: {ex}")

                if pdf_text.strip():
                    prompt = f"""You are an intelligent educational AI assistant helping a student understand their document.
Document Name: {file_name}

Document Extracted Content:
\"\"\"
{pdf_text[:12000]}
\"\"\"

Student Question / Request: {message or 'Summarize this document, explain the main topics, and highlight key takeaways.'}

Instructions:
- Carefully extract and synthesize the information from the document to answer the student's question accurately.
- Provide clear, educational explanations with formatting (bullet points, bold highlights, code blocks if applicable).
- Base your answers directly on the document text."""
                    reply = _generate_ai(_with_progress(prompt, progress), max_tokens=1500)
                    return jsonify({'success': True, 'reply': reply})

                # If text is empty (scanned image PDF) and Gemini Vision is available
                if GEMINI_AVAILABLE:
                    try:
                        from google.genai import types
                        pdf_part = types.Part.from_bytes(data=file_bytes, mime_type='application/pdf')
                        txt_part = types.Part.from_text(
                            text=_with_progress('Student request: ', progress) + (message or 'Analyze this PDF document and explain its key concepts in detail.')
                        )
                        resp = gemini_client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=[pdf_part, txt_part]
                        )
                        if resp and resp.text:
                            return jsonify({'success': True, 'reply': resp.text.strip()})
                    except Exception as g_err:
                        print(f"⚠️ Gemini direct PDF error: {g_err}")

                prompt = f"A student uploaded a PDF named '{file_name}'. The file does not contain extractable text (it may be a scanned image or protected). Student question: {message}. Please advise them kindly on how to proceed or ask questions on the topic."
                reply = _generate_ai(_with_progress(prompt, progress), max_tokens=400)
                return jsonify({'success': True, 'reply': reply})

            # 3. Word (.docx) document analysis
            elif fname_lower.endswith('.docx') or 'wordprocessingml' in file_type:
                docx_text = ''
                try:
                    import io, zipfile, xml.etree.ElementTree as ET
                    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                        xml_content = z.read('word/document.xml')
                        tree = ET.fromstring(xml_content)
                        texts = [node.text for node in tree.iter() if node.text]
                        docx_text = ' '.join(texts)
                except Exception as dx_err:
                    print(f"⚠️ DOCX parse error: {dx_err}")

                if docx_text.strip():
                    prompt = f"""You are an intelligent educational AI assistant helping a student understand their document.
Document Name: {file_name}

Document Extracted Content:
\"\"\"
{docx_text[:12000]}
\"\"\"

Student Question / Request: {message or 'Summarize this document, explain the main topics, and highlight key takeaways.'}

Instructions:
- Carefully extract and synthesize the information from the document to answer the student's question accurately.
- Provide clear, educational explanations with formatting."""
                    reply = _generate_ai(_with_progress(prompt, progress), max_tokens=1500)
                    return jsonify({'success': True, 'reply': reply})

            # 4. Text / Markdown / Code file analysis
            elif file_type.startswith('text/') or fname_lower.endswith(('.txt', '.md', '.csv', '.py', '.json', '.html', '.js', '.c', '.cpp', '.java', '.sql')):
                text_content = ''
                try:
                    text_content = file_bytes.decode('utf-8', errors='ignore')
                except Exception as t_err:
                    print(f"⚠️ Text decode error: {t_err}")

                if text_content.strip():
                    prompt = f"""You are an intelligent educational AI assistant helping a student understand their file.
File Name: {file_name}

File Content:
\"\"\"
{text_content[:12000]}
\"\"\"

Student Question / Request: {message or 'Analyze this file, explain its content, and answer any questions.'}

Instructions:
- Thoroughly analyze the file content above to answer the student.
- Provide clear explanations, examples, or code breakdown where appropriate."""
                    reply = _generate_ai(_with_progress(prompt, progress), max_tokens=1500)
                    return jsonify({'success': True, 'reply': reply})

        except Exception as e:
            print(f"⚠️ File analysis error: {e}")

    # ── Question about a watched video ────────────────────
    video = None if file_data else _chat_video(user_id, message, data.get('video_id'))
    if video:
        try:
            reply = _video_reply(message, history, video)
            if reply:
                return jsonify({'success': True, 'reply': reply,
                                'video': {'video_id': video['video_id'],
                                          'title': html.unescape(video.get('video_title') or 'This video')}})
        except Exception as e:
            print(f"❌ Video question error: {e}")
            return jsonify({'success': False, 'message': "The assistant couldn't reply right now. Try again in a moment."})

    # ── Regular chat with history ─────────────────────────
    history_text = ''
    if history:
        for h in history[-6:]:
            role          = 'Student' if h['role'] == 'user' else 'AI Tutor'
            history_text += f"{role}: {h['content']}\n"

    prompt = f"""Remember the conversation context below.

Previous conversation:
{history_text}

Student: {message}

Instructions:
- Remember context from previous messages
- You don't have a video's content here. Only if the student asks what a video or teacher said, say you can't see it and that they can pick the video under "Ask about". Otherwise don't mention videos or "Ask about"
- Give clear, educational responses
- For code questions: provide working code examples with explanations
- For study plans: give structured day-by-day plans
- Use markdown: bold, code blocks, bullet points where helpful
- Keep responses concise but complete (max 400 words)"""

    try:
        reply = _generate_ai(_with_progress(prompt, progress), max_tokens=1200)
        return jsonify({'success': True, 'reply': reply})
    except Exception as e:
        print(f"❌ Chatbot error: {e}")
        return jsonify({'success': False, 'message': "The assistant couldn't reply right now. Try again in a moment."})


# ============================================================
# CHAT HISTORY — saved per account, so students never see each other's chats
# ============================================================
MAX_CHATS_PER_USER = 30
MAX_MESSAGES_PER_CHAT = 60
_CHAT_ID = re.compile(r'^[0-9]{1,20}$')
_VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{6,20}$')


def get_user_chats(user_id: int) -> list:
    """This student's saved chats, newest first, in the shape the chat page uses."""
    rows = execute_query(
        """SELECT client_id, title, history, video_id, video_title, updated_at
           FROM chat_conversations WHERE user_id=%s
           ORDER BY updated_at DESC LIMIT %s""", (user_id, MAX_CHATS_PER_USER)) or []
    chats = []
    for r in rows:
        try:
            history = json.loads(r['history'] or '[]')
        except ValueError:
            history = []
        chats.append({'id': r['client_id'], 'title': r['title'] or 'Chat', 'history': history,
                      'videoId': r['video_id'] or '', 'videoTitle': r['video_title'] or ''})
    return chats


@gemini_bp.route('/chatbot/conversations', methods=['POST'])
@login_required
def save_chat():
    data = _json_body()
    client_id = str(data.get('id', ''))
    if not _CHAT_ID.match(client_id):
        return jsonify({'success': False, 'message': 'Invalid chat.'}), 400

    history = []
    for m in (data.get('history') or [])[-MAX_MESSAGES_PER_CHAT:]:
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant'):
            history.append({'role': m['role'], 'content': str(m.get('content', ''))[:20000]})
    video_id = str(data.get('videoId') or '')
    video_id = video_id if _VIDEO_ID.match(video_id) else ''

    user_id = session['user_id']
    saved = execute_query(
        """INSERT INTO chat_conversations (user_id, client_id, title, history, video_id, video_title)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE title=VALUES(title), history=VALUES(history),
               video_id=VALUES(video_id), video_title=VALUES(video_title), updated_at=NOW()""",
        (user_id, client_id, str(data.get('title') or 'Chat')[:120], json.dumps(history),
         video_id or None, (str(data.get('videoTitle') or '')[:255] if video_id else None)))
    if saved is False:
        return jsonify({'success': False, 'message': "Couldn't save this chat."}), 500

    # Keep only the newest chats
    old = execute_query(
        "SELECT id FROM chat_conversations WHERE user_id=%s ORDER BY updated_at DESC, id DESC",
        (user_id,)) or []
    for r in old[MAX_CHATS_PER_USER:]:
        execute_query("DELETE FROM chat_conversations WHERE id=%s AND user_id=%s", (r['id'], user_id))
    return jsonify({'success': True})


@gemini_bp.route('/chatbot/conversations/<client_id>', methods=['DELETE'])
@login_required
def delete_chat(client_id):
    if not _CHAT_ID.match(client_id):
        return jsonify({'success': False}), 400
    execute_query("DELETE FROM chat_conversations WHERE user_id=%s AND client_id=%s",
                  (session['user_id'], client_id))
    return jsonify({'success': True})


# ============================================================
# POST-QUIZ RECOMMENDATIONS (internal helper)
# ============================================================
def _get_postquiz_recommendations(
    topic      : str,
    percentage : float,
    user_id    : int,
) -> dict:
    """
    Recommend videos after quiz based on score.
    <60%  → simpler/foundational videos
    60-80% → practice/intermediate
    >80%  → advanced/next topic
    """
    from app.routes.recommend import (
        get_yt, is_quota_err, search_youtube,
        get_db_cache, save_db_cache, fallback_for_query,
        _cache
    )

    if percentage < 60:
        difficulty = 'beginner'
        reason     = f"⚠️ Weak in {topic} — simpler videos to strengthen basics"
        queries    = [
            f"{topic} absolute beginners tutorial from scratch",
            f"{topic} basics explained simply",
        ]
    elif percentage < 80:
        difficulty = 'intermediate'
        reason     = f"📚 Good progress in {topic} — going deeper"
        queries    = [
            f"{topic} intermediate tutorial practice",
            f"{topic} concepts with examples",
        ]
    else:
        difficulty = 'advanced'
        reason     = f"🚀 Excellent in {topic} — next level content"
        queries    = [
            f"{topic} advanced expert tutorial",
            f"{topic} deep dive masterclass",
        ]

    watched_ids = {
        w['video_id'] for w in (
            execute_query(
                "SELECT video_id FROM watched_videos WHERE user_id=%s",
                (user_id,), fetch=True
            ) or []
        )
    }

    videos         = []
    quota_exceeded = False

    try:
        yt = get_yt()
    except Exception:
        quota_exceeded = True
        yt = None

    for q in queries:
        if len(videos) >= 3:
            break

        if quota_exceeded or yt is None:
            fb = fallback_for_query(q, reason, 'post_quiz', percentage / 100)
            if fb['video_id'] not in watched_ids:
                fb['difficulty'] = difficulty
                videos.append(fb)
            continue

        db_vids = get_db_cache(q)
        if db_vids:
            for v in db_vids[:2]:
                if v['video_id'] not in watched_ids and len(videos) < 3:
                    videos.append({**v, 'reason': reason, 'difficulty': difficulty, 'expert': 'post_quiz'})
            continue

        try:
            yt_vids = search_youtube(yt, q, 3)
            save_db_cache(q, yt_vids)
            for v in yt_vids:
                if v['video_id'] not in watched_ids and len(videos) < 3:
                    videos.append({**v, 'reason': reason, 'difficulty': difficulty, 'expert': 'post_quiz'})
        except Exception as e:
            if is_quota_err(e):
                quota_exceeded = True
                fb = fallback_for_query(q, reason, 'post_quiz', percentage / 100)
                if fb['video_id'] not in watched_ids and len(videos) < 3:
                    fb['difficulty'] = difficulty
                    videos.append(fb)

    # Clear MoE cache
    for k in list(_cache.keys()):
        if str(user_id) in k:
            del _cache[k]

    # Two queries can map to the same fallback video
    seen, unique = set(), []
    for v in videos:
        if v['video_id'] not in seen:
            seen.add(v['video_id'])
            unique.append(v)
    videos = unique

    return {
        'recommendations' : videos[:3],
        'difficulty_level': difficulty,
        'reason'          : reason,
        'count'           : len(videos),
    }