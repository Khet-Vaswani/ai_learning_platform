# ============================================================
# quiz_generator.py — AI Quiz Generator
# Sources: Transcript (YouTube captions / Whisper) → Title fallback
# Supports: Adaptive difficulty, Learning curve integration
# ============================================================

import os
import json
import time
import re
from app.utils.db import execute_query


# ── AI generate function ──────────────────────────────────
def _generate(prompt: str, max_tokens: int = 3500) -> str:
    """Try Groq first, fallback to Gemini."""
    from groq import Groq

    GROQ_MODELS = [
        'llama-3.1-8b-instant',
        'llama-3.3-70b-versatile',
        'gemma2-9b-it',
    ]

    client     = Groq(api_key=os.getenv('GROQ_API_KEY'))
    last_error = None

    for model in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model       = model,
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = max_tokens,
                temperature = 0.4,
            )
            result = resp.choices[0].message.content.strip()
            print(f"✅ Quiz via Groq: {model}")
            return result
        except Exception as e:
            err = str(e)
            last_error = err
            if '429' in err or 'rate' in err.lower():
                time.sleep(2)
                continue
            elif '401' in err or 'invalid_api_key' in err.lower():
                break
            continue

    # Gemini fallback
    try:
        from google import genai
        gc   = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        resp = gc.models.generate_content(
            model    = 'gemini-1.5-flash',
            contents = prompt
        )
        print("✅ Quiz via Gemini fallback")
        return resp.text.strip()
    except Exception as e:
        raise Exception(f"All AI models failed. Last: {last_error} | Gemini: {e}")


# ── Text preprocessor ─────────────────────────────────────
def _detect_language(text: str) -> str:
    """Detect the primary language of the content from text script and keywords."""
    if not text or not text.strip():
        return 'English'

    text = text.strip()
    if re.search(r'[\u0900-\u097F]', text):
        return 'Hindi'
    if re.search(r'[\u0600-\u06FF]', text):
        if re.search(r'[ڄڪڍڳڻڦڙ]', text):
            return 'Sindhi'
        return 'Urdu'
    return 'English'


def _preprocess(text: str, max_chars: int = 3500) -> dict:
    """Clean transcript for quiz generation."""
    if not text or len(text.strip()) < 50:
        return {'text': '', 'word_count': 0, 'is_usable': False}

    cleaned = re.sub(r'\[.*?\]', '', text)
    cleaned = re.sub(r'\(.*?\)', '', cleaned)
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)
    cleaned = re.sub(r'SPEAKER\s*\d+\s*:', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'http\S+', '', cleaned)
    cleaned = re.sub(r'\.{3,}', '.', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    sentences = [s.strip() for s in cleaned.split('. ') if len(s.split()) >= 4]
    cleaned   = '. '.join(sentences)
    if cleaned and not cleaned.endswith('.'):
        cleaned += '.'

    if len(cleaned) > max_chars:
        cut = cleaned[:max_chars]
        lp  = cut.rfind('. ')
        if lp > max_chars * 0.7:
            cut = cut[:lp + 1]
        cleaned = cut.strip()

    wc = len(cleaned.split())
    return {
        'text'      : cleaned,
        'word_count': wc,
        'is_usable' : wc >= 50,
    }


def _parse_quiz_json(raw: str) -> list:
    """
    Safely parse quiz JSON from AI response.
    Handles markdown code blocks and extra text.
    """
    # Remove markdown fences
    raw = raw.replace('```json', '').replace('```', '').strip()

    # Extract JSON array
    start = raw.find('[')
    end   = raw.rfind(']') + 1

    if start == -1 or end <= start:
        raise ValueError(f"No JSON array found. Raw response start: {raw[:200]}")

    json_str  = raw[start:end]
    questions = json.loads(json_str)

    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("Parsed JSON is empty or not a list")

    # Validate each question has required fields
    valid = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in ['question', 'options', 'correct']):
            print(f"⚠️ Question {i} missing fields, skipping")
            continue
        if not isinstance(q['options'], dict) or len(q['options']) < 2:
            continue
        # Ensure correct answer exists in options
        if q['correct'] not in q['options']:
            q['correct'] = list(q['options'].keys())[0]
        # Add explanation if missing
        if 'explanation' not in q:
            q['explanation'] = f"The correct answer is {q['correct']}."
        # Validate or assign difficulty to ensure balanced distribution fallback
        if 'difficulty' not in q or q['difficulty'] not in ['Easy', 'Medium', 'Hard']:
            if i < int(len(questions) * 0.4):
                q['difficulty'] = 'Easy'
            elif i < int(len(questions) * 0.8):
                q['difficulty'] = 'Medium'
            else:
                q['difficulty'] = 'Hard'
        valid.append(q)

    return valid


