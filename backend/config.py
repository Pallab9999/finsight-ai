"""Application configuration."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# boto3 reads AWS credentials from the real process environment, not from
# Settings, so .env has to be exported before any client is constructed.
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
    bedrock_region: str = "us-east-1"

    api_url: str = "http://localhost:8000"
    bankbench_sqlite_path: str = (
        str(BANKBENCH_DEFAULT) if BANKBENCH_DEFAULT.parent.parent.exists() else ""
    )
    duckdb_path: Path = DUCKDB_PATH


settings = Settings()
