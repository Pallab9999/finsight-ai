"""
Modulo: test_sync_usecase.py
Descrizione: Test unitari per SyncDatasetsUseCase (happy path, no-op, errore, schema drift).
"""
from __future__ import annotations

from datetime import UTC, datetime

from bankbench_data_sync.core.domain.entities import SyncStatus, TrackedDataset
from bankbench_data_sync.core.usecases.sync_datasets import SyncDatasetsUseCase
from tests.conftest import FakeSocrataDataSource


def _dataset(**overrides: object) -> TrackedDataset:
    base = {"dataset_id": "98xy-uigr", "name": "Test dataset", "category": "Commercio"}
    base.update(overrides)
    return TrackedDataset(**base)  # type: ignore[arg-type]


def test_sync_happy_path_writes_records_and_advances_watermark(
    socrata_sample_records, fake_sync_state_repo, fake_record_repo
):
    data_source = FakeSocrataDataSource(records=socrata_sample_records)
    use_case = SyncDatasetsUseCase(data_source, fake_sync_state_repo, fake_record_repo)

    outcomes = use_case.run([_dataset()])

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == SyncStatus.OK
    assert outcome.records_upserted == 2
    assert outcome.new_watermark == datetime(2026, 8, 3, 9, 30, tzinfo=UTC)
    assert fake_record_repo.written["98xy-uigr"] == socrata_sample_records


def test_sync_no_new_data_keeps_previous_watermark(fake_sync_state_repo, fake_record_repo):
    data_source = FakeSocrataDataSource(records=[])
    use_case = SyncDatasetsUseCase(data_source, fake_sync_state_repo, fake_record_repo)

    outcomes = use_case.run([_dataset()])

    assert outcomes[0].status == SyncStatus.NO_NEW_DATA
    assert outcomes[0].records_upserted == 0
    assert fake_record_repo.written == {}


def test_sync_failure_is_isolated_per_dataset(socrata_sample_records, fake_sync_state_repo, fake_record_repo):
    failing_source = FakeSocrataDataSource(raise_error=True)
    use_case = SyncDatasetsUseCase(failing_source, fake_sync_state_repo, fake_record_repo)

    outcomes = use_case.run([_dataset(dataset_id="broken-1234")])

    assert outcomes[0].status == SyncStatus.FAILED
    assert outcomes[0].message is not None
    assert fake_record_repo.written == {}


def test_sync_flags_schema_drift_without_blocking_write(
    socrata_sample_records, fake_sync_state_repo, fake_record_repo
):
    data_source = FakeSocrataDataSource(records=socrata_sample_records)
    use_case = SyncDatasetsUseCase(data_source, fake_sync_state_repo, fake_record_repo)

    dataset = _dataset(expected_columns=["comune", "colonna_inesistente"])
    outcomes = use_case.run([dataset])

    assert outcomes[0].status == SyncStatus.SCHEMA_DRIFT_WARNING
    # Anche con drift rilevato, i record vengono comunque scritti (fail-soft).
    assert outcomes[0].records_upserted == 2


def test_second_run_passes_watermark_from_first_run_to_data_source(
    socrata_sample_records, fake_sync_state_repo, fake_record_repo
):
    data_source = FakeSocrataDataSource(records=socrata_sample_records)
    use_case = SyncDatasetsUseCase(data_source, fake_sync_state_repo, fake_record_repo)

    use_case.run([_dataset()])
    assert data_source.last_call_since is None  # primo run: nessun watermark

    use_case.run([_dataset()])
    assert data_source.last_call_since == datetime(2026, 8, 3, 9, 30, tzinfo=UTC)
