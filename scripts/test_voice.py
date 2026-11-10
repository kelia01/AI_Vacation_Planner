import os, sys, wave, struct, io
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── TTS ──────────────────────────────────────────────────────────────────────
print("\n=== TTS (ElevenLabs) ===")

def _tts_direct(text: str):
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(buf)
        return buf.getvalue(), None
    except Exception as e:
        return None, str(e)

result, err = _tts_direct("Your Paris itinerary is ready. Day one includes the Eiffel Tower.")
if result:
    out_path = Path(__file__).parent / "tts_output.mp3"
    out_path.write_bytes(result)
    print(f"[OK] TTS worked -- {len(result)} bytes written to {out_path}")
else:
    print(f"[FAIL] TTS failed -- {err}")


# ── STT ──────────────────────────────────────────────────────────────────────
print("\n=== STT (Google Web Speech) ===")

def _transcribe_direct(audio_bytes: bytes, content_type: str = "audio/wav"):
    import speech_recognition as sr
    from pydub import AudioSegment
    import imageio_ffmpeg
    fmt_map = {
        "audio/mpeg": "mp3", "audio/mp3": "mp3",
        "audio/wav": "wav", "audio/x-wav": "wav",
        "audio/ogg": "ogg", "audio/m4a": "mp4",
        "audio/mp4": "mp4",
    }
    fmt = fmt_map.get(content_type, "wav")
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    AudioSegment.ffprobe   = imageio_ffmpeg.get_ffmpeg_exe()
    seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
    buf = io.BytesIO()
    seg.export(buf, format="wav")
    buf.seek(0)
    recognizer = sr.Recognizer()
    with sr.AudioFile(buf) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except Exception:
        return recognizer.recognize_whisper(audio, model="base")

# Build a minimal valid WAV in memory (1 second of silence)
def make_silent_wav() -> bytes:
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack("<" + "h" * 16000, *([0] * 16000)))
    return buf.getvalue()

try:
    wav_bytes = make_silent_wav()
    transcript = _transcribe_direct(wav_bytes, content_type="audio/wav")
    print(f"[OK] STT pipeline works -- transcript: '{transcript}'")
except Exception as e:
    err = str(e)
    if "unintelligible" in err.lower() or "could not understand" in err.lower():
        print("[OK] STT pipeline works -- silence not understood (expected)")
    else:
        print(f"[FAIL] STT failed -- {err}")
