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

    try:
        import whisper

        print(f"🤖 Loading Whisper model: {model_size}")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model  = whisper.load_model(model_size, device=device)

        print(f"🎙️ Transcribing audio on {device}...")
        result = model.transcribe(
            audio_path,
            language     = 'en',
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


def transcribe_with_groq_whisper(audio_path: str) -> str:
    """
    Alternative: Use Groq's Whisper API (faster, no local GPU needed).
    Requires GROQ_API_KEY in .env
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))

        with open(audio_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                model = 'whisper-large-v3',
                file  = f,
                response_format = 'text',
                language = 'en',
            )

        text = response if isinstance(response, str) else response.text
        print(f"✅ Groq Whisper: {len(text)} chars")
        return text.strip()

    except Exception as e:
        print(f"❌ Groq Whisper error: {e}")
        return ''