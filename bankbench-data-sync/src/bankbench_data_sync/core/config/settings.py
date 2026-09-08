"""
Modulo: settings.py
Descrizione: Configurazione centralizzata dell'applicazione (Pydantic Settings).
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_DATASETS_CONFIG: Path = PROJECT_ROOT / "config" / "datasets.yaml"
DEFAULT_SQLITE_PATH: Path = PROJECT_ROOT / "data" / "bankbench_data_sync.db"


class AppSettings(BaseSettings):
    """Impostazioni applicative lette da variabili d'ambiente / file .env.

    Nessun valore sensibile ha un default hardcoded: il token Socrata è
    opzionale (i dataset pubblici funzionano senza), ma se presente alza
    drasticamente il rate limit rispetto alle chiamate anonime.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    socrata_domain: str = Field(
        default="www.dati.lombardia.it",
        description="Dominio del portale Socrata da interrogare.",
    )
    socrata_app_token: str | None = Field(
        default=None,
        description="X-App-Token opzionale per alzare i rate limit di dati.lombardia.it.",
    )
    sqlite_path: Path = Field(default=DEFAULT_SQLITE_PATH)
    datasets_config_path: Path = Field(default=DEFAULT_DATASETS_CONFIG)
    request_timeout_seconds: float = Field(default=30.0, ge=1.0)
    max_pages_per_dataset: int = Field(
        default=200,
        ge=1,
        description="Tetto di sicurezza sulla paginazione per evitare loop infiniti su fonti anomale.",
    )
