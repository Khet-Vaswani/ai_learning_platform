# ============================================================
# gemini.py — AI Quiz, Notes, Chatbot Routes
# Uses: notes_generator.py + quiz_generator.py (pipeline)
# Primary AI: Groq | Fallback: Gemini
# ============================================================

from flask import (Blueprint, request, jsonify,
                   session, render_template, redirect, url_for)
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query

import os, json, time

gemini_bp = Blueprint('gemini', __name__)

# ── Groq client ───────────────────────────────────────────
from groq import Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

GROQ_MODELS = [
    'llama-3.1-8b-instant',
    'llama-3.3-70b-versatile',
    'gemma2-9b-it',
    'mixtral-8x7b-32768',
]

# ── Gemini client ─────────────────────────────────────────
try:
    from google import genai
    gemini_client    = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

GEMINI_MODELS = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-8b',
]


# ============================================================
# SHARED AI GENERATE — used by chatbot only
# (notes/quiz use their own generators)
# ============================================================
def _generate_ai(prompt: str, max_tokens: int = 1200) -> str:
    """Groq → Gemini fallback for chatbot."""
    last_error = None

    for model in GROQ_MODELS:
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
# GENERATE NOTES
# ============================================================
@gemini_bp.route('/gemini/generate-notes', methods=['POST'])
@login_required
def generate_notes_route():
    """
    Generate AI study notes from transcript or video title.
    Frontend sends: video_id, video_title, topic, transcript (optional)
    """
    data        = request.get_json() or {}
    video_id    = data.get('video_id', '')
    video_title = data.get('video_title', '')
    topic       = data.get('topic', '')
    transcript  = data.get('transcript', '')
    user_id     = session['user_id']

    if not transcript:
        cached_trans = execute_query(
            "SELECT transcript_text FROM video_transcripts WHERE video_id = %s",
            (video_id,), fetch=True
        )
        if cached_trans:
            transcript = cached_trans[0]['transcript_text']

    print(f"\n📝 Notes request: '{topic}' | transcript={len(transcript)} chars")

    try:
        from app.ai.notes_generator import generate_notes, get_saved_notes

        # Check DB cache first (avoid regenerating)
        cached = get_saved_notes(user_id, video_id)
        if cached.get('success') and cached.get('from_cache'):
            print(f"✅ Notes from cache")
            return jsonify({
                'success'   : True,
                'notes'     : cached['notes'],
                'notes_html': cached.get('notes_html', cached['notes']),
                'source'    : cached['source'],
                'word_count': cached['word_count'],
                'from_cache': True,
            })

        # Generate fresh notes
        result = generate_notes(
            video_id    = video_id,
            video_title = video_title,
            topic       = topic,
            user_id     = user_id,
            transcript  = transcript,
        )
        return jsonify(result)

    except Exception as e:
        print(f"❌ Notes route error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# GENERATE QUIZ
# ============================================================
@gemini_bp.route('/gemini/generate-quiz', methods=['POST'])
@login_required
def generate_quiz_route():
    """
    Generate MCQ quiz from transcript or video title.
    Frontend sends: video_id, video_title, topic, transcript (optional)
    """
    data        = request.get_json() or {}
    video_id    = data.get('video_id', '')
    video_title = data.get('video_title', '')
    topic       = data.get('topic', '')
    transcript  = data.get('transcript', '')
    user_id     = session['user_id']

    if not transcript:
        cached_trans = execute_query(
            "SELECT transcript_text FROM video_transcripts WHERE video_id = %s",
            (video_id,), fetch=True
        )
        if cached_trans:
            transcript = cached_trans[0]['transcript_text']

    print(f"\n📋 Quiz request: '{topic}' | transcript={len(transcript)} chars")

    try:
        from app.ai.quiz_generator import generate_quiz

        result = generate_quiz(
            video_id    = video_id,
            video_title = video_title,
            topic       = topic,
            user_id     = user_id,
            transcript  = transcript,
            # difficulty = None → auto-detected from learning curve
        )
        return jsonify(result)

    except Exception as e:
        print(f"❌ Quiz route error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


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
    data    = request.get_json() or {}
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
    user_id = session['user_id']
    topic   = request.args.get('topic', 'General')

    # Try learning curve first
    curve = execute_query(
        """SELECT difficulty_level, curve_stage, current_score
           FROM learning_curves WHERE user_id=%s AND topic=%s""",
        (user_id, topic), fetch=True
    )
    if curve:
        return jsonify({
            'success'    : True,
            'difficulty' : curve[0]['difficulty_level'] or 'Medium',
            'curve_stage': curve[0]['curve_stage'],
            'score'      : float(curve[0]['current_score'] or 0),
        })

    # topic_difficulty table
    td = execute_query(
        """SELECT difficulty_level, last_score, attempts
           FROM topic_difficulty WHERE user_id=%s AND topic=%s""",
        (user_id, topic), fetch=True
    )
    if td:
        return jsonify({
            'success'   : True,
            'difficulty': td[0]['difficulty_level'] or 'Medium',
            'last_score': float(td[0]['last_score'] or 0),
            'attempts'  : td[0]['attempts'] or 0,
        })

    return jsonify({'success': True, 'difficulty': 'Medium', 'last_score': 0, 'attempts': 0})


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

    # Get difficulty
    td = execute_query(
        "SELECT difficulty_level FROM topic_difficulty WHERE user_id=%s AND topic=%s",
        (user_id, q['topic']), fetch=True
    )
    difficulty  = td[0]['difficulty_level'] if td else 'Medium'

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
# CHATBOT
# ============================================================
@gemini_bp.route('/chatbot/ask', methods=['POST'])
@login_required
def chatbot_ask():
    data      = request.get_json() or {}
    message   = data.get('message', '')
    history   = data.get('history', [])
    file_data = data.get('file_data')
    file_type = data.get('file_type', '')
    file_name = data.get('file_name', '')
    user_id   = session['user_id']

    # Get learning style
    cognitive = execute_query(
        "SELECT learning_style FROM cognitive_results WHERE user_id=%s",
        (user_id,), fetch=True
    )
    style = cognitive[0]['learning_style'] if cognitive else 'Student'

    # ── Image / PDF analysis ──────────────────────────────
    if file_data:
        try:
            import base64
            file_bytes = base64.b64decode(file_data)

            # Image analysis via Gemini Vision
            if file_type.startswith('image/') and GEMINI_AVAILABLE:
                from google.genai import types
                img_part = types.Part.from_bytes(
                    data      = file_bytes,
                    mime_type = file_type
                )
                txt_part = types.Part.from_text(
                    text = message or (
                        'Analyze this image and explain what you see. '
                        'If it contains code or a problem, solve it. '
                        'If it contains text or notes, explain the concepts.'
                    )
                )
                resp = gemini_client.models.generate_content(
                    model    = 'gemini-1.5-flash',
                    contents = [img_part, txt_part]
                )
                return jsonify({'success': True, 'reply': resp.text.strip()})

            # PDF analysis via PyPDF2
            elif file_type == 'application/pdf':
                try:
                    import io
                    import PyPDF2
                    reader   = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                    pdf_text = ''
                    for page in reader.pages[:5]:
                        pdf_text += page.extract_text() + '\n'

                    if pdf_text.strip():
                        prompt = f"""Analyze this PDF content and answer the student's question.

PDF Content (first 5 pages):
{pdf_text[:3000]}

Student Question: {message or 'Summarize this document and explain the key concepts'}

Provide a clear, educational response."""
                        reply = _generate_ai(prompt, max_tokens=1500)
                        return jsonify({'success': True, 'reply': reply})
                except ImportError:
                    pass

                prompt = f"A student uploaded a PDF named '{file_name}'. They ask: {message}. Ask them to copy-paste the text content."
                reply  = _generate_ai(prompt, max_tokens=400)
                return jsonify({'success': True, 'reply': reply})

        except Exception as e:
            print(f"⚠️ File analysis error: {e}")

    # ── Regular chat with history ─────────────────────────
    history_text = ''
    if history:
        for h in history[-6:]:
            role          = 'Student' if h['role'] == 'user' else 'AI Tutor'
            history_text += f"{role}: {h['content']}\n"

    prompt = f"""You are a helpful AI learning assistant for a {style} student.
Remember the conversation context below.

Previous conversation:
{history_text}

Student: {message}

Instructions:
- Remember context from previous messages
- Give clear, educational responses
- For code questions: provide working code examples with explanations
- For study plans: give structured day-by-day plans
- Use markdown: bold, code blocks, bullet points where helpful
- Keep responses concise but complete (max 400 words)"""

    try:
        reply = _generate_ai(prompt, max_tokens=1200)
        return jsonify({'success': True, 'reply': reply})
    except Exception as e:
        print(f"❌ Chatbot error: {e}")
        return jsonify({'success': False, 'message': str(e)})


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
        _cache, FALLBACK
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

    return {
        'recommendations' : videos[:3],
        'difficulty_level': difficulty,
        'reason'          : reason,
        'count'           : len(videos),
    }