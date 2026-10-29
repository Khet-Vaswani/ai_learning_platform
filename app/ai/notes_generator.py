# ============================================================
# notes_generator.py — AI Study Notes Generator
# Source: ONLY the video transcript (captions / speech-to-text). Output: English.
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
        'openai/gpt-oss-120b',
        'qwen/qwen3.8-27b',
        'openai/gpt-oss-20b',
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
            print(f"[OK] Notes via Groq: {model}")
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
                print(f"[OK] Notes via Gemini fallback: {model}")
                return resp.text.strip()
            except Exception as ge:
                err = str(ge)
                if '429' in err or 'quota' in err.lower():
                    time.sleep(2)
                    continue
                continue
    except Exception as e:
        raise Exception(f"All AI models failed. Last: {last_error} | Gemini: {e}")
    raise Exception(f"All AI models failed. Last: {last_error}")


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


def _detect_language(text: str) -> str:
    """Detect the primary language of the content from text script and keywords."""
    if not text or not text.strip():
        return 'English'

    text = text.strip()

    # Hindi uses Devanagari script
    if re.search(r'[\u0900-\u097F]', text):
        return 'Hindi'

    # Arabic-based scripts for Urdu/Sindhi
    if re.search(r'[\u0600-\u06FF]', text):
        # Sindhi-specific characters
        if re.search(r'[ڄڪڍڳڻڦڙ]', text):
            return 'Sindhi'
        return 'Urdu'

    return 'English'


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
    transcript : str,
    source     : str,
) -> dict:
    """
    Generate English study notes from the video's actual transcript only.
    `video_title` and `topic` are never sent to the AI.
    Returns dict with keys: success, notes, notes_html, source, word_count, message
    """
    from app.ai.transcript_extractor import VALID_TRANSCRIPT_SOURCES, is_valid_transcript

    if source not in VALID_TRANSCRIPT_SOURCES or not is_valid_transcript(transcript):
        return {
            'success': False,
            'transcript_unavailable': True,
            'message': ("We couldn't get this video's transcript, so we can't make notes for it. "
                        "Notes are only made from what is said in the video."),
        }

    processed = _preprocess(transcript, max_chars=12000)
    if not processed['is_usable']:
        return {
            'success': False,
            'transcript_unavailable': True,
            'message': "This video's transcript is too short to make useful notes.",
        }

    language = _detect_language(transcript)
    lang_rule = ("Write the notes in English." if language == 'English' else
                 f"The transcript is in {language}. Write the notes in English, translating faithfully "
                 f"what the speaker said. Do not add anything they did not say.")

    prompt = f"""You are writing study notes for a student, using ONLY the video transcript below.

RULES
1. Use only what the speaker says in the transcript. Do not add outside facts, even if they are true.
2. If a section below has nothing in the transcript to support it, write "Not covered in this video."
3. {lang_rule}
4. Use clear, student-friendly language and the speaker's own terms.

=== VIDEO TRANSCRIPT ===
{processed['text']}
=== END OF TRANSCRIPT ===

Write the notes in EXACTLY this format:

## 📌 Topic Overview
[2-3 sentences on what this lesson covers]

## 🔑 Key Concepts
- **[Concept]**: [explanation as given in the video]
(3 to 6 items)

## 📖 Important Definitions
- **[Term]**: [definition as given in the video]

## 💡 Examples & Applications
- [Example the speaker used]

## ⚡ Key Takeaways
- [Point from the video]
(3 to 5 items)

## 📝 Summary
[3-5 sentences summarizing the lesson]

Keep the notes between 300 and 600 words."""

    try:
        raw_notes = _generate(prompt, max_tokens=2500)
        if not raw_notes or len(raw_notes) < 100:
            raise ValueError("AI returned empty or too-short notes")

        wc = len(raw_notes.split())
        saved = execute_query(
            """INSERT INTO video_notes (user_id, video_id, notes, notes_source, word_count)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               notes        = VALUES(notes),
               notes_source = VALUES(notes_source),
               word_count   = VALUES(word_count),
               generated_at = NOW()""",
            (user_id, video_id, raw_notes, source, wc)
        )
        if saved is False:
            print("⚠️ Notes generated but could not be saved to the database")

        print(f"✅ Notes: {wc} words from transcript [{source}]")
        return {
            'success'   : True,
            'notes'     : raw_notes,
            'notes_html': _format_notes_html(raw_notes),
            'source'    : source,
            'language'  : 'English',
            'transcript_language': language,
            'word_count': wc,
        }

    except Exception as e:
        print(f"❌ Notes generation failed: {e}")
        return {'success': False, 'message': "We couldn't generate notes right now. Try again in a moment."}


# ============================================================
# GET SAVED NOTES — retrieve from DB
# ============================================================
def get_saved_notes(user_id: int, video_id: str) -> dict:
    """Return previously generated transcript-based notes, or {'success': False}."""
    from app.ai.transcript_extractor import VALID_TRANSCRIPT_SOURCES
    sources = sorted(VALID_TRANSCRIPT_SOURCES)
    rows = execute_query(
        f"""SELECT notes, notes_source, word_count
           FROM video_notes
           WHERE user_id=%s AND video_id=%s
             AND notes_source IN ({', '.join(['%s'] * len(sources))})
           ORDER BY generated_at DESC LIMIT 1""",
        (user_id, video_id, *sources), fetch=True
    )
    if rows:
        raw = rows[0]['notes']
        return {
            'success'   : True,
            'notes'     : raw,
            'notes_html': _format_notes_html(raw),
            'source'    : rows[0]['notes_source'],
            'word_count': rows[0]['word_count'],
            'from_cache': True,
        }
    return {'success': False}
