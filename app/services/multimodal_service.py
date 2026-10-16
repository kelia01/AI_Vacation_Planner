import base64
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from elevenlabs.client import ElevenLabs

llm = ChatAnthropic(model="claude-haiku-4-5")

_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"GIF8": "image/gif",
    b"RIFF": "image/webp",
}


def _detect_media_type(data: bytes) -> str:
    for magic, mime in _MAGIC.items():
        if data[: len(magic)] == magic:
            return mime
    return "image/jpeg"


def transcribe_audio(audio_bytes: bytes) -> str:
    """Convert audio bytes to text using SpeechRecognition (free Google web API).
    Accepts any format (MP3, M4A, OGG, WAV) — converts to PCM WAV via pydub.
    """
    import io
    import speech_recognition as sr
    from pydub import AudioSegment

    # Decode any format → PCM WAV in memory
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
    wav_buffer = io.BytesIO()
    audio_segment.export(wav_buffer, format="wav")
    wav_buffer.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_buffer) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)


def analyze_image(image_bytes: bytes, content_type: str = None) -> str:
    """Extract destination info from image using Claude vision."""
    media_type = content_type or _detect_media_type(image_bytes)
    base64_image = base64.b64encode(image_bytes).decode()
    message = llm.invoke([
        HumanMessage(content=[
            {
                "type": "text",
                "text": (
                    "Analyze this travel destination image. "
                    "Extract: location clues, landmarks, climate/weather indicators. "
                    "Return a short plain-text summary."
                ),
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_image,
                },
            },
        ])
    ])
    return message.content


def text_to_speech(text: str) -> bytes | None:
    """Convert text to audio using ElevenLabs. Returns bytes or None on failure."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    try:
        client = ElevenLabs(api_key=api_key)
        audio_bytes = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            text=text,
            model_id="eleven_monolingual_v1",
        )
        return b"".join(audio_bytes)
    except Exception:
        return None