def _get_adaptive_difficulty(user_id: int, topic: str) -> str:
    """Get difficulty from learning curve data."""
    # Check learning curve stage
    curve = execute_query(
        "SELECT curve_stage FROM learning_curves WHERE user_id=%s AND topic=%s",
        (user_id, topic), fetch=True
    )
    if curve:
        stage = curve[0]['curve_stage']
        if stage == 'Struggling':
            return 'Easy'
        elif stage == 'Mastery':
            return 'Hard'
        elif stage in ('Rapid Growth', 'Steady Progress'):
            return 'Medium'

    # Check topic_difficulty table
    td = execute_query(
        "SELECT difficulty_level, last_score, attempts FROM topic_difficulty WHERE user_id=%s AND topic=%s",
        (user_id, topic), fetch=True
    )
    if td:
        score    = float(td[0]['last_score'] or 0)
        attempts = int(td[0]['attempts'] or 0)
        if score >= 80:
            return 'Hard'
        elif score >= 60:
            return 'Medium'
        elif score < 40 and attempts > 1:
            return 'Easy'
        return td[0]['difficulty_level'] or 'Medium'

    return 'Medium'  # default


# ============================================================
# MAIN FUNCTION — Called from gemini.py route
# ============================================================
def generate_quiz(
    video_id     : str,
    video_title  : str,
    topic        : str,
    user_id      : int,
    transcript   : str = '',
    num_questions: int = 20,
    difficulty   : str = None,   # None = auto-detect from DB
) -> dict:
    """
    Generate MCQ quiz from video content.

    Priority:
    1. Transcript (YouTube captions or Whisper) — content-accurate
    2. Video title + topic — fallback

    Returns dict with keys:
        success, questions, quiz_id, total, difficulty, source, message
    """

    # ── Get adaptive difficulty ───────────────────────────
    if difficulty is None:
        difficulty = _get_adaptive_difficulty(user_id, topic)
        print(f"🎯 Adaptive difficulty: {difficulty} for topic '{topic}'")

    # Load student details from DB
    student_category = 'General'
    student_class_dept = 'General'
    student_level = 'Intermediate'
    try:
        user_details = execute_query(
            "SELECT education_category, field_of_interest, skill_level FROM users WHERE id = %s",
            (user_id,), fetch=True
        )
        if user_details:
            student_category = user_details[0].get('education_category') or 'General'
            student_class_dept = user_details[0].get('field_of_interest') or 'General'
            student_level = user_details[0].get('skill_level') or 'Intermediate'
    except Exception as e:
        print(f"⚠️ Error loading student details: {e}")

    language = _detect_language(transcript or video_title or topic)
    language_note = (
        "Use the same language as the source content. Support Sindhi, English, Urdu, and Hindi. "
        "If the transcript is in Sindhi, Urdu, or Hindi, generate questions in that language and preserve the same script."
        if language != 'English' else
        "Use English for the questions."
    )

    # ── Determine content source ──────────────────────────
    content_source = 'title'
    content_block  = f"Video Title: {video_title}\nTopic: {topic}"

    if transcript and len(transcript.strip()) > 150:
        processed = _preprocess(transcript, max_chars=3500)
        if processed['is_usable']:
            content_source = 'transcript'
            content_block  = f"""VIDEO TRANSCRIPT (generate ALL questions from this content):
{processed['text']}

Topic: {topic}"""
            print(f"📝 Quiz using transcript: {processed['word_count']} words")
        else:
            print(f"⚠️ Transcript too short — using title fallback")
    else:
        print(f"⚠️ No transcript — using title fallback")

    # ── Build prompt ──────────────────────────────────────
    prompt = f"""You are an expert AI educational quiz generator.

Your task is to analyze the provided educational transcript/content and generate a high-quality quiz based only on the concepts explained by the tutor. Do not add information that is not present in the provided content.

Student Details:
- Educational Category: {student_category}
- Class/Department: {student_class_dept}
- Learning Level: {student_level}

Topic:
{topic}

Transcript/Content:
{content_block}

Generate a comprehensive quiz according to the student's educational level.

Requirements:

1. Generate {num_questions} multiple-choice questions (MCQs).

2. Each question must include:
   - A clear and meaningful question.
   - Exactly four options (A, B, C, D).
   - Only one correct answer.
   - A short explanation of why the answer is correct.
   - Difficulty level:
     - Easy
     - Medium
     - Hard

3. Adapt the question complexity based on the student's level:
   - Primary students: Use simple language and basic concepts.
   - Secondary/Matriculation: Use moderate-level conceptual questions.
   - Intermediate: Include analytical and application-based questions.
   - University/Professional: Include advanced, critical-thinking, and practical scenario-based questions.

4. Maintain a balanced difficulty distribution:
   - 40% Easy questions
   - 40% Medium questions
   - 20% Hard questions

5. Ensure the quiz evaluates:
   - Concept understanding
   - Logical thinking
   - Application of concepts
   - Important definitions and examples discussed in the content

STRICT RULES:
1. Generate EXACTLY {num_questions} questions.
2. Every question must test a DIFFERENT concept.
3. Questions must be based ONLY on the content provided above.
4. Wrong options (distractors) must be plausible but incorrect.
5. No repeated or similar questions.
6. No trick questions — focus on genuine learning.
7. Language: {language}. {language_note}

Return ONLY a valid JSON array with NO other text, NO markdown:
[
  {{
    "question"   : "What does [specific concept from content] mean?",
    "options"    : {{
      "A": "correct or wrong option",
      "B": "another option",
      "C": "another option",
      "D": "another option"
    }},
    "correct"    : "A",
    "explanation": "Explanation based on the content above",
    "difficulty" : "Easy"
  }}
]

Generate exactly {num_questions} questions now:"""

    # ── Generate via AI ───────────────────────────────────
    try:
        raw = _generate(prompt, max_tokens=3500)

        # Parse JSON
        questions = _parse_quiz_json(raw)

        if len(questions) < 5:
            raise ValueError(
                f"Too few valid questions parsed: {len(questions)}"
            )

        # Limit to requested count
        questions = questions[:num_questions]

        # ── Save to database ──────────────────────────────
        quiz_id = execute_query(
            """INSERT INTO video_quizzes
               (user_id, video_id, video_title, topic, questions, total,
                notes_source, transcript_length)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                video_id,
                video_title,
                topic,
                json.dumps(questions),
                len(questions),
                content_source,
                len(transcript) if transcript else 0,
            )
        )

        # ── Update topic_difficulty ───────────────────────
        execute_query(
            """INSERT INTO topic_difficulty
               (user_id, topic, difficulty_level, last_score, attempts)
               VALUES (%s, %s, %s, 0, 0)
               ON DUPLICATE KEY UPDATE
               difficulty_level = VALUES(difficulty_level)""",
            (user_id, topic, difficulty)
        )

        print(f"✅ Quiz saved: {len(questions)} questions | source='{content_source}' | difficulty='{difficulty}'")

        return {
            'success'   : True,
            'questions' : questions,
            'quiz_id'   : quiz_id,
            'total'     : len(questions),
            'difficulty': difficulty,
            'language'  : language,
            'source'    : content_source,
        }

    except json.JSONDecodeError as e:
        print(f"❌ Quiz JSON parse error: {e}")
        # Retry with simpler prompt
        return _retry_simple_quiz(
            video_id, video_title, topic, user_id,
            content_block, difficulty, num_questions, content_source,
            student_category, student_class_dept, student_level
        )
    except Exception as e:
        print(f"❌ Quiz generation error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': str(e)}


# ── Retry with simpler prompt if JSON fails ───────────────
def _retry_simple_quiz(
    video_id, video_title, topic, user_id,
    content_block, difficulty, num_questions, source,
    student_category, student_class_dept, student_level
) -> dict:
    """Simpler retry prompt when JSON parsing fails."""
    print("🔄 Retrying with simpler prompt...")

    simple_prompt = f"""Generate {num_questions} MCQ questions about: {topic}

Based on: {content_block[:500]}

Student Details:
- Category: {student_category}
- Class/Dept: {student_class_dept}
- Level: {student_level}

Requirements:
- Balanced difficulty: 40% Easy, 40% Medium, 20% Hard.

Return ONLY JSON array:
[
  {{
    "question": "Q?",
    "options": {{"A":"opt1","B":"opt2","C":"opt3","D":"opt4"}},
    "correct": "A",
    "explanation": "reason",
    "difficulty": "Easy"
  }}
]"""

    try:
        raw       = _generate(simple_prompt, max_tokens=3000)
        questions = _parse_quiz_json(raw)

        if questions:
            quiz_id = execute_query(
                """INSERT INTO video_quizzes
                   (user_id, video_id, video_title, topic, questions, total,
                    notes_source, transcript_length)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,0)""",
                (user_id, video_id, video_title, topic,
                 json.dumps(questions), len(questions), source)
            )
            return {
                'success'   : True,
                'questions' : questions,
                'quiz_id'   : quiz_id,
                'total'     : len(questions),
                'difficulty': difficulty,
                'source'    : source,
            }
    except Exception as e:
        print(f"❌ Retry also failed: {e}")

    return {
        'success': False,
        'message': 'Quiz generation failed after retry'
    }


# ============================================================
# SUBMIT QUIZ — Score + Update Learning Data
# ============================================================
def submit_quiz(
    quiz_id : int,
    user_id : int,
    answers : dict,
    topic   : str,
) -> dict:
    """
    Submit quiz answers.
    Updates: video_quizzes, weak_topics, topic_difficulty, learning_curves.
    Returns: score, percentage, results, difficulty feedback.
    """

    # Get quiz from DB
    rows = execute_query(
        "SELECT * FROM video_quizzes WHERE id=%s AND user_id=%s",
        (quiz_id, user_id), fetch=True
    )
    if not rows:
        return {'success': False, 'message': 'Quiz not found'}

    q         = rows[0]
    questions = json.loads(q['questions'])
    score     = 0
    results   = []

    for i, question in enumerate(questions):
        user_ans   = answers.get(str(i), '')
        correct    = question['correct']
        is_correct = (user_ans == correct)
        if is_correct:
            score += 1
        results.append({
            'question'   : question['question'],
            'user_answer': user_ans,
            'correct'    : correct,
            'is_correct' : is_correct,
            'explanation': question.get('explanation', ''),
            'options'    : question.get('options', {}),
            'difficulty' : question.get('difficulty', 'Medium'),
        })

    total      = len(questions)
    percentage = round((score / total * 100), 1) if total > 0 else 0

    # ── Update quiz record ────────────────────────────────
    execute_query(
        "UPDATE video_quizzes SET score=%s, attempted=1 WHERE id=%s",
        (score, quiz_id)
    )

    # ── Detect weak topic (< 60%) ─────────────────────────
    is_weak = percentage < 60
    if is_weak:
        execute_query(
            """INSERT INTO weak_topics (user_id, topic, fail_count)
               VALUES (%s, %s, 1)
               ON DUPLICATE KEY UPDATE
               fail_count    = fail_count + 1,
               last_detected = CURRENT_TIMESTAMP""",
            (user_id, topic)
        )

    # ── Update difficulty for next quiz ───────────────────
    if percentage >= 80:
        new_difficulty = 'Hard'
    elif percentage >= 50:
        new_difficulty = 'Medium'
    else:
        new_difficulty = 'Easy'

    execute_query(
        """INSERT INTO topic_difficulty
           (user_id, topic, difficulty_level, last_score, attempts)
           VALUES (%s, %s, %s, %s, 1)
           ON DUPLICATE KEY UPDATE
           difficulty_level = %s,
           last_score       = %s,
           attempts         = attempts + 1""",
        (user_id, topic, new_difficulty, percentage,
         new_difficulty, percentage)
    )

    # ── Update learning curve ─────────────────────────────
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
        print(f"⚠️ Learning curve update error: {e}")

    # ── Difficulty message ────────────────────────────────
    if percentage >= 80:
        diff_msg = {
            'icon'   : '🔥',
            'title'  : 'Excellent! Level Up!',
            'message': f'Scored {percentage}%! Next quiz = HARD level',
            'color'  : 'success'
        }
    elif percentage >= 60:
        diff_msg = {
            'icon'   : '💪',
            'title'  : 'Good Job!',
            'message': f'Scored {percentage}%. Keeping MEDIUM level.',
            'color'  : 'warning'
        }
    else:
        diff_msg = {
            'icon'   : '📚',
            'title'  : 'Keep Practicing!',
            'message': f'Scored {percentage}%. Next quiz = EASIER level.',
            'color'  : 'info'
        }

    # ── Clear MoE cache so dashboard refreshes ────────────
    try:
        from app.routes.recommend import _cache
        keys = [k for k in _cache if str(user_id) in k]
        for k in keys:
            del _cache[k]
    except Exception:
        pass

    print(f"✅ Quiz submitted: {score}/{total} ({percentage}%) | weak={is_weak} | next_diff={new_difficulty}")

    return {
        'success'       : True,
        'score'         : score,
        'total'         : total,
        'percentage'    : percentage,
        'results'       : results,
        'is_weak'       : is_weak,
        'topic'         : topic,
        'new_difficulty': new_difficulty,
        'difficulty_msg': diff_msg,
        'curve_stage'   : curve_data.get('curve_stage', ''),
        'predicted_next': curve_data.get('predicted_next', 0),
        'mastery_eta'   : curve_data.get('mastery_eta', ''),
    }


# ============================================================
# GET SAVED QUIZ — retrieve from DB
# ============================================================
def get_saved_quiz(user_id: int, video_id: str) -> dict:
    """Retrieve most recent unattempted quiz from database."""
    rows = execute_query(
        """SELECT id, questions, total, notes_source, created_at
           FROM video_quizzes
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