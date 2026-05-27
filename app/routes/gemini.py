# ============================================================
# gemini.py — AI Quiz, Notes, Chatbot + Learning Curve
# Primary: Groq (Free, Fast)
# Fallback: Gemini
# ============================================================

from flask import (Blueprint, request, jsonify,
                   session, render_template, redirect,
                   url_for)
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query

import os, json, time

gemini_bp = Blueprint('gemini', __name__)

# ── Initialize Groq ───────────────────────────────────────
from groq import Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Best models ordered by reliability
GROQ_MODELS = [
    'llama-3.1-8b-instant',       # Fastest, most reliable
    'llama-3.3-70b-versatile',    # More powerful
    'gemma2-9b-it',               # Google's model
    'mixtral-8x7b-32768',         # Mixtral fallback
]

# # ── Gemini Fallback ───────────────────────────────────────
try:
    from google import genai
    gemini_client    = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False

# Updated models — more stable for free tier
GEMINI_MODELS = [
    'gemini-1.5-flash',           # Most reliable free tier
    'gemini-1.5-flash-8b',        # Smaller, faster
    'gemini-2.0-flash-lite',      # Newest but rate limited
]


# ============================================================
# AI GENERATE FUNCTION — Fixed with better retry logic
# ============================================================
def generate(prompt, max_tokens=1000):
    last_error = None

    # ── Try Groq First ────────────────────────────────────
    for model in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                model       = model,
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = max_tokens,
                temperature = 0.7
            )
            result = response.choices[0].message.content.strip()
            print(f"✅ Groq success: {model}")
            return result

        except Exception as e:
            err = str(e)
            last_error = err

            # Rate limit — wait and try next model
            if '429' in err or 'rate' in err.lower():
                print(f"⚠️ Groq rate limit: {model} — trying next")
                time.sleep(1)
                continue

            # Invalid API key — skip all Groq models
            elif '401' in err or 'invalid_api_key' in err.lower() or 'Invalid API Key' in err:
                print(f"❌ Groq API key invalid — switching to Gemini")
                break

            # Token limit — try smaller model
            elif 'token' in err.lower() or 'context' in err.lower():
                print(f"⚠️ Groq token limit: {model} — trying next")
                continue

            # Other error — try next model
            else:
                print(f"❌ Groq error {model}: {e}")
                continue

    # ── Fallback to Gemini ────────────────────────────────
    if GEMINI_AVAILABLE:
        for model in GEMINI_MODELS:
            try:
                response = gemini_client.models.generate_content(
                    model    = model,
                    contents = prompt
                )
                text = response.text.strip()
                print(f"✅ Gemini success: {model}")
                return text

            except Exception as e:
                err = str(e)
                last_error = err

                # Rate limit — wait longer and try next
                if '429' in err or 'quota' in err.lower() or 'rate' in err.lower():
                    print(f"⚠️ Gemini rate limit: {model} — waiting 5s")
                    time.sleep(5)
                    continue

                # Invalid key
                elif '401' in err or 'API_KEY' in err:
                    print(f"❌ Gemini API key invalid")
                    break

                # Model not found — try next
                elif '404' in err or 'not found' in err.lower():
                    print(f"⚠️ Gemini model not found: {model}")
                    continue

                else:
                    print(f"❌ Gemini error {model}: {e}")
                    continue

    raise Exception(f"All AI models unavailable. Last error: {last_error}")


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def calculate_new_difficulty(percentage):
    if percentage >= 80:   return 'Hard'
    elif percentage >= 50: return 'Medium'
    else:                  return 'Easy'


def get_difficulty_message(percentage, new_difficulty):
    if percentage >= 80:
        return {
            'icon'   : '🔥',
            'title'  : 'Excellent! Level Up!',
            'message': f'Scored {percentage}%! Next = HARD',
            'color'  : 'danger'
        }
    elif percentage >= 50:
        return {
            'icon'   : '💪',
            'title'  : 'Good Job!',
            'message': f'Scored {percentage}%. Staying MEDIUM',
            'color'  : 'warning'
        }
    else:
        return {
            'icon'   : '📚',
            'title'  : 'Keep Practicing!',
            'message': f'Scored {percentage}%. Next = EASIER',
            'color'  : 'info'
        }


