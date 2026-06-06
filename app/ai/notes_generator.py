# ============================================================
# notes_generator.py — AI Study Notes Generator
# Sources: Transcript (YouTube captions / Whisper) → Title fallback
# ============================================================

import os
import time
import re
from app.utils.db import execute_query


# ── AI generate function ──────────────────────────────────
def _generate(prompt: str, max_tokens: int = 2000) -> str:
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
                temperature = 0.3,
            )
            result = resp.choices[0].message.content.strip()
            print(f"✅ Notes via Groq: {model}")
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
        print("✅ Notes via Gemini fallback")
        return resp.text.strip()
    except Exception as e:
        raise Exception(f"All AI models failed. Last: {last_error} | Gemini: {e}")


# ── Text preprocessor (inline — no external dep needed) ──
def _preprocess(text: str, max_chars: int = 4000) -> dict:
    """Clean transcript text for AI input."""
    if not text or len(text.strip()) < 50:
        return {'text': '', 'word_count': 0, 'is_usable': False}

    import re

    # Remove noise
    cleaned = re.sub(r'\[.*?\]', '', text)          # [Music], [Applause]
    cleaned = re.sub(r'\(.*?\)', '', cleaned)        # (laughter)
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)  # timestamps
    cleaned = re.sub(r'SPEAKER\s*\d+\s*:', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'http\S+', '', cleaned)        # URLs
    cleaned = re.sub(r'\.{3,}', '.', cleaned)        # ...
    cleaned = re.sub(r'\s+', ' ', cleaned)           # multiple spaces
    cleaned = re.sub(r'\.([A-Z])', r'. \1', cleaned) # fix spacing

    # Remove too-short sentences
    sentences = [s.strip() for s in cleaned.split('. ') if len(s.split()) >= 4]
    cleaned   = '. '.join(sentences)
    if cleaned and not cleaned.endswith('.'):
        cleaned += '.'

    # Smart truncate at sentence boundary
    if len(cleaned) > max_chars:
        cut   = cleaned[:max_chars]
        lp    = cut.rfind('. ')
        if lp > max_chars * 0.7:
            cut = cut[:lp + 1]
        cleaned = cut.strip()

    wc = len(cleaned.split())
    return {
        'text'      : cleaned,
        'word_count': wc,
        'is_usable' : wc >= 50,
    }


def _format_notes_html(raw_notes: str) -> str:
    """Convert markdown notes to clean HTML for display."""
    html = raw_notes

    # H2 headings
    html = re.sub(
        r'^## (.+)$',
        r'<h6 class="fw-bold mt-3 mb-2" style="color:#2563eb;">\1</h6>',
        html, flags=re.MULTILINE
    )
    # Bold text
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # Bullet points
    html = re.sub(
        r'^- (.+)$',
        r'<li style="margin-left:14px;font-size:.83rem;margin-bottom:4px;">\1</li>',
        html, flags=re.MULTILINE
    )
    # Newlines to breaks (but not inside li)
    html = html.replace('\n\n', '<br>')

    return html


