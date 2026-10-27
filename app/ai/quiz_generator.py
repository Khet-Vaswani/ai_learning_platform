# ============================================================
# quiz_generator.py — Fixed: JSON truncation + 3 difficulty levels
# Fix 1: max_tokens 3500 → 6000
# Fix 2: Fewer questions per request (10 not 20)
# Fix 3: Robust JSON parser (handles truncation)
# Fix 4: Beginner / Intermediate / Advanced 3-level system
# ============================================================

import os
import json
import time
import re
from app.utils.db import execute_query


# ── Language config ───────────────────────────────────────
LANGUAGE_PROMPTS = {
    'en': "Write all questions, options, and explanations in English only.",
    'ur': "تمام سوالات، آپشنز اور وضاحتیں صرف اردو میں لکھیں۔",
    'hi': "सभी प्रश्न, विकल्प और स्पष्टीकरण केवल हिंदी में लिखें।",
    'sd': "سڀ سوال، آپشن ۽ وضاحتون صرف سنڌي ۾ لکو۔",
}

LANG_NAMES = {
    'en': 'English',
    'ur': 'Urdu',
    'hi': 'Hindi',
    'sd': 'Sindhi',
}

# ── 3-Level Difficulty System ─────────────────────────────
DIFFICULTY_LEVELS = {
    'Beginner': {
        'label'      : '🟢 Beginner',
        'color'      : '#059669',
        'description': 'Simple recall — definitions, basic facts, straightforward identification.',
        'score_range': 'For students scoring 0–49%',
        'question_style': (
            'Ask ONLY simple recall questions. '
            'Test basic definitions, simple facts, and easy identification. '
            'All wrong options should be clearly different from the correct answer. '
            'Questions should be answerable by anyone who watched the video once.'
        ),
    },
    'Intermediate': {
        'label'      : '🟡 Intermediate',
        'color'      : '#d97706',
        'description': 'Understanding — explain concepts, compare ideas, apply knowledge.',
        'score_range': 'For students scoring 50–79%',
        'question_style': (
            'Ask questions that test understanding and application. '
            'Include comparison questions, "why" and "how" questions. '
            'Wrong options should be plausible but clearly incorrect on reflection. '
            'Mix of easy and moderate difficulty.'
        ),
    },
    'Advanced': {
        'label'      : '🔴 Advanced',
        'color'      : '#dc2626',
        'description': 'Analysis — evaluate scenarios, solve problems, deep understanding.',
        'score_range': 'For students scoring 80–100%',
        'question_style': (
            'Ask analysis and evaluation questions. '
            'Test deep understanding, cause-effect relationships, and critical thinking. '
            'Wrong options should be very plausible and require careful thought. '
            'Include scenario-based and application questions.'
        ),
    },
}

# DB difficulty → display level mapping
DB_TO_LEVEL = {
    'Easy'  : 'Beginner',
    'Medium': 'Intermediate',
    'Hard'  : 'Advanced',
    # Direct mappings
    'Beginner'    : 'Beginner',
    'Intermediate': 'Intermediate',
    'Advanced'    : 'Advanced',
}

LEVEL_TO_DB = {
    'Beginner'    : 'Easy',
    'Intermediate': 'Medium',
    'Advanced'    : 'Hard',
}


