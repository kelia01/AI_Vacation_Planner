"""
Input guardrails for agent endpoints.
Runs before any input reaches the LLM.
"""

import re
from dataclasses import dataclass
from typing import Optional

MAX_TEXT_CHARS = 2_000
MAX_AUDIO_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_IMAGE_BYTES = 5 * 1024 * 1024 

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"forget\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+(?!a\s+vacation)",   # "you are now DAN" etc, but not "you are now a vacation planner"
    r"act\s+as\s+(if\s+you\s+are\s+)?(?!a\s+(travel|vacation|trip))",
    r"new\s+persona",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"bypass\s+(your\s+)?(safety|guidelines|restrictions|rules)",
    r"pretend\s+(you\s+are|to\s+be)\s+(?!a\s+(travel|vacation|trip))",
    r"system\s*:\s*you",          # injected system message attempt
    r"<\s*system\s*>",            # XML-style system tag injection
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE,
)

_TRAVEL_KEYWORDS = re.compile(
    r"trip|travel|hotel|flight|restaurant|museum|weather|itinerary|"
    r"destination|vacation|tour|visit|book|budget|day|night|city|country|"
    r"beach|mountain|culture|food|plan|activity|activities",
    re.IGNORECASE,
)

OFF_TOPIC_MIN_CHARS = 200   # only check texts longer than this

@dataclass
class GuardrailResult:
    passed: bool
    reason: Optional[str] = None
    
def check_text(text: str) -> GuardrailResult:
    """Validate a text input before it reaches the LLM."""
    if len(text) > MAX_TEXT_CHARS:
        return GuardrailResult(
            passed=False,
            reason=f"Text input exceeds maximum length ({MAX_TEXT_CHARS} characters).",
        )

    if _INJECTION_RE.search(text):
        return GuardrailResult(
            passed=False,
            reason="Input contains disallowed instructions.",
        )

    if len(text) >= OFF_TOPIC_MIN_CHARS and not _TRAVEL_KEYWORDS.search(text):
        return GuardrailResult(
            passed=False,
            reason="Input does not appear to be related to travel planning.",
        )

    return GuardrailResult(passed=True)

def check_audio(audio_bytes: bytes) -> GuardrailResult:
    """Validate audio upload size."""
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return GuardrailResult(
            passed=False,
            reason=f"Audio file exceeds maximum size ({MAX_AUDIO_BYTES // (1024*1024)} MB).",
        )
    return GuardrailResult(passed=True)

def check_image(image_bytes: bytes) -> GuardrailResult:
    """Validate image upload size."""
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return GuardrailResult(
            passed=False,
            reason=f"Image file exceeds maximum size ({MAX_IMAGE_BYTES // (1024*1024)} MB).",
        )
    return GuardrailResult(passed=True)

def check_transcript(transcript: str) -> GuardrailResult:
    """
    Run the same text checks on a speech-to-text transcript.
    Transcripts are shorter so the off-topic threshold still applies.
    """
    return check_text(transcript)