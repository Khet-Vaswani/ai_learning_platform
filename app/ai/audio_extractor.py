# ============================================================
# audio_extractor.py
# Downloads audio from YouTube using yt-dlp
# ============================================================

import os
import uuid
import subprocess


AUDIO_DIR = os.path.join(os.path.dirname(__file__),
                         '..', '..', 'temp_audio')


def ensure_audio_dir():
    os.makedirs(AUDIO_DIR, exist_ok=True)


def download_audio(video_id: str) -> str | None:
    """
    Download YouTube audio using python yt_dlp library (or subprocess fallback).
    Returns local file path or None on failure.
    """
    ensure_audio_dir()
    out_name = os.path.join(AUDIO_DIR, f"{video_id}_{uuid.uuid4().hex[:8]}")
    url      = f"https://www.youtube.com/watch?v={video_id}"

    # Try Python yt_dlp module first (use android/ios client to bypass JS runtime & 403 Forbidden)
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_name + '.%(ext)s',
            'quiet': True,
            'noplaylist': True,
            'socket_timeout': 10,
            'retries': 2,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/19.29.37 (Linux; U; Android 11) gzip'
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for ext in ['mp3', 'm4a', 'webm', 'ogg', 'opus']:
            candidate = f"{out_name}.{ext}"
            if os.path.exists(candidate):
                size_mb = os.path.getsize(candidate) / (1024 * 1024)
                print(f"✅ Audio downloaded via yt_dlp module: {size_mb:.1f} MB ({ext})")
                return candidate
    except Exception as py_err:
        print(f"⚠️ Python yt_dlp module download notice: {py_err}. Trying CLI fallback...")

    # CLI fallback using python -m yt_dlp
    import sys
    cmd = [
        sys.executable,
        '-m',
        'yt_dlp',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '5',
        '--socket-timeout', '10',
        '--no-playlist',
        '--quiet',
        '--extractor-args', 'youtube:player_client=android,ios',
        '--output', out_name + '.%(ext)s',
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25
        )

        mp3_path = out_name + '.mp3'
        if os.path.exists(mp3_path):
            size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
            print(f"✅ Audio downloaded via CLI: {size_mb:.1f} MB")
            return mp3_path

        for ext in ['m4a', 'webm', 'ogg', 'opus']:
            alt = out_name + '.' + ext
            if os.path.exists(alt):
                return alt

        print(f"❌ Audio file not found after download")
        if result.stderr:
            print(f"   yt-dlp stderr: {result.stderr[:300]}")
        return None

    except subprocess.TimeoutExpired:
        print(f"❌ Audio download timed out for {video_id}")
        return None
    except Exception as e:
        print(f"❌ Audio download error: {e}")
        return None


def cleanup_audio_files(max_age_hours: int = 2):
    """Remove old temp audio files."""
    import time
    ensure_audio_dir()
    now = time.time()
    for f in os.listdir(AUDIO_DIR):
        fp = os.path.join(AUDIO_DIR, f)
        try:
            if os.path.isfile(fp):
                age_hours = (now - os.path.getmtime(fp)) / 3600
                if age_hours > max_age_hours:
                    os.remove(fp)
        except Exception:
            pass