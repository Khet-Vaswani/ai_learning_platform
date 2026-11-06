# ============================================================
# transcript_extractor.py
# Robust, multi-layered extraction of actual YouTube transcripts
# Hierarchy: DB Cache -> YouTube Captions API -> yt-dlp Subtitles -> Whisper STT (Groq / local)
# Strictly extracts real spoken words. Never returns metadata or title as transcript.
# ============================================================

import os
import re
import urllib.request
import json as pyjson
from app.utils.db import execute_query


# Sources that come from the video's actual spoken words. Anything else
# (title, description, metadata, or the legacy generic 'transcript' label)
# is never used for quizzes or notes.
VALID_TRANSCRIPT_SOURCES = {
    'youtube_captions',
    'youtube_auto_captions',
    'youtube_translated_captions',
    'ytdlp_captions',
    'ytdlp_auto_captions',
    'groq_whisper',
    'whisper',
}

ENGLISH_CODES = ['en', 'en-US', 'en-GB', 'en-IN', 'en-CA', 'en-AU']

# YouTube often blocks caption requests from cloud servers (Vercel, AWS, ...).
# Optional: route them through a proxy, e.g. YT_PROXY_URL=http://user:pass@host:port
YT_PROXY_URL = os.getenv('YT_PROXY_URL') or None


def clean_transcript(text: str) -> str:
    """Remove noise, bracketed descriptions, speaker tags, timestamps, and redundant whitespace."""
    if not text:
        return ''
    # Remove music tags, applause, sound effects [Music], (Laughter), etc.
    text = re.sub(r'\[.*?\]', ' ', text)
    text = re.sub(r'\(.*?\)', ' ', text)
    # Remove timestamps like [00:01:23] or 00:01:23
    text = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', ' ', text)
    # Remove speaker markers e.g. "Speaker 1:", ">>"
    text = re.sub(r'>>+', ' ', text)
    text = re.sub(r'SPEAKER\s*\d*\s*:', ' ', text, flags=re.IGNORECASE)
    # Remove URLs
    text = re.sub(r'https?://\S+', ' ', text)
    # Remove HTML entities and tags
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
    # Clean excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_valid_transcript(text: str) -> bool:
    """
    Ensure the text is a genuine spoken video transcript and NOT
    a title, description fallback, or metadata summary.
    """
    if not text or not isinstance(text, str):
        return False
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    
    # Reject title / metadata / description fallback patterns
    lowered = stripped.lower()
    if lowered.startswith('video title:') and 'summary & overview:' in lowered:
        return False
    if 'transcript not available' in lowered or 'no transcript available' in lowered:
        return False
        
    words = stripped.split()
    return len(words) >= 20


def get_cached_transcript(video_id: str):
    """
    Check DB cache for a verified, authentic video transcript.
    Strictly ignores any rows marked with metadata/description/title.
    """
    try:
        rows = execute_query(
            """SELECT transcript_text, source, word_count
               FROM video_transcripts
               WHERE video_id = %s""",
            (video_id,), fetch=True
        )
        # Only trust rows extracted from captions or speech-to-text
        if rows and rows[0].get('source') in VALID_TRANSCRIPT_SOURCES:
            text = rows[0].get('transcript_text', '')
            if is_valid_transcript(text):
                return {
                    'transcript': text,
                    'source'    : rows[0].get('source') or 'transcript',
                    'cached'    : True,
                    'word_count': rows[0].get('word_count', len(text.split()))
                }
    except Exception as e:
        print(f"⚠️ Cache read error for {video_id}: {e}")
    return None


def save_transcript_cache(video_id: str, text: str, source: str):
    """Save verified transcript to DB cache."""
    if not is_valid_transcript(text) or source not in VALID_TRANSCRIPT_SOURCES:
        return
    word_count = len(text.split())
    try:
        execute_query(
            """INSERT INTO video_transcripts
               (video_id, transcript_text, source, word_count)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               transcript_text = VALUES(transcript_text),
               source          = VALUES(source),
               word_count      = VALUES(word_count),
               created_at      = NOW()""",
            (video_id, text, source, word_count)
        )
    except Exception as e:
        print(f"⚠️ Failed to cache transcript for {video_id}: {e}")


def _snippets_to_text(fetched) -> str:
    """Join caption lines. Handles youtube-transcript-api 1.x snippet objects and 0.x dicts."""
    parts = []
    for seg in fetched or []:
        text = seg.get('text', '') if isinstance(seg, dict) else getattr(seg, 'text', '')
        if text:
            parts.append(text)
    return ' '.join(parts)


def _list_caption_tracks(video_id: str):
    """Return the video's caption track list (1.x instance API, with 0.x fallback)."""
    from youtube_transcript_api import YouTubeTranscriptApi
    if hasattr(YouTubeTranscriptApi, 'list_transcripts'):          # 0.x
        proxies = {'http': YT_PROXY_URL, 'https': YT_PROXY_URL} if YT_PROXY_URL else None
        return YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)
    proxy_config = None                                           # 1.x
    if YT_PROXY_URL:
        from youtube_transcript_api.proxies import GenericProxyConfig
        proxy_config = GenericProxyConfig(http_url=YT_PROXY_URL, https_url=YT_PROXY_URL)
    return YouTubeTranscriptApi(proxy_config=proxy_config).list(video_id)


