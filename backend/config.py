"""Application configuration."""

from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# boto3 reads AWS credentials from the real process environment, not from
# Settings, so .env has to be exported before any client is constructed.
# override=False keeps an already-set empty var stuck; export_dotenv_secrets
# copies non-empty .env values into os.environ when the process still has blanks.
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
DUCKDB_PATH = DATA_DIR / "finsight.duckdb"
BANKBENCH_DEFAULT = PROJECT_ROOT / "bankbench-data-sync" / "data" / "bankbench_data_sync.db"

DEMO_QUERY = (
    "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, "
    "a textile manufacturer in Milan."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Amazon Bedrock. Credentials are read from the standard AWS environment
    # variables (AWS_BEARER_TOKEN_BEDROCK, or AWS_ACCESS_KEY_ID / SECRET /
    # SESSION_TOKEN) by boto3 itself, so they are never held in this object.
    bedrock_enabled: bool = False
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    # Nova 2 Lite accepts audio; Nova Lite v1 is image/video/text only.
    bedrock_stt_model_id: str = "amazon.nova-2-lite-v1:0"
    bedrock_region: str = "us-east-1"

    api_url: str = "http://localhost:8000"
    bankbench_sqlite_path: str = (
        str(BANKBENCH_DEFAULT) if BANKBENCH_DEFAULT.parent.parent.exists() else ""
    )
    duckdb_path: Path = DUCKDB_PATH


settings = Settings()


def export_dotenv_secrets() -> None:
    """Copy non-empty .env secrets into os.environ if the process still has blanks.

    Streamlit often starts with `AWS_BEARER_TOKEN_BEDROCK=` already in the
    environment. python-dotenv will not overwrite that empty value, so voice
    stays disabled until we push the file value in ourselves. Values are never logged.
    """
    from dotenv import dotenv_values

    values = dotenv_values(PROJECT_ROOT / ".env")
    for key in (
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        file_val = (values.get(key) or "").strip()
        env_val = (os.getenv(key) or "").strip()
        if file_val and not env_val:
            os.environ[key] = file_val


export_dotenv_secrets()


def gemini_key() -> str:
    """Gemini key from settings or GOOGLE_API_KEY. Never log the value."""
    return settings.gemini_api_key or os.getenv("GOOGLE_API_KEY", "")
