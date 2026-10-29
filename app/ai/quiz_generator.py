# ============================================================
# quiz_generator.py — Transcript-Grounded Quiz Generator
# Source: ONLY the video's actual transcript (captions or speech-to-text).
# Output: always English. Every question carries a verbatim quote from the
# transcript, and questions whose quote can't be found in it are discarded.
# The video title / topic are stored for display but never sent to the AI.
# ============================================================

import os
import json
import time
import re
from app.utils.db import execute_query
from app.ai.transcript_extractor import (
    VALID_TRANSCRIPT_SOURCES,
    is_valid_transcript,
    clean_transcript,
)


LANG_NAMES = {'en': 'English', 'ur': 'Urdu', 'hi': 'Hindi', 'sd': 'Sindhi'}

# ── Quiz levels ───────────────────────────────────────────
# Every quiz has exactly ONE level, chosen from the student's past scores
# (see choose_quiz_level). All questions in a quiz are written at that level.
DIFFICULTY_LEVELS = {
    'Easy': {
        'label'      : 'Easy',
        'color'      : '#16a34a',
        'description': 'Recall: facts, terms and definitions stated directly in the video.',
        'score_range': 'Average under 50%',
        'question_style': (
            'EASY: every question tests direct recall of one fact, term or definition the speaker states plainly, '
            'answerable from a single sentence of the transcript. '
            'Typical forms: "What is X?", "Which term does the speaker use for ...?", "What is the first step of ...?". '
            'Wrong options are clearly incorrect according to the transcript.'
        ),
    },
    'Medium': {
        'label'      : 'Medium',
        'color'      : '#d97706',
        'description': 'Understanding: why and how things work, comparing ideas from the video.',
        'score_range': 'Average 50–79%',
        'question_style': (
            'MEDIUM: every question tests understanding of an explanation, not just a remembered word. '
            'Typical forms: "Why does the speaker say ...?", "How does X work according to the video?", '
            '"What is the difference between X and Y as explained?", "What is the purpose of ...?". '
            'Do not ask simple "What is X?" or "Which phase is X in?" recall questions. '
            'Wrong options are plausible but contradicted or unsupported by what the speaker said.'
        ),
    },
    'Hard': {
        'label'      : 'Hard',
        'color'      : '#dc2626',
        'description': 'Analysis: applying ideas, cause and effect, and subtle distinctions from the video.',
        'score_range': 'Average 80% or higher',
        'question_style': (
            'HARD: every question requires reasoning that combines or applies what the speaker explained. '
            'Typical forms: a short scenario ("A team has finished X but skipped Y. According to the video, what problem is most likely?"), '
            '"What would happen if ... based on the explanation in the video?", "Which statement best explains why X leads to Y?", '
            'or "Which option correctly connects X with Y as described?". '
            'Never ask simple recall ("What is X?", "Which phase involves X?", "What document is created in X?"). '
            'The answer must still follow only from the transcript, and the evidence quote must contain the facts that justify it. '
            'Distractors are close to the truth, but only one answer is supported by the transcript.'
        ),
    },
}

# Older data used Beginner / Intermediate / Advanced
DB_TO_LEVEL = {
    'Easy': 'Easy', 'Medium': 'Medium', 'Hard': 'Hard',
    'Beginner': 'Easy', 'Intermediate': 'Medium', 'Advanced': 'Hard',
}
LEVEL_TO_DB = {'Easy': 'Easy', 'Medium': 'Medium', 'Hard': 'Hard'}

# Plain chat models only. Agentic "compound" models are excluded on purpose:
# they can run web searches, which would bring in knowledge from outside the video.
GROQ_MODELS   = ['openai/gpt-oss-120b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-20b']
GEMINI_MODELS = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-flash-latest']

MIN_QUESTIONS = 3


class QuizGenerationError(Exception):
    pass


