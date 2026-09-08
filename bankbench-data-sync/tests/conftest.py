"""
Modulo: conftest.py
Descrizione: Fake adapter (in-memory) per testare i use case senza rete o DB reale.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from bankbench_data_sync.core.domain.entities import SyncWatermark
from bankbench_data_sync.core.ports.data_source import OpenDataSourcePort
from bankbench_data_sync.core.ports.repository import (
    RecordRepositoryPort,
    SyncStateRepositoryPort,
)

FIXTURES_DIR = Path(__file__).parent / "unit" / "fixtures"


class FakeSocrataDataSource(OpenDataSourcePort):
    """Restituisce record precaricati da fixture invece di chiamare la rete."""

    def __init__(self, records: list[dict[str, Any]] | None = None, raise_error: bool = False) -> None:
        self._records = records if records is not None else []
        self._raise_error = raise_error
        self.last_call_since: datetime | None = None

    def fetch_updated_records(
        self, dataset_id: str, since: datetime | None, page_size: int
    ) -> list[dict[str, Any]]:
        from bankbench_data_sync.core.domain.exceptions import DataSourceUnavailableError

        self.last_call_since = since
        if self._raise_error:
            raise DataSourceUnavailableError("fonte simulata non disponibile")
        return self._records

    def discover_dataset_ids(self, category: str, domain: str) -> list[dict[str, Any]]:
        return []


class FakeSyncStateRepository(SyncStateRepositoryPort):
    """Watermark in memoria, azzerati ad ogni test."""

    def __init__(self) -> None:
        self._store: dict[str, SyncWatermark] = {}

    def get_watermark(self, dataset_id: str) -> SyncWatermark:
        return self._store.get(dataset_id, SyncWatermark(dataset_id=dataset_id))

    def save_watermark(self, watermark: SyncWatermark) -> None:
        self._store[watermark.dataset_id] = watermark


class FakeRecordRepository(RecordRepositoryPort):
    """Storage in memoria dei record scritti, per asserzioni nei test."""

    def __init__(self) -> None:
        self.written: dict[str, list[dict[str, Any]]] = {}

    def upsert_records(self, dataset_id: str, records: list[dict[str, Any]]) -> int:
        self.written.setdefault(dataset_id, []).extend(records)
        return len(records)


@pytest.fixture
def socrata_sample_records() -> list[dict[str, Any]]:
    return json.loads((FIXTURES_DIR / "socrata_sample.json").read_text(encoding="utf-8"))


@pytest.fixture
def fake_sync_state_repo() -> FakeSyncStateRepository:
    return FakeSyncStateRepository()


@pytest.fixture
def fake_record_repo() -> FakeRecordRepository:
    return FakeRecordRepository()
