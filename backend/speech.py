"""Speech-to-text for voice prompts.

Amazon Bedrock models that accept audio are tried first using the same AWS
credentials as the text chain. Gemini is the fallback. Credentials stay in
the environment; they are never logged.
"""

from __future__ import annotations

import logging

from backend.config import export_dotenv_secrets, gemini_key, settings
from backend.llm import bedrock_available, bedrock_api_key_format_ok

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
    """True when a speech model can actually be called."""
    export_dotenv_secrets()
    if gemini_key():
        return True
    return bedrock_available() and bedrock_api_key_format_ok()


def mime_for(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MIME_BY_SUFFIX.get(suffix, "audio/wav")


def _audio_format(mime_type: str) -> str:
    return _FORMAT_BY_MIME.get((mime_type or "").lower(), "wav")


def sniff_audio_format(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Prefer magic bytes over the container filename Streamlit reports."""
    if audio_bytes.startswith(b"RIFF"):
        return "wav"
    if audio_bytes.startswith(b"OggS"):
        return "ogg"
    if audio_bytes.startswith(b"fLaC"):
        return "flac"
    if len(audio_bytes) > 8 and audio_bytes[4:8] == b"ftyp":
        return "mp4"
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    if audio_bytes[:3] == b"ID3" or audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    return _audio_format(mime_type)


def _bedrock_stt_model_ids() -> list[str]:
    seen: list[str] = []
    region = (settings.bedrock_region or "us-east-1").lower()
    preferred = (
        settings.bedrock_stt_model_id,
        "amazon.nova-2-lite-v1:0",
        "us.amazon.nova-2-lite-v1:0",
        "eu.amazon.nova-2-lite-v1:0",
        "amazon.nova-lite-v1:0",
        "us.amazon.nova-lite-v1:0",
    )
    if region.startswith("eu"):
        preferred = (
            settings.bedrock_stt_model_id,
            "eu.amazon.nova-2-lite-v1:0",
            "amazon.nova-2-lite-v1:0",
            "us.amazon.nova-2-lite-v1:0",
            "amazon.nova-lite-v1:0",
        )
    for mid in preferred:
        if mid and mid not in seen:
            seen.append(mid)
    return seen


def _transcribe_with_bedrock(audio_bytes: bytes, mime_type: str) -> str | None:
    if not bedrock_available():
        return None
    audio_format = sniff_audio_format(audio_bytes, mime_type)
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)
        last_error = None
        for model_id in _bedrock_stt_model_ids():
            try:
                response = client.converse(
                    modelId=model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "audio": {
                                        "format": audio_format,
                                        "source": {"bytes": audio_bytes},
                                    }
                                },
                                {"text": TRANSCRIBE_INSTRUCTION},
                            ],
                        }
                    ],
                    inferenceConfig={"temperature": 0.0, "maxTokens": 512},
                )
                text = response["output"]["message"]["content"][0]["text"].strip()
                if text:
                    return text
            except Exception as exc:
                last_error = exc
                logger.warning("Bedrock transcription failed on %s: %s", model_id, exc)
        if last_error:
            logger.warning("All Bedrock STT models failed: %s", last_error)
        return None
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
    export_dotenv_secrets()
    if not audio_bytes:
        return None, "No audio captured."

    if not stt_available():
        if bedrock_available() and not bedrock_api_key_format_ok():
            return None, (
                "The saved Amazon key is not a Bedrock API key (those start with ABSK). "
                "Type the question instead — answers still run against your credit data."
            )
        return None, (
            "Voice input needs `AWS_BEARER_TOKEN_BEDROCK` or a Gemini key "
            "(`GEMINI_API_KEY` / `GOOGLE_API_KEY`) in `.env`, then reload."
        )

    if text := _transcribe_with_bedrock(audio_bytes, mime_type):
        return text, "Heard your question."

    if text := _transcribe_with_gemini(audio_bytes, mime_type):
        return text, "Heard your question."

    return None, (
        "Could not transcribe that recording. Type the same question in the box "
        "and press Ask — answers still run against your credit data."
    )