# ── AI generate — with higher token limit ─────────────────
def _generate(prompt: str, max_tokens: int = 6000) -> str:
    """
    Groq first, then Gemini fallback.
    max_tokens raised to 6000 to prevent JSON truncation.
    """
    from groq import Groq
    GROQ_MODELS = [
        'groq/compound-mini',
        'groq/compound',
        'openai/gpt-oss-120b',
        'qwen/qwen3.8-27b',
    ]
    client     = Groq(api_key=os.getenv('GROQ_API_KEY'))
    last_error = None

    for model in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model       = model,
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = max_tokens,
                temperature = 0.3,   # Lower = more consistent JSON
            )
            result = resp.choices[0].message.content.strip()
            print(f"✅ Quiz via Groq: {model} | tokens≈{len(result)//4}")
            return result
        except Exception as e:
            err = str(e)
            last_error = err
            if '429' in err or 'rate' in err.lower():
                time.sleep(2); continue
            elif '401' in err or 'invalid_api_key' in err.lower():
                break
            continue

    # Gemini fallback
    GEMINI_MODELS = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-flash-latest']
    try:
        from google import genai
        gc = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        for model in GEMINI_MODELS:
            try:
                resp = gc.models.generate_content(
                    model    = model,
                    contents = prompt
                )
                print(f"✅ Quiz via Gemini fallback: {model}")
                return resp.text.strip()
            except Exception as ge:
                err = str(ge)
                if '429' in err or 'quota' in err.lower():
                    time.sleep(2); continue
                continue
    except Exception as e:
        raise Exception(f"All AI models failed. Last: {last_error} | Gemini: {e}")
    raise Exception(f"All AI models failed. Last: {last_error}")


# ── Text preprocessor ─────────────────────────────────────
def _preprocess(text: str, max_chars: int = 3000) -> dict:
    if not text or len(text.strip()) < 30:
        return {'text': '', 'word_count': 0, 'is_usable': False}
    cleaned = re.sub(r'\[.*?\]', '', text)
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)
    cleaned = re.sub(r'http\S+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > max_chars:
        cut = cleaned[:max_chars]
        lp  = cut.rfind('. ')
        if lp > max_chars * 0.7:
            cut = cut[:lp + 1]
        cleaned = cut.strip()
    wc = len(cleaned.split())
    return {'text': cleaned, 'word_count': wc, 'is_usable': wc >= 20}


# ── Language detection ─────────────────────────────────────
def _detect_language(text: str) -> str:
    if not text:
        return 'en'
    arabic     = len(re.findall(r'[\u0600-\u06FF]', text))
    devanagari = len(re.findall(r'[\u0900-\u097F]', text))
    latin      = len(re.findall(r'[a-zA-Z]', text))
    total      = max(arabic + devanagari + latin, 1)
    if devanagari / total > 0.3:
        return 'hi'
    if arabic / total > 0.3:
        sindhi = len(re.findall(r'[\u0680-\u068F]', text))
        return 'sd' if sindhi > 5 else 'ur'
    return 'en'


# ── ROBUST JSON parser — handles truncation ───────────────
def _parse_quiz_json(raw: str) -> list:
    """
    Parse quiz JSON. Handles:
    - Markdown fences (```json ... ```)
    - Truncated JSON (incomplete last object)
    - Extra text before/after array
    """
    # Remove markdown fences
    raw = raw.replace('```json', '').replace('```', '').strip()

    # Find array boundaries
    start = raw.find('[')
    if start == -1:
        raise ValueError(f"No '[' found in response. Raw: {raw[:300]}")

    end = raw.rfind(']') + 1

    # If no closing bracket → JSON was truncated
    if end == 0:
        print("⚠️ JSON truncated — attempting recovery...")
        raw = _recover_truncated_json(raw[start:])
        end = len(raw)
        start = 0
    else:
        raw = raw[start:end]

    # Try direct parse
    try:
        questions = json.loads(raw)
        return _validate_questions(questions)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e} — attempting recovery...")
        raw = _recover_truncated_json(raw)
        try:
            questions = json.loads(raw)
            return _validate_questions(questions)
        except json.JSONDecodeError as e2:
            raise ValueError(f"JSON parse failed after recovery: {e2}")


