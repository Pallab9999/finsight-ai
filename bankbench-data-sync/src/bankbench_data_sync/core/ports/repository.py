"""
Modulo: repository.py
Descrizione: Contratti astratti per la persistenza dello stato di sync e dei record.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from bankbench_data_sync.core.domain.entities import SyncWatermark


class SyncStateRepositoryPort(ABC):
    """Porta astratta per leggere/scrivere il watermark di sync di ogni dataset."""

    @abstractmethod
    def get_watermark(self, dataset_id: str) -> SyncWatermark:
        """Restituisce il watermark corrente (vuoto se mai sincronizzato prima)."""

    @abstractmethod
    def save_watermark(self, watermark: SyncWatermark) -> None:
        """Persiste il nuovo watermark dopo un run di sync riuscito."""


class RecordRepositoryPort(ABC):
    """Porta astratta per l'upsert dei record grezzi di un dataset."""

    @abstractmethod
    def upsert_records(self, dataset_id: str, records: list[dict[str, Any]]) -> int:
        """Inserisce/aggiorna i record per ``dataset_id``.

        Returns:
            Numero di record effettivamente scritti (dopo deduplica).
        """
