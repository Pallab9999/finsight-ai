"""
Modulo: sync_datasets.py
Descrizione: Orchestrazione della sincronizzazione incrementale di uno o più dataset tracciati.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from bankbench_data_sync.core.domain.entities import (
    SyncOutcome,
    SyncStatus,
    SyncWatermark,
    TrackedDataset,
)
from bankbench_data_sync.core.domain.exceptions import DataSourceUnavailableError
from bankbench_data_sync.core.ports.data_source import OpenDataSourcePort
from bankbench_data_sync.core.ports.repository import (
    RecordRepositoryPort,
    SyncStateRepositoryPort,
)

logger = logging.getLogger(__name__)

UPDATED_AT_SYSTEM_FIELD = ":updated_at"


class SyncDatasetsUseCase:
    """Sincronizza in modo incrementale i dataset tracciati verso lo storage locale.

    Strategia fail-soft: un dataset che fallisce (rete, schema drift) non
    interrompe la sync degli altri dataset della batch — coerente con un
    job di ingestion continua che deve restare resiliente.
    """

    def __init__(
        self,
        data_source: OpenDataSourcePort,
        sync_state_repo: SyncStateRepositoryPort,
        record_repo: RecordRepositoryPort,
    ) -> None:
        self._data_source = data_source
        self._sync_state_repo = sync_state_repo
        self._record_repo = record_repo

    def run(self, datasets: list[TrackedDataset]) -> list[SyncOutcome]:
        """Esegue un run di sync per ciascun dataset tracciato.

        Args:
            datasets: Elenco dei dataset da sincronizzare (da config/datasets.yaml).

        Returns:
            Un SyncOutcome per dataset, mai un'eccezione propagata al chiamante:
            gli errori per-dataset sono catturati e riportati come SyncStatus.FAILED.
        """
        outcomes: list[SyncOutcome] = []
        for dataset in datasets:
            outcomes.append(self._sync_one(dataset))
        return outcomes

    def _sync_one(self, dataset: TrackedDataset) -> SyncOutcome:
        watermark = self._sync_state_repo.get_watermark(dataset.dataset_id)
        logger.info(
            "Avvio sync dataset=%s da watermark=%s",
            dataset.dataset_id,
            watermark.last_synced_at,
        )

        try:
            records = self._data_source.fetch_updated_records(
                dataset_id=dataset.dataset_id,
                since=watermark.last_synced_at,
                page_size=dataset.page_size,
            )
        except DataSourceUnavailableError as err:
            logger.error("Sync fallita per dataset=%s: %s", dataset.dataset_id, err, exc_info=True)
            return SyncOutcome(dataset_id=dataset.dataset_id, status=SyncStatus.FAILED, message=str(err))

        if not records:
            self._sync_state_repo.save_watermark(
                SyncWatermark(
                    dataset_id=dataset.dataset_id,
                    last_synced_at=watermark.last_synced_at,
                    last_run_at=datetime.now(UTC),
                )
            )
            return SyncOutcome(dataset_id=dataset.dataset_id, status=SyncStatus.NO_NEW_DATA)

        drift_detected = self._check_schema_drift(dataset, records)

        written = self._record_repo.upsert_records(dataset.dataset_id, records)
        new_watermark_value = self._max_updated_at(records) or datetime.now(UTC)

        self._sync_state_repo.save_watermark(
            SyncWatermark(
                dataset_id=dataset.dataset_id,
                last_synced_at=new_watermark_value,
                last_run_at=datetime.now(UTC),
            )
        )

        status = SyncStatus.SCHEMA_DRIFT_WARNING if drift_detected else SyncStatus.OK
        logger.info(
            "Sync completata dataset=%s record_scritti=%d nuovo_watermark=%s",
            dataset.dataset_id,
            written,
            new_watermark_value,
        )
        return SyncOutcome(
            dataset_id=dataset.dataset_id,
            status=status,
            records_upserted=written,
            new_watermark=new_watermark_value,
        )

    def _check_schema_drift(self, dataset: TrackedDataset, records: list[dict[str, Any]]) -> bool:
        """Confronta le colonne attese in config con quelle effettivamente ricevute."""
        if not dataset.expected_columns:
            return False
        actual_columns = set(records[0].keys())
        missing = set(dataset.expected_columns) - actual_columns
        if missing:
            logger.warning(
                "Schema drift su dataset=%s: colonne attese mancanti=%s",
                dataset.dataset_id,
                missing,
            )
            return True
        return False

    def _max_updated_at(self, records: list[dict[str, Any]]) -> datetime | None:
        """Estrae il timestamp massimo tra i record per avanzare il watermark."""
        timestamps: list[datetime] = []
        for record in records:
            raw = record.get(UPDATED_AT_SYSTEM_FIELD)
            if not raw:
                continue
            try:
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                logger.debug("Timestamp non parsabile ignorato: %s", raw)
                continue
            # Socrata restituisce :updated_at senza suffisso di timezone (implicitamente UTC).
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            timestamps.append(parsed)
        return max(timestamps) if timestamps else None
