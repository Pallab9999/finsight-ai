"""Provider selection for executive summary generation."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import llm


def test_no_credentials_falls_back_to_template(monkeypatch):
    monkeypatch.delenv(llm.BEDROCK_TOKEN_ENV, raising=False)
    monkeypatch.delenv(llm.AWS_KEY_ENV, raising=False)
    monkeypatch.setattr(llm.settings, "bedrock_enabled", False)
    monkeypatch.setattr(llm.settings, "gemini_api_key", "")

    text, provider = llm.generate_summary("prompt")

    assert text is None
    assert provider == "template"


def test_bearer_token_selects_bedrock(monkeypatch):
    monkeypatch.setenv(llm.BEDROCK_TOKEN_ENV, "bedrock-api-key-test")
    monkeypatch.setattr(llm, "_summarize_with_bedrock", lambda prompt: "from bedrock")

    text, provider = llm.generate_summary("prompt")

    assert text == "from bedrock"
    assert provider == "bedrock"


def test_bedrock_failure_falls_through_to_gemini(monkeypatch):
    monkeypatch.setenv(llm.BEDROCK_TOKEN_ENV, "bedrock-api-key-test")
    monkeypatch.setattr(llm, "_summarize_with_bedrock", lambda prompt: None)
    monkeypatch.setattr(llm, "_summarize_with_gemini", lambda prompt: "from gemini")

    text, provider = llm.generate_summary("prompt")

    assert text == "from gemini"
    assert provider == "gemini"


def test_gemini_used_when_no_aws_credentials(monkeypatch):
    monkeypatch.delenv(llm.BEDROCK_TOKEN_ENV, raising=False)
    monkeypatch.delenv(llm.AWS_KEY_ENV, raising=False)
    monkeypatch.setattr(llm.settings, "bedrock_enabled", False)
    monkeypatch.setattr(llm, "_summarize_with_gemini", lambda prompt: "from gemini")

    text, provider = llm.generate_summary("prompt")

    assert text == "from gemini"
    assert provider == "gemini"
