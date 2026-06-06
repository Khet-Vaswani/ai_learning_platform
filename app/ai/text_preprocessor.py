# ============================================================
# text_preprocessor.py
# Cleans and prepares transcript for AI generation
# ============================================================

import re


def preprocess_transcript(text: str, max_chars: int = 4000) -> dict:
    """
    Clean and prepare transcript for AI input.
    Returns dict with cleaned text and metadata.
    """
    if not text or len(text.strip()) < 50:
        return {
            'text'       : '',
            'word_count' : 0,
            'is_usable'  : False,
            'quality'    : 'empty'
        }

    # ── Step 1: Basic cleaning ────────────────────────────
    # Remove filler words common in transcripts
    fillers = [
        r'\bum+\b', r'\buh+\b', r'\byou know\b', r'\blike\b',
        r'\bright\b', r'\bokay so\b', r'\balright\b',
        r'\bso basically\b',
    ]
    cleaned = text
    for f in fillers:
        cleaned = re.sub(f, '', cleaned, flags=re.IGNORECASE)

    # Remove timestamps like [00:01:30]
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)

    # Remove speaker labels like "SPEAKER 1:"
    cleaned = re.sub(r'SPEAKER\s*\d+\s*:', '', cleaned, flags=re.IGNORECASE)

    # Remove repeated punctuation
    cleaned = re.sub(r'\.{3,}', '.', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # ── Step 2: Sentence boundary improvement ────────────
    # Ensure space after periods
    cleaned = re.sub(r'\.([A-Z])', r'. \1', cleaned)

    # ── Step 3: Remove very short sentences (< 3 words) ──
    sentences = cleaned.split('. ')
    sentences = [s.strip() for s in sentences if len(s.split()) >= 3]
    cleaned   = '. '.join(sentences).strip()

    if cleaned and not cleaned.endswith('.'):
        cleaned += '.'

    # ── Step 4: Truncate intelligently ───────────────────
    truncated = smart_truncate(cleaned, max_chars)

    word_count = len(truncated.split())

    # ── Step 5: Quality assessment ───────────────────────
    if word_count < 50:
        quality = 'poor'
    elif word_count < 200:
        quality = 'fair'
    elif word_count < 500:
        quality = 'good'
    else:
        quality = 'excellent'

    return {
        'text'      : truncated,
        'word_count': word_count,
        'is_usable' : word_count >= 50,
        'quality'   : quality,
        'original_length': len(text),
        'cleaned_length' : len(cleaned),
    }


def smart_truncate(text: str, max_chars: int) -> str:
    """
    Truncate text at sentence boundary, not mid-sentence.
    """
    if len(text) <= max_chars:
        return text

    # Cut at max_chars
    truncated = text[:max_chars]

    # Find last sentence ending
    last_period = truncated.rfind('. ')
    if last_period > max_chars * 0.7:
        truncated = truncated[:last_period + 1]

    return truncated.strip()


def extract_key_sentences(text: str, max_sentences: int = 20) -> str:
    """
    For very long transcripts — extract most important sentences
    using simple keyword frequency scoring.
    """
    if not text:
        return ''

    sentences = [s.strip() for s in text.split('. ') if len(s.split()) >= 5]
    if len(sentences) <= max_sentences:
        return text

    # Score by word frequency (simple TF approach)
    from collections import Counter
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    # Exclude common stopwords
    stops = {'this','that','with','have','from','they','will','been',
             'were','their','what','when','which','then','than','more'}
    word_freq = Counter(w for w in words if w not in stops)

    scored = []
    for i, sent in enumerate(sentences):
        sent_words = re.findall(r'\b[a-zA-Z]{4,}\b', sent.lower())
        score      = sum(word_freq.get(w, 0) for w in sent_words)
        # Boost first and last sentences (usually important)
        if i < 3 or i >= len(sentences) - 3:
            score *= 1.5
        scored.append((score, i, sent))

    # Sort by score, keep top N, then re-sort by original order
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    top = sorted(top, key=lambda x: x[1])

    return '. '.join(s for _, _, s in top) + '.'