# ── AI generate function ──────────────────────────────────
def _generate(prompt: str, max_tokens: int = 6000) -> str:
    """Groq first, then Gemini. Asks for a JSON object response."""
    last_error = None
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        for model in GROQ_MODELS:
            try:
                resp = client.chat.completions.create(
                    model           = model,
                    messages        = [
                        {"role": "system", "content": "You write quizzes using only the transcript the user provides. You never use outside knowledge."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens      = max_tokens,
                    temperature     = 0.2,
                    response_format = {"type": "json_object"},
                )
                result = (resp.choices[0].message.content or '').strip()
                if result:
                    print(f"✅ Quiz via Groq: {model}")
                    return result
            except Exception as e:
                last_error = str(e)
                if '429' in last_error or 'rate' in last_error.lower():
                    time.sleep(2)
                elif '401' in last_error or 'invalid_api_key' in last_error.lower():
                    break
    except Exception as e:
        last_error = str(e)

    try:
        from google import genai
        gc = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        for model in GEMINI_MODELS:
            try:
                resp = gc.models.generate_content(
                    model=model, contents=prompt,
                    config={'response_mime_type': 'application/json', 'temperature': 0.2},
                )
                if resp.text:
                    print(f"✅ Quiz via Gemini: {model}")
                    return resp.text.strip()
            except Exception as ge:
                last_error = str(ge)
                if '429' in last_error or 'quota' in last_error.lower():
                    time.sleep(2)
    except Exception as e:
        last_error = str(e)

    raise QuizGenerationError(f"All AI models failed. Last error: {last_error}")


# ── Transcript preparation ────────────────────────────────
def _sample_transcript(text: str, max_chars: int = 18000) -> str:
    """Fit long transcripts into the prompt by sampling the start, middle and end."""
    if len(text) <= max_chars:
        return text
    start = text[: int(max_chars * 0.40)]
    mid_point = len(text) // 2
    mid = text[mid_point - int(max_chars * 0.17): mid_point + int(max_chars * 0.18)]
    end = text[-int(max_chars * 0.25):]
    return f"{start.strip()}\n[...]\n{mid.strip()}\n[...]\n{end.strip()}"


def _detect_language(text: str) -> str:
    if not text:
        return 'en'
    arabic     = len(re.findall(r'[؀-ۿ]', text))
    devanagari = len(re.findall(r'[ऀ-ॿ]', text))
    latin      = len(re.findall(r'[a-zA-Z]', text))
    total      = max(arabic + devanagari + latin, 1)
    if devanagari / total > 0.3:
        return 'hi'
    if arabic / total > 0.3:
        return 'sd' if len(re.findall(r'[ڀ-ڏ]', text)) > 5 else 'ur'
    return 'en'


# ── Grounding check ───────────────────────────────────────
def _normalize(text: str) -> list:
    """Lowercase word tokens (letters/digits in any script), punctuation removed."""
    return re.findall(r'\w+', (text or '').lower())


def _ngrams(tokens: list, n: int = 3) -> set:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


class _Grounding:
    """Checks that a quoted passage really appears in the transcript."""

    def __init__(self, transcript: str):
        self.tokens = _normalize(transcript)
        self.joined = ' ' + ' '.join(self.tokens) + ' '
        self.grams  = _ngrams(self.tokens)

    def supports(self, quote: str) -> bool:
        q = _normalize(quote)
        if len(q) < 5:
            return False
        if (' ' + ' '.join(q) + ' ') in self.joined:
            return True
        # Allow small differences (punctuation, a dropped filler word):
        # most of the quote's 3-word sequences must occur in the transcript.
        grams = _ngrams(q)
        return bool(grams) and len(grams & self.grams) / len(grams) >= 0.75


# ── Response parsing & validation ─────────────────────────
def _parse_questions(raw: str) -> list:
    raw = raw.replace('```json', '').replace('```', '').strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find('['), raw.rfind(']')
        if start == -1 or end <= start:
            raise QuizGenerationError("AI response was not valid JSON")
        data = json.loads(raw[start:end + 1])
    if isinstance(data, dict):
        data = data.get('questions') or next((v for v in data.values() if isinstance(v, list)), [])
    if not isinstance(data, list):
        raise QuizGenerationError("AI response did not contain a question list")
    return data


def _validate(questions: list, grounding: _Grounding, seen: set) -> tuple:
    """Keep only well-formed questions whose evidence quote is in the transcript."""
    kept, dropped = [], 0
    for q in questions:
        if not isinstance(q, dict):
            dropped += 1; continue
        question = str(q.get('question', '')).strip()
        options  = q.get('options')
        correct  = str(q.get('correct', '')).strip().upper()[:1]
        evidence = str(q.get('evidence', '')).strip()

        if (not question or not isinstance(options, dict)
                or set(options.keys()) != {'A', 'B', 'C', 'D'}
                or correct not in options):
            dropped += 1; continue
        values = [str(v).strip() for v in options.values()]
        if any(not v for v in values) or len({v.lower() for v in values}) != 4:
            dropped += 1; continue
        if question.lower() in seen:
            dropped += 1; continue
        if not grounding.supports(evidence):
            dropped += 1; continue

        seen.add(question.lower())
        kept.append({
            'question'   : question,
            'options'    : {k: str(options[k]).strip() for k in ('A', 'B', 'C', 'D')},
            'correct'    : correct,
            'explanation': str(q.get('explanation', '')).strip() or 'This is stated in the video.',
            'evidence'   : evidence,
        })
    return kept, dropped


# ── Quiz level from past scores ───────────────────────────
def level_for_score(avg: float) -> str:
    if avg >= 80:
        return 'Hard'
    if avg >= 50:
        return 'Medium'
    return 'Easy'


def choose_quiz_level(user_id: int, topic: str) -> dict:
    """
    Pick ONE level for the next quiz from the student's past scores:
      1. average of the last 3 quizzes on this topic,
      2. otherwise the average of their last 5 quizzes on any topic,
      3. otherwise the quiz difficulty they chose in Settings (default Medium).
    Returns {'level', 'average', 'basis'}.
    """
    def recent(sql, params):
        rows = execute_query(sql, params, fetch=True) or []
        return [float(r['pct']) for r in rows if r.get('pct') is not None]

    if topic:
        scores = recent(
            """SELECT score/total*100 AS pct FROM video_quizzes
               WHERE user_id=%s AND topic=%s AND attempted=1 AND total>0
               ORDER BY created_at DESC LIMIT 3""", (user_id, topic))
        if scores:
            avg = sum(scores) / len(scores)
            return {'level': level_for_score(avg), 'average': round(avg, 1),
                    'basis': f"your last {len(scores)} quiz{'zes' if len(scores) != 1 else ''} on {topic}"}

    scores = recent(
        """SELECT score/total*100 AS pct FROM video_quizzes
           WHERE user_id=%s AND attempted=1 AND total>0
           ORDER BY created_at DESC LIMIT 5""", (user_id,))
    if scores:
        avg = sum(scores) / len(scores)
        return {'level': level_for_score(avg), 'average': round(avg, 1),
                'basis': f"your last {len(scores)} quiz{'zes' if len(scores) != 1 else ''}"}

    pref = execute_query("SELECT difficulty_level FROM users WHERE id=%s", (user_id,), fetch=True)
    level = DB_TO_LEVEL.get((pref[0]['difficulty_level'] if pref else None) or 'Medium', 'Medium')
    return {'level': level, 'average': None, 'basis': 'the difficulty in your settings (no quiz scores yet)'}


# ── Prompt ────────────────────────────────────────────────
def _build_prompt(transcript_text: str, transcript_lang: str, level: str, num_questions: int, avoid: list) -> str:
    level_cfg = DIFFICULTY_LEVELS.get(level, DIFFICULTY_LEVELS['Medium'])
    if transcript_lang == 'en':
        lang_rule = "Write every question, option and explanation in English."
        quote_rule = "copied word for word from the transcript"
    else:
        name = LANG_NAMES.get(transcript_lang, 'another language')
        lang_rule = (f"The transcript is in {name}. Write every question, option and explanation in English, "
                     f"translating faithfully what the speaker said. Do not add anything they did not say.")
        quote_rule = f"copied word for word from the transcript in its original {name} text (do not translate the quote)"

    avoid_block = ''
    if avoid:
        avoid_block = "\nDo not repeat these questions:\n" + '\n'.join(f"- {a}" for a in avoid[:20]) + '\n'

    return f"""Create a multiple-choice quiz about the lesson in the VIDEO TRANSCRIPT below.

RULES
1. The transcript is your ONLY source. Every question, correct answer and explanation must come from something the speaker actually says in it.
2. Do not use outside knowledge, even if it is true. If something is not in the transcript, do not ask about it.
3. Ask about the lesson's content (concepts, definitions, steps, examples). Do not ask about the speaker, channel, greetings, or what the video "is called".
4. Each question has exactly 4 options labeled A, B, C, D. Exactly one is correct according to the transcript; the other three are clearly wrong according to it.
5. "evidence": a short passage of 8 to 30 words {quote_rule}, which proves the correct answer. It must appear in the transcript exactly.
6. "explanation": one or two sentences in English explaining why the answer is correct, based on that passage.
7. {lang_rule}
8. ONE LEVEL ONLY. This is a {level_cfg['label'].upper()} quiz. {level_cfg['question_style']}
   Every question must be at this same level. Do not include any easier or harder questions, and do not label questions with their own difficulty.
{avoid_block}
Return a JSON object with exactly {num_questions} questions in this shape:
{{"questions": [{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct": "B", "explanation": "...", "evidence": "..."}}]}}

=== VIDEO TRANSCRIPT ===
{transcript_text}
=== END OF TRANSCRIPT ==="""


# ============================================================
# MAIN — generate_quiz()
# ============================================================
def generate_quiz(
    video_id     : str,
    video_title  : str,
    topic        : str,
    user_id      : int,
    transcript   : str,
    source       : str,
    num_questions: int = 10,
    difficulty   : str = None,
) -> dict:
    """
    Generate an English MCQ quiz from the video's actual transcript.
    `transcript` must come from captions or speech-to-text (`source` in
    VALID_TRANSCRIPT_SOURCES); otherwise no quiz is generated.
    `video_title` and `topic` are saved with the quiz but never sent to the AI.
    """
    if source not in VALID_TRANSCRIPT_SOURCES or not is_valid_transcript(transcript):
        return {
            'success': False,
            'transcript_unavailable': True,
            'message': ("We couldn't get this video's transcript, so we can't make a quiz for it. "
                        "Quizzes are only made from what is said in the video."),
        }

    transcript = clean_transcript(transcript)
    transcript_lang = _detect_language(transcript)

    level_info = choose_quiz_level(user_id, topic) if difficulty is None else \
        {'level': DB_TO_LEVEL.get(difficulty, 'Medium'), 'average': None, 'basis': 'requested level'}
    difficulty = level_info['level']

    target = min(max(num_questions, MIN_QUESTIONS), 20)
    print(f"\n[QUIZ] video={video_id} | source={source} | transcript_lang={transcript_lang} | "
          f"level={difficulty} | words={len(transcript.split())}")

    grounding = _Grounding(transcript)      # check quotes against the FULL transcript
    prompt_text = _sample_transcript(transcript)
    questions, seen, last_error = [], set(), None

    for attempt in range(3):
        needed = target - len(questions)
        if needed <= 0:
            break
        try:
            raw = _generate(_build_prompt(prompt_text, transcript_lang, difficulty,
                                          min(needed + 2, 12), [q['question'] for q in questions]))
            kept, dropped = _validate(_parse_questions(raw), grounding, seen)
            questions.extend(kept)
            print(f"[QUIZ] attempt {attempt + 1}: kept {len(kept)}, dropped {dropped} (not grounded or malformed) "
                  f"| total {len(questions)}/{target}")
        except Exception as e:
            last_error = e
            print(f"[QUIZ] attempt {attempt + 1} failed: {e}")

    questions = questions[:target]
    if len(questions) < MIN_QUESTIONS:
        print(f"[QUIZ] Not enough grounded questions ({len(questions)}). Last error: {last_error}")
        return {
            'success': False,
            'message': ("We couldn't make enough questions that are backed by this video's transcript. "
                        "Try again in a moment, or choose another video."),
        }

    db_difficulty = LEVEL_TO_DB.get(difficulty, 'Medium')
    quiz_id = execute_query(
        """INSERT INTO video_quizzes
           (user_id, video_id, video_title, topic, questions, total,
            notes_source, transcript_length, difficulty)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, video_id, video_title, topic, json.dumps(questions, ensure_ascii=False),
         len(questions), source, len(transcript), difficulty)
    )
    if quiz_id is False:
        return {'success': False, 'message': "The quiz was created but couldn't be saved. Try again."}

    execute_query(
        """INSERT INTO topic_difficulty (user_id, topic, difficulty_level, last_score, attempts)
           VALUES (%s, %s, %s, 0, 0)
           ON DUPLICATE KEY UPDATE difficulty_level = VALUES(difficulty_level)""",
        (user_id, topic, db_difficulty)
    )

    level_cfg = DIFFICULTY_LEVELS[difficulty]
    print(f"[QUIZ] Saved quiz {quiz_id}: {len(questions)} transcript-grounded questions")
    return {
        'success'         : True,
        'questions'       : questions,
        'quiz_id'         : quiz_id,
        'total'           : len(questions),
        'difficulty'      : difficulty,
        'difficulty_label': level_cfg['label'],
        'difficulty_color': level_cfg['color'],
        'difficulty_basis': level_info['basis'],
        'source'          : source,
        'language'        : 'en',
        'lang_name'       : 'English',
        'transcript_language': LANG_NAMES.get(transcript_lang, 'English'),
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
    rows = execute_query(
        "SELECT * FROM video_quizzes WHERE id=%s AND user_id=%s",
        (quiz_id, user_id), fetch=True
    )
    if not rows:
        return {'success': False, 'message': 'Quiz not found'}

    questions  = json.loads(rows[0]['questions'])
    topic      = rows[0].get('topic') or topic          # use the quiz's own topic
    quiz_level = DB_TO_LEVEL.get(rows[0].get('difficulty') or '', 'Medium')
    score      = 0
    results    = []

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
            'evidence'   : q.get('evidence', ''),
            'options'    : q.get('options', {}),
        })

    total      = len(questions)
    percentage = round((score / total * 100), 1) if total > 0 else 0

    execute_query(
        "UPDATE video_quizzes SET score=%s, attempted=1 WHERE id=%s",
        (score, quiz_id)
    )

    # Level of the NEXT quiz on this topic: the same rule used when creating quizzes
    # (average of the last 3 scores on the topic, which now includes this one)
    next_info   = choose_quiz_level(user_id, topic)
    new_level   = next_info['level']
    new_db_diff = LEVEL_TO_DB[new_level]
    order       = ['Easy', 'Medium', 'Hard']
    change      = order.index(new_level) - order.index(quiz_level)
    if change > 0:
        title, color = 'Level up', 'success'
        message = f"Your next quiz on {topic} will be {new_level}, based on {next_info['basis']} (average {next_info['average']}%)."
    elif change < 0:
        title, color = 'Next quiz will be easier', 'info'
        message = f"Your next quiz on {topic} will be {new_level}, based on {next_info['basis']} (average {next_info['average']}%)."
    else:
        title, color = f'Staying at {new_level}', 'warning'
        message = f"Your next quiz on {topic} stays {new_level}, based on {next_info['basis']} (average {next_info['average']}%)."
    level_feedback = {'icon': '', 'title': title, 'message': message, 'color': color, 'badge': new_level}

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
        'quiz_level'     : quiz_level,
        'new_level'      : new_level,
        'new_difficulty' : new_db_diff,
        'difficulty_msg' : level_feedback,
        'curve_stage'    : curve_data.get('curve_stage', ''),
        'predicted_next' : curve_data.get('predicted_next', 0),
        'mastery_eta'    : curve_data.get('mastery_eta', ''),
    }


# ── Cache retrieval ────────────────────────────────────────
def get_saved_quiz(user_id: int, video_id: str, level: str = None) -> dict:
    """
    Retrieve unattempted saved quiz from DB cache.
    Strictly verifies the quiz was generated from an authentic transcript source.
    """
    sources = sorted(VALID_TRANSCRIPT_SOURCES)
    rows = execute_query(
        f"""SELECT id, questions, total, notes_source, difficulty FROM video_quizzes
           WHERE user_id=%s AND video_id=%s AND attempted=0
             AND notes_source IN ({', '.join(['%s'] * len(sources))})
             AND (%s IS NULL OR difficulty = %s)
           ORDER BY created_at DESC LIMIT 1""",
        (user_id, video_id, *sources, level, level), fetch=True
    )
    if rows:
        return {
            'success'   : True,
            'quiz_id'   : rows[0]['id'],
            'questions' : json.loads(rows[0]['questions']),
            'total'     : rows[0]['total'],
            'source'    : rows[0]['notes_source'],
            'difficulty': rows[0]['difficulty'],
            'difficulty_label': rows[0]['difficulty'],
            'from_cache': True,
        }
    return {'success': False, 'message': 'No saved transcript-based quiz found'}