"""
Modulo: entities.py
Descrizione: Entità di dominio pure per il sync dei dataset Open Data Lombardia.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TrackedDataset(BaseModel):
    """Un dataset Socrata che il sistema tiene sincronizzato.

    Corrisponde a una riga in config/datasets.yaml.
    """

    dataset_id: str = Field(..., min_length=4, description="4x4 Socrata (es. '98xy-uigr')")
    name: str = Field(..., description="Nome leggibile del dataset")
    category: str = Field(..., description="Categoria dati.lombardia.it (es. 'Commercio')")
    expected_columns: list[str] = Field(
        default_factory=list,
        description="Colonne minime attese, usate per il controllo di schema drift.",
    )
    page_size: int = Field(default=1000, ge=1, le=50_000)


class SyncStatus(str, Enum):
    """Esito di un run di sincronizzazione per un dataset."""

    OK = "ok"
    NO_NEW_DATA = "no_new_data"
    SCHEMA_DRIFT_WARNING = "schema_drift_warning"
    FAILED = "failed"


class SyncOutcome(BaseModel):
    """Risultato di un tentativo di sync per un singolo dataset."""

    dataset_id: str
    status: SyncStatus
    records_upserted: int = 0
    new_watermark: datetime | None = None
    message: str | None = None


class SyncWatermark(BaseModel):
    """Stato di avanzamento persistito per un dataset (per il fetch incrementale)."""

    dataset_id: str
    last_synced_at: datetime | None = None
    last_run_at: datetime | None = None
