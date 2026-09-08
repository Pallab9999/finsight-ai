"""Speech-to-text provider order: Amazon Bedrock, then Gemini."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import speech
from backend import llm


def test_stt_unavailable_without_credentials(monkeypatch):
    monkeypatch.setattr(speech, "bedrock_available", lambda: False)
    monkeypatch.setattr(speech, "gemini_key", lambda: "")

    assert speech.stt_available() is False
    text, status = speech.transcribe(b"fake-wav")
    assert text is None
    assert "Bedrock" in status or "Gemini" in status


def test_empty_audio_short_circuits(monkeypatch):
    monkeypatch.setattr(speech, "bedrock_available", lambda: True)
    monkeypatch.setattr(speech, "bedrock_api_key_format_ok", lambda: True)
    text, status = speech.transcribe(b"")
    assert text is None
    assert "No audio" in status


def test_bedrock_transcription_preferred(monkeypatch):
    monkeypatch.setattr(speech, "bedrock_available", lambda: True)
    monkeypatch.setattr(speech, "bedrock_api_key_format_ok", lambda: True)
    monkeypatch.setattr(speech, "gemini_key", lambda: "")
    monkeypatch.setattr(
        speech, "_transcribe_with_bedrock", lambda audio, mime: "Assess a 750k loan for EcoTex"
    )
    monkeypatch.setattr(speech, "_transcribe_with_gemini", lambda audio, mime: "should not run")

    text, status = speech.transcribe(b"wav-bytes", "audio/wav")
    assert text == "Assess a 750k loan for EcoTex"
    assert "Heard" in status


def test_gemini_used_when_bedrock_fails(monkeypatch):
    monkeypatch.setattr(speech, "bedrock_available", lambda: True)
    monkeypatch.setattr(speech, "bedrock_api_key_format_ok", lambda: True)
    monkeypatch.setattr(speech, "_transcribe_with_bedrock", lambda audio, mime: None)
    monkeypatch.setattr(speech, "gemini_key", lambda: "test-key")
    monkeypatch.setattr(
        speech, "_transcribe_with_gemini", lambda audio, mime: "What is EcoTex revenue?"
    )

    text, status = speech.transcribe(b"wav-bytes")
    assert text == "What is EcoTex revenue?"
    assert "Heard" in status


def test_sniff_audio_format_prefers_magic_bytes():
    wav = b"RIFF" + b"\x00" * 8 + b"WAVE"
    assert speech.sniff_audio_format(wav, "audio/webm") == "wav"
    webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 8
    assert speech.sniff_audio_format(webm, "audio/wav") == "webm"


def test_mime_for_defaults_to_wav():
    assert speech.mime_for("clip.wav") == "audio/wav"
    assert speech.mime_for("clip.webm") == "audio/webm"
    assert speech.mime_for("noext") == "audio/wav"


def test_invalid_bearer_token_is_not_treated_as_usable(monkeypatch):
    monkeypatch.setenv(llm.BEDROCK_TOKEN_ENV, "AQ.not-a-bedrock-api-key")
    monkeypatch.delenv(llm.AWS_KEY_ENV, raising=False)
    monkeypatch.setattr(llm.settings, "bedrock_enabled", False)
    assert llm.bedrock_available() is True
    assert llm.bedrock_api_key_format_ok() is False


def test_bedrock_available_helper_still_reads_token_env(monkeypatch):
    monkeypatch.setenv(llm.BEDROCK_TOKEN_ENV, "bedrock-api-key-test")
    monkeypatch.setattr(llm.settings, "bedrock_enabled", False)
    assert llm.bedrock_available() is True
    assert llm.bedrock_api_key_format_ok() is True
