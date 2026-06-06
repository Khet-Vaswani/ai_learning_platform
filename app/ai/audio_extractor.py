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
    Download YouTube audio as mp3 using yt-dlp.
    Returns local file path or None on failure.
    """
    ensure_audio_dir()
    out_name = os.path.join(AUDIO_DIR, f"{video_id}_{uuid.uuid4().hex[:8]}")
    url      = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        'yt-dlp',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '5',        # 0=best, 9=worst (5 is enough for STT)
        '--no-playlist',
        '--quiet',
        '--output', out_name + '.%(ext)s',
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120                # 2 min timeout
        )

        mp3_path = out_name + '.mp3'
        if os.path.exists(mp3_path):
            size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
            print(f"✅ Audio downloaded: {size_mb:.1f} MB")
            return mp3_path

        # Sometimes yt-dlp saves with different extension
        for ext in ['m4a', 'webm', 'ogg']:
            alt = out_name + '.' + ext
            if os.path.exists(alt):
                return alt

        print(f"❌ Audio file not found after download")
        print(f"   yt-dlp stderr: {result.stderr[:300]}")
        return None

    except subprocess.TimeoutExpired:
        print(f"❌ Audio download timed out for {video_id}")
        return None
    except FileNotFoundError:
        print("❌ yt-dlp not installed. Run: pip install yt-dlp")
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