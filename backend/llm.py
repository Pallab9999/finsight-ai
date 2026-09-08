"""Summary generation providers: Bedrock, then Gemini, then deterministic template.

Credentials are never stored in code or in Settings. Bedrock reads them from the
standard AWS environment variables; Gemini reads GEMINI_API_KEY from the env/.env.
"""

from __future__ import annotations

import logging
import os

from backend.config import settings

logger = logging.getLogger(__name__)

BEDROCK_TOKEN_ENV = "AWS_BEARER_TOKEN_BEDROCK"
AWS_KEY_ENV = "AWS_ACCESS_KEY_ID"


def bedrock_available() -> bool:
    """True when a Bedrock credential is present in the environment."""
    if settings.bedrock_enabled:
        return True
    return bool(os.getenv(BEDROCK_TOKEN_ENV) or os.getenv(AWS_KEY_ENV))


def _summarize_with_bedrock(prompt: str) -> str | None:
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)
        response = client.converse(
            modelId=settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.2, "maxTokens": 512},
        )
        return response["output"]["message"]["content"][0]["text"].strip()
    except Exception as exc:
        logger.warning("Bedrock summary failed: %s", exc)
        return None


def _gemini_api_key() -> str:
    return (
        settings.gemini_api_key
        or os.getenv("GEMINI_API_KEY", "")
        or os.getenv("GOOGLE_API_KEY", "")
    )


def _summarize_with_gemini(prompt: str) -> str | None:
    api_key = _gemini_api_key()
    if not api_key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=api_key,
            temperature=0.2,
        )
        content = llm.invoke(prompt).content
        if isinstance(content, list):
            content = " ".join(str(part) for part in content)
        return str(content).strip()
    except Exception as exc:
        logger.warning("Gemini summary failed: %s", exc)
        return None


def generate_summary(prompt: str) -> tuple[str | None, str]:
    """Try each provider in order.

    Returns the summary text (None if every provider failed) and the name of the
    provider that produced it, for the audit trail.
    """
    if bedrock_available():
        if text := _summarize_with_bedrock(prompt):
            return text, "bedrock"

    if text := _summarize_with_gemini(prompt):
        return text, "gemini"

    return None, "template"
