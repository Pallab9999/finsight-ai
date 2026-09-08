"""Speech-to-text for voice prompts.

Amazon Bedrock (Nova Lite audio) is tried first using the same AWS credentials
as the summary chain. Gemini is the fallback when it can accept inline audio.
Credentials stay in the environment; they are never logged.
"""

from __future__ import annotations

import logging

from backend.config import gemini_key, settings
from backend.llm import bedrock_available

logger = logging.getLogger(__name__)

TRANSCRIBE_INSTRUCTION = (
    "Transcribe this audio verbatim. It is a spoken credit, financial, or "
    "analytics prompt from either an SME borrower or a bank underwriter. "
    "Preserve company names, currencies, amounts, and financial terms exactly. "
    "Return only the transcript text, with no commentary, quotes, or preamble."
)

_MIME_BY_SUFFIX = {
    "wav": "audio/wav",
    "mp3": "audio/mp3",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "webm": "audio/webm",
    "flac": "audio/flac",
}

_FORMAT_BY_MIME = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
    "audio/flac": "flac",
}


def stt_available() -> bool:
    """True when Bedrock or Gemini can transcribe audio."""
    return bedrock_available() or bool(gemini_key())


def mime_for(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MIME_BY_SUFFIX.get(suffix, "audio/wav")


def _audio_format(mime_type: str) -> str:
    return _FORMAT_BY_MIME.get((mime_type or "").lower(), "wav")


def _transcribe_with_bedrock(audio_bytes: bytes, mime_type: str) -> str | None:
    if not bedrock_available():
        return None
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)
        response = client.converse(
            modelId=settings.bedrock_stt_model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "audio": {
                                "format": _audio_format(mime_type),
                                "source": {"bytes": audio_bytes},
                            }
                        },
                        {"text": TRANSCRIBE_INSTRUCTION},
                    ],
                }
            ],
            inferenceConfig={"temperature": 0.0, "maxTokens": 512},
        )
        return response["output"]["message"]["content"][0]["text"].strip()
    except Exception as exc:
        logger.warning("Bedrock transcription failed: %s", exc)
        return None


def _transcribe_with_gemini(audio_bytes: bytes, mime_type: str) -> str | None:
    if not gemini_key():
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_key())
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                TRANSCRIBE_INSTRUCTION,
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        return (response.text or "").strip()
    except Exception as exc:
        logger.warning("Gemini transcription failed: %s", exc)
        return None


def transcribe(audio_bytes: bytes, mime_type: str = "audio/wav") -> tuple[str | None, str]:
    """Transcribe spoken audio. Returns (transcript, status message)."""
    if not audio_bytes:
        return None, "No audio captured."

    if not stt_available():
        return None, (
            "Voice input needs Amazon Bedrock (`AWS_BEARER_TOKEN_BEDROCK`) or a Gemini key "
            "(`GEMINI_API_KEY` / `GOOGLE_API_KEY`) in `.env`, then reload."
        )

    if text := _transcribe_with_bedrock(audio_bytes, mime_type):
        return text, f"Transcribed {len(audio_bytes) / 1024:.0f} KB of audio via Amazon Bedrock."

    if text := _transcribe_with_gemini(audio_bytes, mime_type):
        return text, f"Transcribed {len(audio_bytes) / 1024:.0f} KB of audio via Gemini."

    return None, "Transcription failed. Type the prompt instead, or record again."
