"""Speech-to-text for the voice analytics console.

Gemini is used because it accepts inline audio directly, so the project needs no
transcription provider beyond the key already in the summary chain. The key is
read from the environment via Settings and never held anywhere else.
"""

from __future__ import annotations

import logging

from backend.config import settings

logger = logging.getLogger(__name__)

TRANSCRIBE_INSTRUCTION = (
    "Transcribe this audio verbatim. It is a spoken question from a loan officer "
    "about a company's financial or ESG analytics, so preserve financial terms, "
    "company names and numbers exactly. Return only the transcript text, with no "
    "commentary, quotes or preamble."
)

# Streamlit's audio_input returns WAV; keep a small map for other inputs.
_MIME_BY_SUFFIX = {
    "wav": "audio/wav",
    "mp3": "audio/mp3",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "webm": "audio/webm",
    "flac": "audio/flac",
}


def stt_available() -> bool:
    """True when a Gemini key is configured, so the UI can explain itself."""
    return bool(settings.gemini_api_key)


def mime_for(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MIME_BY_SUFFIX.get(suffix, "audio/wav")


def transcribe(audio_bytes: bytes, mime_type: str = "audio/wav") -> tuple[str | None, str]:
    """Transcribe spoken audio.

    Returns the transcript and a status message. The transcript is None when
    transcription is unavailable or failed, which the caller surfaces to the user
    rather than treating as an empty question.
    """
    if not audio_bytes:
        return None, "No audio captured."

    if not settings.gemini_api_key:
        return None, (
            "Voice input needs a Gemini API key. Set GEMINI_API_KEY in .env "
            "(or in Streamlit secrets when hosted), then reload."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                TRANSCRIBE_INSTRUCTION,
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        transcript = (response.text or "").strip()
        if not transcript:
            return None, "Gemini returned an empty transcript. Try recording again."
        return transcript, f"Transcribed {len(audio_bytes) / 1024:.0f} KB of audio via Gemini."
    except Exception as exc:
        logger.warning("Gemini transcription failed: %s", exc)
        return None, f"Transcription failed ({type(exc).__name__}). You can type the question instead."
