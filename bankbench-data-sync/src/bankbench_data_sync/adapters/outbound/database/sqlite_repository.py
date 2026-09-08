"""
Modulo: sqlite_repository.py
Descrizione: Adapter outbound SQLite per lo stato di sync e i record grezzi.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bankbench_data_sync.core.domain.entities import SyncWatermark
from bankbench_data_sync.core.domain.exceptions import RepositoryWriteError
from bankbench_data_sync.core.ports.repository import (
    RecordRepositoryPort,
    SyncStateRepositoryPort,
)

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_state (
    dataset_id TEXT PRIMARY KEY,
    last_synced_at TEXT,
    last_run_at TEXT
);

CREATE TABLE IF NOT EXISTS raw_records (
    dataset_id TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (dataset_id, record_hash)
);
"""


def _connect(sqlite_path: Path) -> sqlite3.Connection:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.executescript(_SCHEMA)
    return connection


class SqliteSyncStateRepository(SyncStateRepositoryPort):
    """Persiste il watermark di sync per dataset in SQLite."""

    def __init__(self, sqlite_path: Path) -> None:
        self._connection = _connect(sqlite_path)

    def get_watermark(self, dataset_id: str) -> SyncWatermark:
        row = self._connection.execute(
            "SELECT dataset_id, last_synced_at, last_run_at FROM sync_state WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
        if row is None:
            return SyncWatermark(dataset_id=dataset_id)
        return SyncWatermark(
            dataset_id=row[0],
            last_synced_at=datetime.fromisoformat(row[1]) if row[1] else None,
            last_run_at=datetime.fromisoformat(row[2]) if row[2] else None,
        )

    def save_watermark(self, watermark: SyncWatermark) -> None:
        try:
            self._connection.execute(
                """
                INSERT INTO sync_state (dataset_id, last_synced_at, last_run_at)
                VALUES (:dataset_id, :last_synced_at, :last_run_at)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    last_synced_at = excluded.last_synced_at,
                    last_run_at = excluded.last_run_at
                """,
                {
                    "dataset_id": watermark.dataset_id,
                    "last_synced_at": watermark.last_synced_at.isoformat() if watermark.last_synced_at else None,
                    "last_run_at": watermark.last_run_at.isoformat() if watermark.last_run_at else None,
                },
            )
            self._connection.commit()
        except sqlite3.Error as err:
            raise RepositoryWriteError(f"Scrittura watermark fallita per {watermark.dataset_id}: {err}") from err

    def close(self) -> None:
        self._connection.close()


class SqliteRecordRepository(RecordRepositoryPort):
    """Persiste i record grezzi (JSON) con deduplica via hash del contenuto.

    I dataset Socrata non garantiscono sempre una chiave naturale stabile
    nella risposta pubblica: l'hash del payload evita duplicati quando lo
    stesso record viene ri-scaricato senza modifiche sostanziali.
    """

    def __init__(self, sqlite_path: Path) -> None:
        self._connection = _connect(sqlite_path)

    def upsert_records(self, dataset_id: str, records: list[dict[str, Any]]) -> int:
        now = datetime.now(UTC).isoformat()
        rows = [
            (dataset_id, self._hash_record(record), json.dumps(record, ensure_ascii=False), now)
            for record in records
        ]
        try:
            cursor = self._connection.executemany(
                """
                INSERT INTO raw_records (dataset_id, record_hash, payload, ingested_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(dataset_id, record_hash) DO NOTHING
                """,
                rows,
            )
            self._connection.commit()
            return cursor.rowcount if cursor.rowcount is not None else len(rows)
        except sqlite3.Error as err:
            raise RepositoryWriteError(f"Scrittura record fallita per {dataset_id}: {err}") from err

    @staticmethod
    def _hash_record(record: dict[str, Any]) -> str:
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def close(self) -> None:
        self._connection.close()