def extract_youtube_captions(video_id: str) -> dict:
    """
    Extract captions with youtube-transcript-api.
    Preference: English manual -> English auto -> YouTube's English translation
    of the real captions -> original-language captions.
    """
    try:
        tracks = list(_list_caption_tracks(video_id))
    except ImportError:
        print("⚠️ youtube-transcript-api not installed")
        return {'transcript': '', 'source': 'none', 'cached': False}
    except Exception as e:
        if type(e).__name__ in ('RequestBlocked', 'IpBlocked'):
            print(f"[Transcript] YouTube blocked this server's caption request for {video_id}")
            return {'transcript': '', 'source': 'none', 'cached': False, 'blocked': True}
        print(f"ℹ️ No caption tracks for {video_id}: {type(e).__name__}: {str(e)[:160]}")
        return {'transcript': '', 'source': 'none', 'cached': False}

    def is_english(t):
        return t.language_code.split('-')[0].lower() == 'en'

    manual_en = [t for t in tracks if is_english(t) and not t.is_generated]
    auto_en   = [t for t in tracks if is_english(t) and t.is_generated]
    others    = [t for t in tracks if not is_english(t)]

    attempts = [(t, None, 'youtube_captions') for t in manual_en]
    attempts += [(t, None, 'youtube_auto_captions') for t in auto_en]
    # Translation of the video's own captions into English (still the spoken content)
    attempts += [(t, 'en', 'youtube_translated_captions') for t in others if getattr(t, 'is_translatable', False)]
    attempts += [(t, None, 'youtube_auto_captions' if t.is_generated else 'youtube_captions') for t in others]

    for track, translate_to, source in attempts:
        try:
            target  = track.translate(translate_to) if translate_to else track
            cleaned = clean_transcript(_snippets_to_text(target.fetch()))
            if is_valid_transcript(cleaned):
                save_transcript_cache(video_id, cleaned, source)
                lang = translate_to or track.language_code
                print(f"✅ YouTube captions extracted ({lang}): {len(cleaned.split())} words [{source}]")
                return {'transcript': cleaned, 'source': source, 'cached': False, 'language': lang}
        except Exception as e:
            print(f"ℹ️ Caption track {track.language_code}{' → ' + translate_to if translate_to else ''} failed: {type(e).__name__}")
            continue

    return {'transcript': '', 'source': 'none', 'cached': False}


def extract_ytdlp_subtitles(video_id: str) -> dict:
    """
    Extract captions/subtitles using yt-dlp without downloading media.
    Fetches raw JSON3 or VTT subtitle streams directly from YouTube.
    """
    try:
        import yt_dlp
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10,
            **({'proxy': YT_PROXY_URL} if YT_PROXY_URL else {}),
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb', 'web']
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {'transcript': '', 'source': 'none', 'cached': False}

            sub_dict = info.get('subtitles') or {}
            auto_sub_dict = info.get('automatic_captions') or {}

            candidates = []
            for lang, formats in sub_dict.items():
                candidates.append((lang, formats, 'ytdlp_captions'))
            for lang, formats in auto_sub_dict.items():
                candidates.append((lang, formats, 'ytdlp_auto_captions'))

            # Prioritize English, Urdu, Hindi or whatever comes first
            def lang_priority(item):
                code = item[0].lower()
                if code.startswith('en'): return 0
                if code.startswith('ur'): return 1
                if code.startswith('hi'): return 2
                return 3

            candidates.sort(key=lang_priority)

            for lang, formats, source in candidates:
                fmt_url = None
                fmt_ext = ''
                for f in formats:
                    ext = f.get('ext', '')
                    if ext in ('json3', 'srv1', 'vtt', 'ttml'):
                        fmt_url = f.get('url')
                        fmt_ext = ext
                        if ext == 'json3':
                            break
                if not fmt_url and formats:
                    fmt_url = formats[0].get('url')
                    fmt_ext = formats[0].get('ext', '')

                if not fmt_url:
                    continue

                try:
                    req = urllib.request.Request(
                        fmt_url,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    )
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler({'http': YT_PROXY_URL, 'https': YT_PROXY_URL})
                        if YT_PROXY_URL else urllib.request.ProxyHandler())
                    with opener.open(req, timeout=10) as resp:
                        raw_data = resp.read().decode('utf-8', errors='ignore')

                    extracted_text = ''
                    if fmt_ext == 'json3' or '"events"' in raw_data:
                        try:
                            parsed = pyjson.loads(raw_data)
                            words = []
                            for ev in parsed.get('events', []):
                                for s in ev.get('segs', []):
                                    t = s.get('utf8', '').strip()
                                    if t and t != '\n':
                                        words.append(t)
                            extracted_text = ' '.join(words)
                        except Exception:
                            pass

                    if not extracted_text:
                        # Strip XML/VTT/SRT tags & timestamps
                        extracted_text = re.sub(r'<[^>]+>', ' ', raw_data)
                        extracted_text = re.sub(r'\d{2}:\d{2}:\d{2}[\.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[\.,]\d{3}', ' ', extracted_text)
                        extracted_text = re.sub(r'WEBVTT.*?\n', ' ', extracted_text)

                    cleaned = clean_transcript(extracted_text)
                    if is_valid_transcript(cleaned):
                        save_transcript_cache(video_id, cleaned, source)
                        print(f"✅ yt-dlp subtitle stream extracted ({lang}): {len(cleaned)} chars [{source}]")
                        return {
                            'transcript': cleaned,
                            'source'    : source,
                            'cached'    : False
                        }
                except Exception as stream_err:
                    print(f"⚠️ Subtitle stream error ({lang}): {stream_err}")
                    continue

    except Exception as e:
        print(f"⚠️ yt-dlp subtitle extraction notice for {video_id}: {e}")
        if 'not a bot' in str(e).lower() or 'sign in to confirm' in str(e).lower():
            return {'transcript': '', 'source': 'none', 'cached': False, 'blocked': True}

    return {'transcript': '', 'source': 'none', 'cached': False}