# ============================================================
# MAIN FUNCTION — Called from gemini.py route
# ============================================================
def generate_notes(
    video_id   : str,
    video_title: str,
    topic      : str,
    user_id    : int,
    transcript : str = '',
) -> dict:
    """
    Generate structured study notes.

    Priority:
    1. Transcript (YouTube captions or Whisper) — most accurate
    2. Video title + topic — fallback

    Returns dict with keys:
        success, notes, notes_html, source, word_count, message
    """

    # ── Determine content source ──────────────────────────
    content_source = 'title'
    content_block  = f"Video Title: {video_title}\nTopic: {topic}"

    if transcript and len(transcript.strip()) > 150:
        processed = _preprocess(transcript, max_chars=4000)

        if processed['is_usable']:
            content_source = 'transcript'
            content_block  = f"""VIDEO TRANSCRIPT (actual tutor explanation — use as primary source):
{processed['text']}

Video Title: {video_title}
Topic: {topic}"""
            print(f"📝 Notes using transcript: {processed['word_count']} words")
        else:
            print(f"⚠️ Transcript too short ({processed['word_count']} words) — using title")
    else:
        print(f"⚠️ No transcript available — using title fallback")

    # ── Build prompt ──────────────────────────────────────
    source_instruction = (
        "Base ALL notes ONLY on the transcript content above. "
        "Extract the exact concepts and explanations the tutor gave."
        if content_source == 'transcript'
        else
        "Generate comprehensive educational notes about this topic for students."
    )

    prompt = f"""You are an expert educational note-taker helping students study.

{source_instruction}

Content:
{content_block}

RULES:
1. Write notes ONLY based on the content provided
2. Use clear, student-friendly language
3. Be specific — use actual terms from the content
4. Structure must follow the EXACT format below

Generate study notes using EXACTLY this format:

## 📌 Topic Overview
[2-3 sentences explaining what this lesson is about]

## 🔑 Key Concepts
- **[Concept Name]**: [clear explanation]
- **[Concept Name]**: [clear explanation]
- **[Concept Name]**: [clear explanation]
- **[Concept Name]**: [clear explanation]
- **[Concept Name]**: [clear explanation]

## 📖 Important Definitions
- **[Term]**: [precise definition]
- **[Term]**: [precise definition]
- **[Term]**: [precise definition]

## 💡 Examples & Applications
- [Practical example from the lesson]
- [Practical example from the lesson]

## ⚡ Key Takeaways
- [Important point 1]
- [Important point 2]
- [Important point 3]
- [Important point 4]

## 📝 Summary
[4-5 sentences summarizing everything covered in this lesson]

Notes should be 400-600 words total. Be specific and educational."""

    # ── Generate via AI ───────────────────────────────────
    try:
        raw_notes = _generate(prompt, max_tokens=2000)

        if not raw_notes or len(raw_notes) < 100:
            raise ValueError("AI returned empty or too-short notes")

        # Convert to HTML for display
        notes_html = _format_notes_html(raw_notes)

        # ── Save to database ──────────────────────────────
        wc = len(raw_notes.split())
        execute_query(
            """INSERT INTO video_notes
               (user_id, video_id, video_title, topic, notes,
                notes_source, transcript_used, word_count)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               notes           = VALUES(notes),
               notes_source    = VALUES(notes_source),
               transcript_used = VALUES(transcript_used),
               word_count      = VALUES(word_count),
               updated_at      = NOW()""",
            (
                user_id,
                video_id,
                video_title,
                topic,
                raw_notes,
                content_source,
                transcript[:500] if transcript else '',
                wc
            )
        )

        print(f"✅ Notes saved: {wc} words from '{content_source}'")

        return {
            'success'   : True,
            'notes'     : raw_notes,
            'notes_html': notes_html,
            'source'    : content_source,
            'word_count': wc,
        }

    except Exception as e:
        print(f"❌ Notes generation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e),
            'source' : content_source,
        }


# ============================================================
# GET SAVED NOTES — retrieve from DB
# ============================================================
def get_saved_notes(user_id: int, video_id: str) -> dict:
    """Retrieve previously generated notes from database."""
    rows = execute_query(
        """SELECT notes, notes_source, word_count, created_at
           FROM video_notes
           WHERE user_id=%s AND video_id=%s
           ORDER BY created_at DESC LIMIT 1""",
        (user_id, video_id), fetch=True
    )
    if rows:
        raw   = rows[0]['notes']
        return {
            'success'   : True,
            'notes'     : raw,
            'notes_html': _format_notes_html(raw),
            'source'    : rows[0]['notes_source'],
            'word_count': rows[0]['word_count'],
            'from_cache': True,
        }
    return {'success': False, 'message': 'No saved notes found'}