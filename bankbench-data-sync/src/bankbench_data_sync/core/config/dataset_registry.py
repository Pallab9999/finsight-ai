"""
Modulo: dataset_registry.py
Descrizione: Trasforma la configurazione grezza (letta da YAML da un adapter) in entità di dominio.
"""
from __future__ import annotations

from typing import Any

from bankbench_data_sync.core.domain.entities import TrackedDataset


def parse_tracked_datasets(raw_entries: list[dict[str, Any]]) -> list[TrackedDataset]:
    """Converte le righe grezze di config/datasets.yaml in ``TrackedDataset`` validati.

    La lettura del file YAML resta responsabilità dell'adapter inbound (I/O);
    questa funzione è pura e quindi testabile senza filesystem.
    """
    return [TrackedDataset(**entry) for entry in raw_entries]