def extract_whisper_transcript(video_id: str) -> dict:
    """
    Download audio and transcribe speech using Groq Whisper API (primary) or local Whisper.
    Strictly removes temporary audio file immediately after transcription.
    """
    try:
        from app.ai.audio_extractor import download_audio
        from app.ai.speech_to_text import transcribe_with_groq_whisper, transcribe_with_whisper

        print(f"🎙️ Extracting audio for speech-to-text: {video_id}")
        audio_path = download_audio(video_id)

        if not audio_path or not os.path.exists(audio_path):
            print(f"❌ Audio download failed for {video_id}")
            return {'transcript': '', 'source': 'none', 'cached': False}

        transcribed_text = ''
        source = 'groq_whisper'

        try:
            print("🚀 Transcribing via Groq Whisper API...")
            transcribed_text = transcribe_with_groq_whisper(audio_path)
        except Exception as ge:
            print(f"⚠️ Groq Whisper attempt failed: {ge}")

        if not transcribed_text or not is_valid_transcript(transcribed_text):
            try:
                print("🔄 Falling back to local Whisper STT...")
                transcribed_text = transcribe_with_whisper(audio_path, model_size='base')
                source = 'whisper'
            except Exception as we:
                print(f"⚠️ Local Whisper attempt failed: {we}")

        # Always remove temp audio file to prevent disk exhaustion
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

        if transcribed_text and is_valid_transcript(transcribed_text):
            cleaned = clean_transcript(transcribed_text)
            save_transcript_cache(video_id, cleaned, source)
            print(f"✅ Whisper speech-to-text transcript generated: {len(cleaned)} chars [{source}]")
            return {
                'transcript': cleaned,
                'source'    : source,
                'cached'    : False
            }

    except Exception as e:
        print(f"❌ Whisper audio pipeline error for {video_id}: {e}")

    return {'transcript': '', 'source': 'none', 'cached': False}


def extract_transcript_full_pipeline(
    video_id: str,
    video_title: str = '',
    use_whisper: bool = True
) -> dict:
    """
    Full resilient extraction pipeline for YouTube video transcripts.
    Order of execution:
      1. Database cache (verified actual transcript)
      2. youtube-transcript-api (manual, auto, multi-language)
      3. yt-dlp direct subtitle extraction
      4. Audio download + Whisper Speech-To-Text (Groq / local)

    Strictly returns an authentic transcript or empty text.
    Never falls back to title, description, or metadata.
    """
    if not video_id:
        return {'transcript': '', 'source': 'none', 'cached': False}

    # Step 1: Check DB cache
    cached = get_cached_transcript(video_id)
    if cached and is_valid_transcript(cached.get('transcript')):
        print(f"✅ Transcript from DB cache: {video_id} ({cached.get('word_count', 0)} words)")
        return cached

    # Step 2: YouTube Captions API
    captions_res = extract_youtube_captions(video_id)
    if captions_res.get('transcript') and is_valid_transcript(captions_res['transcript']):
        return captions_res

    # Step 3: yt-dlp Subtitle Stream extraction
    ytdlp_res = extract_ytdlp_subtitles(video_id)
    if ytdlp_res.get('transcript') and is_valid_transcript(ytdlp_res['transcript']):
        return ytdlp_res

    # YouTube refused this server (common on cloud hosts): the video may well have
    # captions, and downloading its audio would be blocked too
    blocked = bool(captions_res.get('blocked') or ytdlp_res.get('blocked'))

    # Step 4: Whisper Speech-To-Text
    if use_whisper and not blocked:
        whisper_res = extract_whisper_transcript(video_id)
        if whisper_res.get('transcript') and is_valid_transcript(whisper_res['transcript']):
            return whisper_res

    print(f"❌ No authentic transcript could be retrieved for video: {video_id}"
          + (" (YouTube blocked this server)" if blocked else ""))
    return {
        'transcript': '',
        'source'    : 'none',
        'cached'    : False,
        'blocked'   : blocked,
    }