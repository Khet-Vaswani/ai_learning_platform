# ============================================================
# pipeline.py — Main AI Pipeline Orchestrator
# Coordinates: transcript → preprocess → notes/quiz generation
# ============================================================

import os
import json
import time
from app.utils.db import execute_query
from app.ai.transcript_extractor import extract_transcript_full_pipeline
from app.ai.text_preprocessor    import preprocess_transcript, extract_key_sentences


# ── Shared AI generate function ───────────────────────────
def generate_ai(prompt: str, max_tokens: int = 2000) -> str:
    """Try Groq first, fallback to Gemini."""
    from groq import Groq
    groq_models = [
        'llama-3.1-8b-instant',
        'llama-3.3-70b-versatile',
        'gemma2-9b-it',
    ]
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))

    for model in groq_models:
        try:
            resp = client.chat.completions.create(
                model    = model,
                messages = [{"role": "user", "content": prompt}],
                max_tokens  = max_tokens,
                temperature = 0.3,     # lower = more focused/accurate
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if '429' in err or 'rate' in err.lower():
                time.sleep(2)
                continue
            elif '401' in err:
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
        return resp.text.strip()
    except Exception as e:
        raise Exception(f"All AI models failed: {e}")


# ============================================================
# NOTES GENERATION
# ============================================================
def generate_notes_from_content(
    video_id   : str,
    video_title: str,
    topic      : str,
    user_id    : int,
    transcript : str = '',
    source     : str = 'title'
) -> dict:
    """
    Generate structured study notes.
    Uses transcript if available, otherwise video title.
    """

    # Preprocess transcript
    if transcript and len(transcript.strip()) > 100:
        processed = preprocess_transcript(transcript, max_chars=4000)

        if processed['is_usable']:
            # For very long transcripts, extract key sentences
            content_text = processed['text']
            if processed['word_count'] > 800:
                content_text = extract_key_sentences(
                    processed['text'], max_sentences=30
                )

            content_block = f"""
VIDEO TRANSCRIPT (actual tutor speech — use this as primary source):
{content_text}

Video Title: {video_title}
Topic: {topic}
"""
            content_source = source  # 'youtube_captions', 'whisper', etc.
            print(f"✅ Notes from transcript ({processed['word_count']} words)")
        else:
            content_block  = f"Video Title: {video_title}\nTopic: {topic}"
            content_source = 'title'
    else:
        content_block  = f"Video Title: {video_title}\nTopic: {topic}"
        content_source = 'title'

    prompt = f"""You are an expert educational note-taker for students.

Generate comprehensive, accurate study notes based on this content:
{content_block}

STRICT RULES:
1. Base notes ONLY on the content provided above
2. Do NOT add information not present in the transcript
3. If using transcript — extract exact concepts the tutor explained
4. Use clear, student-friendly language

Format EXACTLY as follows (use these exact headings):

## 📌 Topic Overview
[2-3 sentences summarizing what this lesson covers]

## 🔑 Key Concepts
- **Concept 1**: explanation
- **Concept 2**: explanation
- **Concept 3**: explanation
- **Concept 4**: explanation
- **Concept 5**: explanation

## 📖 Important Definitions
- **Term 1**: definition
- **Term 2**: definition
- **Term 3**: definition

## 💡 Examples & Applications
- Example 1: practical example from the lesson
- Example 2: practical example from the lesson

## ⚡ Key Takeaways
- Takeaway 1
- Takeaway 2
- Takeaway 3
- Takeaway 4

## 📝 Summary
[4-5 sentences summarizing the complete lesson]

Total notes should be 400-600 words."""

    try:
        notes = generate_ai(prompt, max_tokens=1800)

        # Save to database
        execute_query(
            """INSERT INTO video_notes
               (user_id, video_id, video_title, topic, notes,
                notes_source, transcript_used, word_count)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               notes            = VALUES(notes),
               notes_source     = VALUES(notes_source),
               transcript_used  = VALUES(transcript_used),
               word_count       = VALUES(word_count),
               updated_at       = NOW()""",
            (user_id, video_id, video_title, topic,
             notes, content_source,
             transcript[:1000] if transcript else '',
             len(notes.split()))
        )

        return {
            'success'   : True,
            'notes'     : notes,
            'source'    : content_source,
            'word_count': len(notes.split())
        }

    except Exception as e:
        print(f"❌ Notes generation error: {e}")
        return {'success': False, 'message': str(e)}


# ============================================================
# QUIZ GENERATION
# ============================================================
def generate_quiz_from_content(
    video_id   : str,
    video_title: str,
    topic      : str,
    user_id    : int,
    transcript : str   = '',
    source     : str   = 'title',
    difficulty : str   = 'Medium',
    num_questions: int = 20
) -> dict:
    """
    Generate MCQ quiz from video content.
    """

    diff_guide = {
        'Easy'  : 'Basic recall questions — definitions and simple facts.',
        'Medium': 'Understanding questions — concepts and applications.',
        'Hard'  : 'Analysis questions — comparisons, scenarios, advanced concepts.'
    }

    # Build content source
    if transcript and len(transcript.strip()) > 100:
        processed = preprocess_transcript(transcript, max_chars=3500)
        if processed['is_usable']:
            content_text  = processed['text']
            content_block = f"""
VIDEO TRANSCRIPT (base all questions on this content):
{content_text}

Topic: {topic}
"""
            print(f"✅ Quiz from transcript ({processed['word_count']} words)")
        else:
            content_block = f"Video Title: {video_title}\nTopic: {topic}"
    else:
        content_block = f"Video Title: {video_title}\nTopic: {topic}"

    prompt = f"""You are an expert educational quiz generator.

Generate exactly {num_questions} multiple-choice questions based on:
{content_block}

Difficulty: {difficulty} — {diff_guide.get(difficulty, diff_guide['Medium'])}

STRICT RULES:
1. ALL questions must be based on the content above
2. Do NOT add questions about things not covered in the content
3. Each question must test a DIFFERENT concept
4. Wrong options must be plausible but clearly incorrect on reflection
5. No trick questions — focus on learning

Return ONLY a valid JSON array. No markdown, no extra text:
[
  {{
    "question"   : "Clear question text?",
    "options"    : {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}},
    "correct"    : "A",
    "explanation": "Why A is correct based on the content"
  }}
]"""

    try:
        raw   = generate_ai(prompt, max_tokens=3500)
        raw   = raw.replace('```json', '').replace('```', '').strip()

        # Extract JSON array
        start = raw.find('[')
        end   = raw.rfind(']') + 1
        if start == -1 or end <= start:
            raise ValueError("No JSON array found in response")

        questions = json.loads(raw[start:end])[:num_questions]

        if not questions:
            raise ValueError("Empty questions list")

        # Save to database
        from app.ai.quiz_generator import _save_quiz_to_db
        quiz_id = _save_quiz_to_db(user_id, video_id, video_title, topic, questions, source, transcript)

        if not quiz_id or isinstance(quiz_id, bool):
            return {'success': False, 'message': 'Failed to save quiz record'}

        return {
            'success'   : True,
            'questions' : questions,
            'quiz_id'   : quiz_id,
            'total'     : len(questions),
            'difficulty': difficulty,
            'source'    : source
        }

    except json.JSONDecodeError as e:
        print(f"❌ Quiz JSON parse error: {e}")
        print(f"   Raw response: {raw[:300]}")
        return {'success': False, 'message': 'Failed to parse quiz JSON'}
    except Exception as e:
        print(f"❌ Quiz generation error: {e}")
        return {'success': False, 'message': str(e)}


# ============================================================
# FULL PIPELINE — Called from routes
# ============================================================
def run_full_pipeline(
    video_id   : str,
    video_title: str,
    topic      : str,
    user_id    : int,
    action     : str = 'both',   # 'notes', 'quiz', or 'both'
    difficulty : str = 'Medium',
    use_whisper: bool = False,   # Set True if GPU available
) -> dict:
    """
    Main entry point — runs full pipeline:
    1. Extract transcript
    2. Preprocess
    3. Generate notes and/or quiz
    """

    print(f"\n🚀 Pipeline start: {video_id} | action={action}")

    # Step 1: Extract transcript
    transcript_result = extract_transcript_full_pipeline(
        video_id    = video_id,
        video_title = video_title,
        use_whisper = use_whisper
    )
    transcript = transcript_result.get('transcript', '')
    source     = transcript_result.get('source', 'title')

    print(f"   Transcript: {len(transcript)} chars from '{source}'")

    result = {'transcript_source': source}

    # Step 2: Generate notes
    if action in ('notes', 'both'):
        notes_result = generate_notes_from_content(
            video_id    = video_id,
            video_title = video_title,
            topic       = topic,
            user_id     = user_id,
            transcript  = transcript,
            source      = source
        )
        result['notes'] = notes_result

    # Step 3: Generate quiz
    if action in ('quiz', 'both'):
        # Get difficulty from DB
        td = execute_query(
            "SELECT difficulty_level FROM topic_difficulty WHERE user_id=%s AND topic=%s",
            (user_id, topic), fetch=True
        )
        if td:
            difficulty = td[0]['difficulty_level']

        quiz_result = generate_quiz_from_content(
            video_id    = video_id,
            video_title = video_title,
            topic       = topic,
            user_id     = user_id,
            transcript  = transcript,
            source      = source,
            difficulty  = difficulty
        )
        result['quiz'] = quiz_result

    print(f"✅ Pipeline complete: {video_id}")
    return result