def _recover_truncated_json(raw: str) -> str:
    """
    Fix truncated JSON array by removing the last incomplete object.
    Finds the last complete object (ends with }) and closes the array.
    """
    raw = raw.strip()

    # Ensure it starts with [
    if not raw.startswith('['):
        raw = '[' + raw

    # Find last complete object — last occurrence of },
    # which means there's another object after it
    last_complete = raw.rfind('},')
    if last_complete == -1:
        last_complete = raw.rfind('}')

    if last_complete > 0:
        # Cut off anything after the last complete object
        trimmed = raw[:last_complete + 1].rstrip(',').strip()
        if not trimmed.endswith(']'):
            trimmed += ']'
        print(f"✅ JSON recovered: kept content up to position {last_complete}")
        return trimmed

    return raw + ']'


def _validate_questions(questions: list) -> list:
    """Validate each question has required fields."""
    if not isinstance(questions, list) or not questions:
        raise ValueError("Parsed JSON is empty or not a list")

    valid = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in ['question', 'options', 'correct']):
            print(f"⚠️ Q{i} missing fields — skipping")
            continue
        if not isinstance(q['options'], dict) or len(q['options']) < 2:
            continue
        if q['correct'] not in q['options']:
            # Try to fix — use first option
            q['correct'] = list(q['options'].keys())[0]
        if 'explanation' not in q or not q['explanation']:
            q['explanation'] = f"The correct answer is option {q['correct']}."
        valid.append(q)

    if not valid:
        raise ValueError("No valid questions after validation")

    return valid


# ── Adaptive difficulty from DB ────────────────────────────
def _get_difficulty(user_id: int, topic: str) -> str:
    """
    Returns: 'Beginner', 'Intermediate', or 'Advanced'
    """
    # Learning curve stage
    curve = execute_query(
        "SELECT curve_stage FROM learning_curves WHERE user_id=%s AND topic=%s",
        (user_id, topic), fetch=True
    )
    if curve:
        stage = curve[0]['curve_stage']
        if stage in ('Struggling', 'Not Started'):
            return 'Beginner'
        if stage == 'Mastery':
            return 'Advanced'
        if stage in ('Rapid Growth', 'Steady Progress', 'Plateau'):
            return 'Intermediate'

    # topic_difficulty table
    td = execute_query(
        "SELECT difficulty_level, last_score, attempts FROM topic_difficulty WHERE user_id=%s AND topic=%s",
        (user_id, topic), fetch=True
    )
    if td:
        db_level = td[0]['difficulty_level'] or 'Medium'
        score    = float(td[0]['last_score'] or 0)
        attempts = int(td[0]['attempts'] or 0)
        # Adjust based on score
        if score >= 80:
            return 'Advanced'
        if score >= 50:
            return 'Intermediate'
        if score < 50 and attempts >= 1:
            return 'Beginner'
        return DB_TO_LEVEL.get(db_level, 'Intermediate')

    return 'Intermediate'   # default


# ── Build prompt — smaller batches to avoid truncation ────
def _build_prompt(
    content_block : str,
    topic         : str,
    lang          : str,
    level         : str,
    num_questions : int,
    content_source: str,
) -> str:
    lang_instruction = LANGUAGE_PROMPTS.get(lang, LANGUAGE_PROMPTS['en'])
    lang_name        = LANG_NAMES.get(lang, 'English')
    level_cfg        = DIFFICULTY_LEVELS.get(level, DIFFICULTY_LEVELS['Intermediate'])

    source_note = (
        "ALL questions MUST be based ONLY on the video transcript provided above."
        if content_source == 'transcript'
        else f"Generate educational questions about: {topic}"
    )

    return f"""You are an expert educational quiz generator.

LANGUAGE: {lang_instruction}

{source_note}

Content:
{content_block}

DIFFICULTY LEVEL: {level_cfg['label']}
{level_cfg['question_style']}

CRITICAL RULES — READ CAREFULLY:
1. Generate EXACTLY {num_questions} questions
2. Return ONLY a valid complete JSON array
3. Do NOT truncate — complete every object fully
4. Every question must have: question, options (A/B/C/D), correct, explanation
5. No markdown, no extra text — ONLY the JSON array
6. All text in {lang_name} only

REQUIRED JSON FORMAT (copy exactly):
[
  {{
    "question": "question text here?",
    "options": {{
      "A": "first option",
      "B": "second option",
      "C": "third option",
      "D": "fourth option"
    }},
    "correct": "A",
    "explanation": "explanation why A is correct"
  }}
]

Generate exactly {num_questions} complete questions now. Start with [ and end with ]"""


