# ============================================================
# speech_to_text.py
# Converts audio to text using OpenAI Whisper (local)
# ============================================================

import os
import torch


def transcribe_with_whisper(
    audio_path: str,
    model_size: str = 'base'           # tiny|base|small|medium|large
) -> str:
    """
    Transcribe audio file using Whisper.

    Model sizes vs accuracy vs speed:
    - tiny   : fastest, least accurate (~32x realtime)
    - base   : good balance for FYP  (~16x realtime) ← RECOMMENDED
    - small  : better accuracy       (~6x  realtime)
    - medium : very accurate         (~2x  realtime)
    - large  : best accuracy         (~1x  realtime, needs 10GB GPU RAM)

    Returns: transcribed text string
    """
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return ''

    import shutil
    if not shutil.which('ffmpeg'):
        print("⚠️ Local Whisper skipped: ffmpeg is not installed or not on PATH")
        return ''

    try:
        import whisper

        print(f"🤖 Loading Whisper model: {model_size}")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model  = whisper.load_model(model_size, device=device)

        print(f"🎙️ Transcribing audio on {device}...")
        result = model.transcribe(
            audio_path,
            language     = None,   # auto-detect: transcribe what was actually said
            verbose      = False,
            fp16         = (device == 'cuda'),
            # Options to improve accuracy:
            temperature       = 0,      # deterministic output
            compression_ratio_threshold = 2.4,
            logprob_threshold = -1.0,
            no_speech_threshold = 0.6,
        )

        text = result.get('text', '').strip()
        print(f"✅ Whisper done: {len(text)} chars")
        return text

    except ImportError:
        print("❌ Whisper not installed. Run: pip install openai-whisper")
        return ''
    except Exception as e:
        print(f"❌ Whisper transcription error: {e}")
        import traceback
        traceback.print_exc()
        return ''


def transcribe_with_groq_whisper(audio_path: str, language: str = None) -> str:
    """
    Use Groq's Whisper API (whisper-large-v3 / whisper-large-v3-turbo).
    Ultra-fast cloud STT, no local GPU needed.
    Requires GROQ_API_KEY in .env
    """
    if not audio_path or not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return ''

    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("❌ GROQ_API_KEY not found in environment")
        return ''

    # Check file size (Groq limit is 25 MB)
    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if size_mb > 25:
        print(f"⚠️ Audio file size ({size_mb:.1f} MB) exceeds Groq 25MB limit. Falling back to local Whisper.")
        return ''

    from groq import Groq
    client = Groq(api_key=api_key)
    models = ['whisper-large-v3', 'whisper-large-v3-turbo']

    for model in models:
        try:
            with open(audio_path, 'rb') as f:
                params = {
                    'model': model,
                    'file': f,
                    'response_format': 'text',
                    'temperature': 0.0,
                }
                if language:
                    params['language'] = language

                response = client.audio.transcriptions.create(**params)

            text = response if isinstance(response, str) else getattr(response, 'text', str(response))
            text = text.strip()
            if len(text) > 50:
                print(f"✅ Groq Whisper ({model}): {len(text)} chars ({len(text.split())} words)")
                return text

        except Exception as e:
            print(f"⚠️ Groq Whisper ({model}) error: {e}")
            continue

    return ''