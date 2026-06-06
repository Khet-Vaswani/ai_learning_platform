# ============================================================
# transcript_extractor.py
# Extracts transcript from YouTube videos
# Sources: YouTube captions → Whisper → Description fallback
# ============================================================

import os
import re
from app.utils.db import execute_query


def clean_transcript(text: str) -> str:
    """Remove noise from transcript text."""
    if not text:
        return ''
    # Remove music tags, [applause], etc.
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    # Remove multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    return text.strip()


def get_cached_transcript(video_id: str):
    """Check DB cache first."""
    rows = execute_query(
        "SELECT transcript_text, source FROM video_transcripts WHERE video_id=%s",
        (video_id,), fetch=True
    )
    if rows:
        return {
            'transcript': rows[0]['transcript_text'],
            'source'    : rows[0]['source'],
            'cached'    : True
        }
    return None


def save_transcript_cache(video_id: str, text: str, source: str):
    """Save transcript to DB cache."""
    word_count = len(text.split())
    execute_query(
        """INSERT INTO video_transcripts
           (video_id, transcript_text, source, word_count)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE
           transcript_text = VALUES(transcript_text),
           source          = VALUES(source),
           word_count      = VALUES(word_count)""",
        (video_id, text, source, word_count)
    )


def extract_youtube_captions(video_id: str) -> dict:
    """
    Try to get YouTube auto-captions or manual captions.
    Returns dict with transcript text and source.
    """
    # Check cache first
    cached = get_cached_transcript(video_id)
    if cached:
        print(f"✅ Transcript from cache: {video_id}")
        return cached

    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable
        )

        # Try multiple language preferences
        languages = ['en', 'en-US', 'en-GB', 'en-IN', 'a.en']

        transcript_list = None
        source = 'youtube_captions'

        try:
            # Try manual captions first (more accurate)
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, languages=languages
            )
        except NoTranscriptFound:
            # Try auto-generated captions
            try:
                all_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                auto = all_transcripts.find_generated_transcript(['en'])
                transcript_list = auto.fetch()
                source = 'youtube_auto_captions'
            except Exception:
                pass

        if transcript_list:
            # Join all segments
            full_text = ' '.join([
                seg['text'] for seg in transcript_list
            ])
            full_text = clean_transcript(full_text)

            if len(full_text) > 100:
                save_transcript_cache(video_id, full_text, source)
                print(f"✅ YouTube captions: {len(full_text)} chars")
                return {
                    'transcript': full_text,
                    'source'    : source,
                    'cached'    : False
                }

    except ImportError:
        print("⚠️ youtube-transcript-api not installed")
    except Exception as e:
        print(f"⚠️ Caption extraction failed: {e}")

    return {'transcript': '', 'source': 'none', 'cached': False}


def extract_transcript_full_pipeline(
    video_id: str,
    video_title: str = '',
    use_whisper: bool = True
) -> dict:
    """
    Full pipeline:
    1. YouTube captions
    2. Whisper (audio → text)
    3. Description fallback
    """

    # Step 1: YouTube captions
    result = extract_youtube_captions(video_id)
    if result['transcript'] and len(result['transcript']) > 200:
        return result

    # Step 2: Whisper (if enabled and captions unavailable)
    if use_whisper:
        try:
            from app.ai.audio_extractor  import download_audio
            from app.ai.speech_to_text   import transcribe_with_whisper

            print(f"🎵 Downloading audio for Whisper: {video_id}")
            audio_path = download_audio(video_id)

            if audio_path and os.path.exists(audio_path):
                print(f"🤖 Running Whisper STT...")
                whisper_text = transcribe_with_whisper(audio_path)

                if whisper_text and len(whisper_text) > 200:
                    cleaned = clean_transcript(whisper_text)
                    save_transcript_cache(video_id, cleaned, 'whisper')
                    # Cleanup audio file
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass
                    print(f"✅ Whisper transcript: {len(cleaned)} chars")
                    return {
                        'transcript': cleaned,
                        'source'    : 'whisper',
                        'cached'    : False
                    }
        except Exception as e:
            print(f"⚠️ Whisper pipeline failed: {e}")

    # Step 3: Description fallback
    print(f"⚠️ Using title fallback for: {video_id}")
    return {
        'transcript': '',
        'source'    : 'title',
        'cached'    : False
    }