# ============================================================
# MAIN — generate_quiz()
# ============================================================
def generate_quiz(
    video_id     : str,
    video_title  : str,
    topic        : str,
    user_id      : int,
    transcript   : str = '',
    num_questions: int = 10,    # Reduced: 10 per request to avoid truncation
    difficulty   : str = None,  # None = auto-detect
    language     : str = 'en',
) -> dict:
    """
    Generate MCQ quiz with 3-level difficulty system.
    Beginner → Intermediate → Advanced
    """

    # Validate language
    if language not in LANGUAGE_PROMPTS:
        language = 'en'
    if language == 'en' and transcript:
        detected = _detect_language(transcript)
        if detected != 'en':
            language = detected

    # Get difficulty level (Beginner/Intermediate/Advanced)
    if difficulty is None:
        difficulty = _get_difficulty(user_id, topic)
    elif difficulty in DB_TO_LEVEL:
        difficulty = DB_TO_LEVEL[difficulty]

    # Ensure valid level
    if difficulty not in DIFFICULTY_LEVELS:
        difficulty = 'Intermediate'

    print(f"\n[QUIZ] Quiz: topic='{topic}' | level='{difficulty}' | lang='{language}' | transcript={len(transcript)} chars")

    # ── Content source ────────────────────────────────────
    content_source = 'title'
    content_block  = f"Video Title: {video_title}\nTopic: {topic}"

    if transcript and len(transcript.strip()) > 50:
        processed = _preprocess(transcript, max_chars=2500)
        if processed['is_usable']:
            content_source = 'transcript'
            content_block  = (
                f"VIDEO TRANSCRIPT:\n{processed['text']}\n\n"
                f"Topic: {topic}"
            )
            print(f"[OK] Using transcript: {processed['word_count']} words")

    # ── Generate — smaller batch to avoid truncation ──────
    # Generate in batches of 5 if num_questions > 10
    target   = min(num_questions, 20)
    batch    = min(target, 8)   # 8 questions per API call

    all_questions = []
    attempts_left = 3

    while len(all_questions) < target and attempts_left > 0:
        attempts_left -= 1
        needed = min(batch, target - len(all_questions))

        try:
            prompt    = _build_prompt(
                content_block, topic, language, difficulty, needed, content_source
            )
            raw       = _generate(prompt, max_tokens=6000)
            questions = _parse_quiz_json(raw)

            # Avoid duplicate questions
            existing_q = {q['question'].lower() for q in all_questions}
            new_q      = [q for q in questions
                         if q['question'].lower() not in existing_q]
            all_questions.extend(new_q)

            print(f"[OK] Batch done: {len(new_q)} questions | total={len(all_questions)}")

            if len(all_questions) >= target:
                break

        except Exception as e:
            print(f"[WARN] Batch attempt failed: {e}")
            if attempts_left == 0 and not all_questions:
                # Last resort: very simple prompt
                all_questions = _emergency_fallback(
                    topic, content_block, language, difficulty, target
                )
            elif attempts_left == 0:
                break   # Use what we have

    if not all_questions:
        return {'success': False, 'message': 'Quiz generation failed after all attempts'}

    all_questions = all_questions[:target]

    # ── Save to DB ────────────────────────────────────────
    db_difficulty = LEVEL_TO_DB.get(difficulty, 'Medium')
    try:
        quiz_id = execute_query(
            """INSERT INTO video_quizzes
               (user_id, video_id, video_title, topic, questions, total,
                notes_source, transcript_length)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, video_id, video_title, topic,
             json.dumps(all_questions), len(all_questions),
             content_source, len(transcript) if transcript else 0)
        )
        if quiz_id is False:
            # execute_query returns False on failure; retry without newer columns
            quiz_id = execute_query(
                """INSERT INTO video_quizzes
                   (user_id, video_id, video_title, topic, questions, total)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, video_id, video_title, topic,
                 json.dumps(all_questions), len(all_questions))
            )

        # Update topic_difficulty
        execute_query(
            """INSERT INTO topic_difficulty
               (user_id, topic, difficulty_level, last_score, attempts)
               VALUES (%s, %s, %s, 0, 0)
               ON DUPLICATE KEY UPDATE
               difficulty_level = VALUES(difficulty_level)""",
            (user_id, topic, db_difficulty)
        )

        level_cfg = DIFFICULTY_LEVELS[difficulty]
        print(f"[OK] Quiz saved: {len(all_questions)} Qs | level={difficulty} | lang={language} | source={content_source}")

        return {
            'success'        : True,
            'questions'      : all_questions,
            'quiz_id'        : quiz_id,
            'total'          : len(all_questions),
            'difficulty'     : difficulty,
            'difficulty_label': level_cfg['label'],
            'difficulty_color': level_cfg['color'],
            'source'         : content_source,
            'language'       : language,
            'lang_name'      : LANG_NAMES.get(language, 'English'),
        }

    except Exception as e:
        print(f"[ERROR] DB save error: {e}")
        import traceback; traceback.print_exc()
        return {'success': False, 'message': str(e)}