# ============================================================
# GENERATE QUIZ
# ============================================================
@gemini_bp.route('/gemini/generate-quiz', methods=['POST'])
@login_required
def generate_quiz():
    data        = request.get_json()
    video_title = data.get('video_title', '')
    topic       = data.get('topic', '')
    user_id     = session['user_id']
    video_id    = data.get('video_id', '')

    # ── Get difficulty from learning curve ────────────────
    topic_diff = execute_query(
        """SELECT difficulty_level, last_score, attempts
           FROM topic_difficulty
           WHERE user_id=%s AND topic=%s""",
        (user_id, topic), fetch=True
    )

    if topic_diff:
        difficulty = topic_diff[0]['difficulty_level']
        attempts   = topic_diff[0]['attempts']
        last_score = float(topic_diff[0]['last_score'])
    else:
        difficulty = 'Medium'
        attempts   = 0
        last_score = 0.0

    # ── Check learning curve stage ────────────────────────
    curve = execute_query(
        """SELECT curve_stage, predicted_next
           FROM learning_curves
           WHERE user_id=%s AND topic=%s""",
        (user_id, topic), fetch=True
    )

    curve_stage = curve[0]['curve_stage'] if curve else 'Not Started'

    if curve_stage == 'Struggling' and difficulty != 'Easy':
        difficulty = 'Easy'
    elif curve_stage == 'Mastery' and difficulty != 'Hard':
        difficulty = 'Hard'

    diff_guide = {
        'Easy'  : 'Simple basic questions. Definitions only.',
        'Medium': 'Mix of concepts and applications.',
        'Hard'  : 'Advanced analysis and scenarios.'
    }

    prompt = f"""Generate exactly 20 multiple choice questions about:
Video: {video_title}
Topic: {topic}
Difficulty: {difficulty} — {diff_guide[difficulty]}

Rules:
- Cover different aspects of the topic
- No repeated or similar questions
- Clear and unambiguous questions

Return ONLY valid JSON array, no other text:
[
  {{
    "question": "Question text?",
    "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}},
    "correct": "A",
    "explanation": "Why A is correct"
  }}
]"""

    try:
        raw   = generate(prompt, max_tokens=3000)
        raw   = raw.replace('```json', '').replace('```', '').strip()
        start = raw.find('[')
        end   = raw.rfind(']') + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        questions = json.loads(raw)
        questions = questions[:20]

        quiz_id = execute_query(
            """INSERT INTO video_quizzes
               (user_id, video_id, video_title,
                topic, questions, total)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (user_id, video_id, video_title,
             topic, json.dumps(questions), len(questions))
        )

        return jsonify({
            'success'    : True,
            'questions'  : questions,
            'quiz_id'    : quiz_id,
            'total'      : len(questions),
            'difficulty' : difficulty,
            'attempts'   : attempts,
            'last_score' : last_score,
            'curve_stage': curve_stage
        })

    except Exception as e:
        print(f"❌ Quiz error: {e}")
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# GENERATE NOTES
# ============================================================
@gemini_bp.route('/gemini/generate-notes', methods=['POST'])
@login_required
def generate_notes():
    data        = request.get_json()
    video_title = data.get('video_title', '')
    topic       = data.get('topic', '')
    user_id     = session['user_id']
    video_id    = data.get('video_id', '')

    prompt = f"""Create detailed study notes for a student about:
Video: {video_title}
Topic: {topic}

Format exactly like this:
## Key Concepts
- concept 1 with brief explanation
- concept 2 with brief explanation
- concept 3 with brief explanation
- concept 4 with brief explanation
- concept 5 with brief explanation

## Important Definitions
- Term1: detailed definition
- Term2: detailed definition
- Term3: detailed definition

## Examples
- Example 1: practical example
- Example 2: practical example

## Key Takeaways
- takeaway 1
- takeaway 2
- takeaway 3

## Summary
Write 4-5 sentences summarizing the main concepts.

Keep it educational and comprehensive. Around 400-500 words."""

    try:
        notes = generate(prompt, max_tokens=1500)

        execute_query(
            """INSERT INTO video_notes (user_id, video_id, notes)
               VALUES (%s,%s,%s)
               ON DUPLICATE KEY UPDATE notes=%s""",
            (user_id, video_id, notes, notes)
        )

        return jsonify({'success': True, 'notes': notes})

    except Exception as e:
        print(f"❌ Notes error: {e}")
        return jsonify({'success': False, 'message': str(e)})
# ============================================================
# DIFFICULTY-BASED VIDEO RECOMMENDATIONS
# Called after quiz submission
# ============================================================
def get_difficulty_based_recommendations(topic, percentage, user_id):
    """
    Post-quiz: recommend videos based on score.
    Weak  (<60%) → simpler foundational videos
    Good  (60-80%) → intermediate practice
    Strong (>80%) → advanced + next topic
    """
    from app.routes.recommend import (
        get_yt, is_quota_err, search_youtube,
        get_db_cache, save_db_cache,
        fallback_for_query, _cache, set_cache, get_cache
    )

    if percentage < 60:
        difficulty = 'beginner'
        reason     = f"⚠️ Weak in {topic} — simpler videos to strengthen basics"
        queries    = [
            f"{topic} absolute beginners tutorial from zero",
            f"{topic} basics explained simply step by step",
            f"learn {topic} from scratch complete guide",
        ]
    elif percentage < 80:
        difficulty = 'intermediate'
        reason     = f"📚 Good progress in {topic} — going deeper"
        queries    = [
            f"{topic} intermediate tutorial practice exercises",
            f"{topic} concepts explained with examples",
            f"{topic} in depth complete course",
        ]
    else:
        difficulty = 'advanced'
        reason     = f"🚀 Excellent in {topic} — next level content"
        queries    = [
            f"{topic} advanced expert tutorial projects",
            f"{topic} professional level deep dive",
            f"advanced {topic} complete masterclass",
        ]

    watched_ids = {
        w['video_id'] for w in
        (execute_query(
            "SELECT video_id FROM watched_videos WHERE user_id=%s",
            (user_id,), fetch=True
        ) or [])
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
            fb = fallback_for_query(q, reason, 'post_quiz', percentage)
            if fb['video_id'] not in watched_ids:
                fb['difficulty'] = difficulty
                videos.append(fb)
            continue

        # DB cache
        db_videos = get_db_cache(q)
        if db_videos:
            for v in db_videos[:2]:
                if v['video_id'] not in watched_ids and len(videos) < 3:
                    videos.append({
                        **v,
                        'reason'    : reason,
                        'difficulty': difficulty,
                        'expert'    : 'post_quiz',
                    })
            continue

        try:
            yt_videos = search_youtube(yt, q, 3)
            save_db_cache(q, yt_videos)
            for v in yt_videos:
                if v['video_id'] not in watched_ids and len(videos) < 3:
                    videos.append({
                        **v,
                        'reason'    : reason,
                        'difficulty': difficulty,
                        'expert'    : 'post_quiz',
                    })
        except Exception as e:
            if is_quota_err(e):
                quota_exceeded = True
                fb = fallback_for_query(q, reason, 'post_quiz', percentage)
                if fb['video_id'] not in watched_ids and len(videos) < 3:
                    fb['difficulty'] = difficulty
                    videos.append(fb)

    # Clear MoE cache so dashboard refreshes
    cache_key = f"rec_{user_id}"
    if cache_key in _cache:
        del _cache[cache_key]
    pref_cache_pattern = f"pref_{user_id}"
    keys_to_delete = [k for k in _cache if k.startswith(pref_cache_pattern)]
    for k in keys_to_delete:
        del _cache[k]

    return {
        'recommendations' : videos[:3],
        'difficulty_level': difficulty,
        'reason'          : reason,
        'count'           : len(videos),
    }




# ============================================================
# SUBMIT QUIZ — Learning Curve + Weak Topic Detection
# ============================================================
@gemini_bp.route('/gemini/submit-quiz', methods=['POST'])
@login_required
def submit_quiz():
    data    = request.get_json()
    user_id = session['user_id']
    quiz_id = data.get('quiz_id')
    answers = data.get('answers', {})
    topic   = data.get('topic', '')

    quizzes = execute_query(
        "SELECT * FROM video_quizzes WHERE id=%s AND user_id=%s",
        (quiz_id, user_id), fetch=True
    )

    if not quizzes:
        return jsonify({'success': False, 'message': 'Quiz not found'})

    questions  = json.loads(quizzes[0]['questions'])
    score      = 0
    results    = []

    for i, q in enumerate(questions):
        user_ans   = answers.get(str(i), '')
        correct    = q['correct']
        is_correct = user_ans == correct
        if is_correct:
            score += 1
        results.append({
            'question'   : q['question'],
            'user_answer': user_ans,
            'correct'    : correct,
            'is_correct' : is_correct,
            'explanation': q.get('explanation', '')
        })

    total      = len(questions)
    percentage = round((score / total * 100), 1) if total > 0 else 0

    execute_query(
        "UPDATE video_quizzes SET score=%s, attempted=1 WHERE id=%s",
        (score, quiz_id)
    )

    # ── Weak Topic Detection ──────────────────────────────
    is_weak        = percentage < 60
    related_search = None

    if is_weak:
        execute_query(
            """INSERT INTO weak_topics (user_id, topic, fail_count)
               VALUES (%s,%s,1)
               ON DUPLICATE KEY UPDATE
               fail_count    = fail_count + 1,
               last_detected = CURRENT_TIMESTAMP""",
            (user_id, topic)
        )
        related_search = topic
        print(f"⚠️ Weak topic: {topic} ({percentage}%)")

    # ── Auto Difficulty Adjustment ────────────────────────
    new_difficulty = calculate_new_difficulty(percentage)
    difficulty_msg = get_difficulty_message(percentage, new_difficulty)

    execute_query(
        """INSERT INTO topic_difficulty
           (user_id, topic, difficulty_level, last_score, attempts)
           VALUES (%s,%s,%s,%s,1)
           ON DUPLICATE KEY UPDATE
           difficulty_level = %s,
           last_score       = %s,
           attempts         = attempts + 1""",
        (user_id, topic, new_difficulty, percentage,
         new_difficulty, percentage)
    )

    execute_query(
        "UPDATE users SET difficulty_level=%s WHERE id=%s",
        (new_difficulty, user_id)
    )

    # ── Update Learning Curve ─────────────────────────────
    curve_data = {}
    try:
        from app.ai.learning_curve import LearningCurveModel
        lc         = LearningCurveModel(user_id)
        curve      = lc.save_curve(topic)
        curve_data = {
            'curve_stage'   : curve['curve_stage'],
            'predicted_next': curve['predicted_next'],
            'mastery_eta'   : curve['mastery_eta'],
            'learning_rate' : curve['learning_rate']
        }
        print(f"📈 Learning Curve updated: {topic} → {curve['curve_stage']}")

    except Exception as e:
        print(f"⚠️ Learning curve error: {e}")

    # ── Get Difficulty-Based Video Recommendations ────────
# ── Get post-quiz video suggestions ───────────────────
    video_suggestions = {}
    try:
        video_suggestions = get_difficulty_based_recommendations(
            topic, percentage, user_id
        )
        print(f"🎥 Post-quiz recs: {video_suggestions.get('difficulty_level')} "
              f"({video_suggestions.get('count', 0)} videos)")
    except Exception as e:
        print(f"⚠️ Post-quiz rec error: {e}")
        import traceback
        traceback.print_exc()
        video_suggestions = {
            'recommendations' : [],
            'difficulty_level': 'unknown',
            'reason'          : '',
            'count'           : 0,
        }

    return jsonify({
        'success'              : True,
        'score'                : score,
        'total'                : total,
        'percentage'           : percentage,
        'results'              : results,
        'is_weak'              : is_weak,
        'topic'                : topic,
        'new_difficulty'       : new_difficulty,
        'difficulty_msg'       : difficulty_msg,
        'related_search'       : related_search,
        'curve_stage'          : curve_data.get('curve_stage', ''),
        'predicted_next'       : curve_data.get('predicted_next', 0),
        'mastery_eta'          : curve_data.get('mastery_eta', ''),
        'learning_rate'        : curve_data.get('learning_rate', 0),
        'video_suggestions'    : video_suggestions.get('recommendations', []),
        'suggestion_reason'    : video_suggestions.get('reason', ''),
        'suggestion_difficulty': video_suggestions.get('difficulty_level', ''),
        'suggestion_count'     : video_suggestions.get('count', 0),
    })


# ============================================================
# CHATBOT
# ============================================================
@gemini_bp.route('/chatbot/ask', methods=['POST'])
@login_required
def chatbot_ask():
    data      = request.get_json()
    message   = data.get('message', '')
    history   = data.get('history', [])
    file_data = data.get('file_data', None)
    file_type = data.get('file_type', '')
    file_name = data.get('file_name', '')
    user_id   = session['user_id']

    cognitive = execute_query(
        "SELECT learning_style FROM cognitive_results WHERE user_id=%s",
        (user_id,), fetch=True
    )
    style = cognitive[0]['learning_style'] if cognitive else 'Student'

    # ── Image / PDF Analysis ──────────────────────────────
    if file_data:
        try:
            import base64
            img_bytes = base64.b64decode(file_data)

            if file_type.startswith('image/'):
                if GEMINI_AVAILABLE:
                    from google.genai import types
                    img_part = types.Part.from_bytes(
                        data      = img_bytes,
                        mime_type = file_type
                    )
                    txt_part = types.Part.from_text(
                        text = message or
                               'Analyze this image and explain what you see. '
                               'If it contains code, explain it. '
                               'If it contains a problem, solve it.'
                    )
                    response = gemini_client.models.generate_content(
                        model    = 'gemini-1.5-flash',
                        contents = [img_part, txt_part]
                    )
                    return jsonify({
                        'success': True,
                        'reply'  : response.text.strip()
                    })

            elif file_type == 'application/pdf':
                try:
                    import io
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(img_bytes))
                    pdf_text   = ''
                    for page in pdf_reader.pages[:5]:
                        pdf_text += page.extract_text() + '\n'

                    if pdf_text.strip():
                        prompt = f"""Analyze this PDF content and answer the question.

PDF Content:
{pdf_text[:3000]}

Student Question: {message or 'Summarize this PDF and explain key points'}

Provide a clear, educational response."""

                        reply = generate(prompt, max_tokens=1500)
                        return jsonify({'success': True, 'reply': reply})

                except ImportError:
                    pass

                prompt = f"""A student uploaded a PDF file named '{file_name}'.
They ask: {message or 'Please analyze this document'}
Since I cannot read the PDF directly, ask them to copy-paste the text."""

                reply = generate(prompt, max_tokens=500)
                return jsonify({'success': True, 'reply': reply})

        except Exception as e:
            print(f"File analysis error: {e}")

    # ── Regular Chat with History ─────────────────────────
    history_text = ''
    if history:
        for h in history[-6:]:
            role = 'Student' if h['role'] == 'user' else 'AI'
            history_text += f"{role}: {h['content']}\n"

    prompt = f"""You are a helpful AI learning assistant for a {style} student.
You have memory of the conversation below.

Previous conversation:
{history_text}

Student now asks: {message}

Instructions:
- Remember context from previous messages
- Give clear, educational responses
- For code questions, provide code examples
- For study plans, give structured day-by-day plans
- Keep responses concise but complete
- Use markdown formatting (bold, code blocks, bullet points)"""

    try:
        reply = generate(prompt, max_tokens=1200)
        return jsonify({'success': True, 'reply': reply})
    except Exception as e:
        print(f"Chatbot error: {e}")
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# GET DIFFICULTY
# ============================================================
@gemini_bp.route('/gemini/get-difficulty', methods=['GET'])
@login_required
def get_difficulty():
    user_id = session['user_id']
    topic   = request.args.get('topic', '')

    curve = execute_query(
        """SELECT difficulty_level, curve_stage,
                  current_score, predicted_next
           FROM learning_curves
           WHERE user_id=%s AND topic=%s""",
        (user_id, topic), fetch=True
    )

    if curve:
        return jsonify({
            'success'       : True,
            'difficulty'    : curve[0]['difficulty_level'],
            'curve_stage'   : curve[0]['curve_stage'],
            'current_score' : float(curve[0]['current_score']),
            'predicted_next': float(curve[0]['predicted_next'])
        })

    topic_diff = execute_query(
        """SELECT difficulty_level, last_score, attempts
           FROM topic_difficulty
           WHERE user_id=%s AND topic=%s""",
        (user_id, topic), fetch=True
    )

    if topic_diff:
        return jsonify({
            'success'   : True,
            'difficulty': topic_diff[0]['difficulty_level'],
            'last_score': float(topic_diff[0]['last_score']),
            'attempts'  : topic_diff[0]['attempts']
        })

    return jsonify({
        'success'   : True,
        'difficulty': 'Medium',
        'last_score': 0,
        'attempts'  : 0
    })


# ============================================================
# QUIZ PAGE
# ============================================================
@gemini_bp.route('/quiz/page/<int:quiz_id>')
@login_required
def quiz_page(quiz_id):
    user_id = session['user_id']

    quiz = execute_query(
        """SELECT * FROM video_quizzes
           WHERE id=%s AND user_id=%s""",
        (quiz_id, user_id), fetch=True
    )

    if not quiz:
        return redirect(url_for('dashboard.index'))

    q         = quiz[0]
    questions = json.loads(q['questions'])

    curve = execute_query(
        """SELECT difficulty_level, curve_stage
           FROM learning_curves
           WHERE user_id=%s AND topic=%s""",
        (user_id, q['topic']), fetch=True
    )

    if curve:
        difficulty  = curve[0]['difficulty_level']
        curve_stage = curve[0]['curve_stage']
    else:
        topic_diff = execute_query(
            """SELECT difficulty_level FROM topic_difficulty
               WHERE user_id=%s AND topic=%s""",
            (user_id, q['topic']), fetch=True
        )
        difficulty  = topic_diff[0]['difficulty_level'] \
                      if topic_diff else 'Medium'
        curve_stage = 'Not Started'

    return render_template(
        'quiz_page.html',
        quiz_id     = quiz_id,
        quiz_topic  = q['topic'],
        quiz_title  = q['video_title'],
        questions   = questions,
        total       = len(questions),
        difficulty  = difficulty,
        curve_stage = curve_stage
    )