# ── Emergency fallback — minimal questions ─────────────────
def _emergency_fallback(
    topic, content_block, language, difficulty, count
) -> list:
    """Generate a very small quiz when all else fails."""
    print("[EMERGENCY] Emergency fallback — generating 3 questions only")
    lang_name = LANG_NAMES.get(language, 'English')
    simple    = f"""Generate 3 multiple choice questions about: {topic}
Content: {content_block[:400]}
Write in {lang_name}.
Return ONLY JSON:
[{{"question":"Q?","options":{{"A":"opt1","B":"opt2","C":"opt3","D":"opt4"}},"correct":"A","explanation":"reason"}}]"""
    try:
        raw       = _generate(simple, max_tokens=2000)
        questions = _parse_quiz_json(raw)
        return questions[:count]
    except Exception as e:
        print(f"❌ Emergency fallback failed: {e}")
        return []


# ============================================================
# SUBMIT QUIZ — Score + Update Learning Data
# ============================================================
def submit_quiz(
    quiz_id : int,
    user_id : int,
    answers : dict,
    topic   : str,
) -> dict:
    rows = execute_query(
        "SELECT * FROM video_quizzes WHERE id=%s AND user_id=%s",
        (quiz_id, user_id), fetch=True
    )
    if not rows:
        return {'success': False, 'message': 'Quiz not found'}

    questions = json.loads(rows[0]['questions'])
    score     = 0
    results   = []

    for i, q in enumerate(questions):
        user_ans   = answers.get(str(i), '')
        correct    = q['correct']
        is_correct = (user_ans == correct)
        if is_correct:
            score += 1
        results.append({
            'question'   : q['question'],
            'user_answer': user_ans,
            'correct'    : correct,
            'is_correct' : is_correct,
            'explanation': q.get('explanation', ''),
            'options'    : q.get('options', {}),
        })

    total      = len(questions)
    percentage = round((score / total * 100), 1) if total > 0 else 0

    execute_query(
        "UPDATE video_quizzes SET score=%s, attempted=1 WHERE id=%s",
        (score, quiz_id)
    )

    # ── Determine next difficulty level ───────────────────
    # 3-level system: Beginner → Intermediate → Advanced
    if percentage >= 80:
        new_level      = 'Advanced'
        new_db_diff    = 'Hard'
        level_feedback = {
            'icon'   : '🔥',
            'title'  : 'Excellent! Level Up!',
            'message': f'Scored {percentage}%! Next quiz = Advanced level 🔴',
            'color'  : 'success',
            'badge'  : '🔴 Advanced',
        }
    elif percentage >= 50:
        new_level      = 'Intermediate'
        new_db_diff    = 'Medium'
        level_feedback = {
            'icon'   : '💪',
            'title'  : 'Good Job! Keep Going!',
            'message': f'Scored {percentage}%. Continuing at Intermediate level 🟡',
            'color'  : 'warning',
            'badge'  : '🟡 Intermediate',
        }
    else:
        new_level      = 'Beginner'
        new_db_diff    = 'Easy'
        level_feedback = {
            'icon'   : '📚',
            'title'  : 'Keep Practicing!',
            'message': f'Scored {percentage}%. Next quiz = Beginner level 🟢',
            'color'  : 'info',
            'badge'  : '🟢 Beginner',
        }

    # Weak topic detection (< 50%)
    is_weak = percentage < 50
    if is_weak:
        execute_query(
            """INSERT INTO weak_topics (user_id, topic, fail_count)
               VALUES (%s, %s, 1)
               ON DUPLICATE KEY UPDATE
               fail_count    = fail_count + 1,
               last_detected = NOW()""",
            (user_id, topic)
        )

    # Update topic_difficulty
    execute_query(
        """INSERT INTO topic_difficulty
           (user_id, topic, difficulty_level, last_score, attempts)
           VALUES (%s, %s, %s, %s, 1)
           ON DUPLICATE KEY UPDATE
           difficulty_level = %s,
           last_score       = %s,
           attempts         = attempts + 1""",
        (user_id, topic, new_db_diff, percentage, new_db_diff, percentage)
    )

    # Update learning curve
    curve_data = {}
    try:
        from app.ai.learning_curve import LearningCurveModel
        lc         = LearningCurveModel(user_id)
        curve      = lc.save_curve(topic)
        curve_data = {
            'curve_stage'   : curve.get('curve_stage', ''),
            'predicted_next': curve.get('predicted_next', 0),
            'mastery_eta'   : curve.get('mastery_eta', ''),
        }
    except Exception as e:
        print(f"⚠️ Learning curve: {e}")

    # Clear MoE recommendation cache
    try:
        from app.routes.recommend import _cache
        for k in list(_cache.keys()):
            if str(user_id) in k:
                del _cache[k]
    except Exception:
        pass

    print(f"✅ Quiz submitted: {score}/{total} ({percentage}%) | next_level={new_level}")

    return {
        'success'        : True,
        'score'          : score,
        'total'          : total,
        'percentage'     : percentage,
        'results'        : results,
        'is_weak'        : is_weak,
        'topic'          : topic,
        'new_level'      : new_level,
        'new_difficulty' : new_db_diff,
        'difficulty_msg' : level_feedback,
        'curve_stage'    : curve_data.get('curve_stage', ''),
        'predicted_next' : curve_data.get('predicted_next', 0),
        'mastery_eta'    : curve_data.get('mastery_eta', ''),
    }


# ── Cache retrieval ────────────────────────────────────────
def get_saved_quiz(user_id: int, video_id: str) -> dict:
    rows = execute_query(
        """SELECT id, questions, total, notes_source FROM video_quizzes
           WHERE user_id=%s AND video_id=%s AND attempted=0
           ORDER BY created_at DESC LIMIT 1""",
        (user_id, video_id), fetch=True
    )
    if rows:
        return {
            'success'   : True,
            'quiz_id'   : rows[0]['id'],
            'questions' : json.loads(rows[0]['questions']),
            'total'     : rows[0]['total'],
            'source'    : rows[0]['notes_source'],
            'from_cache': True,
        }
    return {'success': False, 'message': 'No saved quiz found'}