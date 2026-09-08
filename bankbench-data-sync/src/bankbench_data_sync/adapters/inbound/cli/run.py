"""
Modulo: run.py
Descrizione: Entrypoint CLI (sync / discover), pensato per Task Scheduler o cron.
"""
from __future__ import annotations

import argparse
import logging

import yaml

from bankbench_data_sync.core.config.dataset_registry import parse_tracked_datasets
from bankbench_data_sync.core.config.settings import AppSettings
from bankbench_data_sync.core.domain.entities import SyncStatus
from bankbench_data_sync.core.usecases.discover_datasets import DiscoverDatasetsUseCase
from bankbench_data_sync.core.usecases.sync_datasets import SyncDatasetsUseCase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def _build_socrata_client(settings: AppSettings):
    # Import locale per non creare una dipendenza rigida dell'inbound sull'implementazione
    # concreta di rete quando si eseguono solo test unitari sul core.
    from bankbench_data_sync.adapters.outbound.socrata.client import SocrataClient

    return SocrataClient(
        domain=settings.socrata_domain,
        app_token=settings.socrata_app_token,
        timeout_seconds=settings.request_timeout_seconds,
        max_pages=settings.max_pages_per_dataset,
    )


def run_sync(settings: AppSettings) -> None:
    """Esegue un ciclo di sync su tutti i dataset presenti in config/datasets.yaml."""
    from bankbench_data_sync.adapters.outbound.database.sqlite_repository import (
        SqliteRecordRepository,
        SqliteSyncStateRepository,
    )

    if not settings.datasets_config_path.exists():
        logger.error(
            "File di configurazione dataset non trovato: %s. "
            "Esegui prima 'discover' e popola config/datasets.yaml.",
            settings.datasets_config_path,
        )
        return

    raw_config = yaml.safe_load(settings.datasets_config_path.read_text(encoding="utf-8")) or {}
    tracked_datasets = parse_tracked_datasets(raw_config.get("datasets", []))
    if not tracked_datasets:
        logger.warning("Nessun dataset tracciato in %s.", settings.datasets_config_path)
        return

    data_source = _build_socrata_client(settings)
    sync_state_repo = SqliteSyncStateRepository(settings.sqlite_path)
    record_repo = SqliteRecordRepository(settings.sqlite_path)

    try:
        use_case = SyncDatasetsUseCase(data_source, sync_state_repo, record_repo)
        outcomes = use_case.run(tracked_datasets)
    finally:
        data_source.close()
        sync_state_repo.close()
        record_repo.close()

    for outcome in outcomes:
        level = logging.ERROR if outcome.status == SyncStatus.FAILED else logging.INFO
        logger.log(
            level,
            "dataset=%s status=%s record_scritti=%d %s",
            outcome.dataset_id,
            outcome.status.value,
            outcome.records_upserted,
            outcome.message or "",
        )


def run_discover(settings: AppSettings, category: str) -> None:
    """Elenca i dataset candidati per una categoria, senza scrivere config."""
    data_source = _build_socrata_client(settings)
    try:
        use_case = DiscoverDatasetsUseCase(data_source)
        results = use_case.run(category=category, domain=settings.socrata_domain)
    finally:
        data_source.close()

    if not results:
        logger.warning(
            "Nessun risultato dalla Discovery API per categoria=%s dominio=%s. "
            "Verifica connettività o prova a cercare manualmente su %s/browse?category=%s",
            category,
            settings.socrata_domain,
            settings.socrata_domain,
            category,
        )
        return

    print(f"\nDataset candidati per categoria '{category}':\n")
    for item in results:
        print(f"  - id: {item['dataset_id']:<12} nome: {item['name']}")
    print(
        "\nAggiungi manualmente quelli rilevanti a config/datasets.yaml "
        "(la discovery non scrive nulla in autonomia)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="BankBench Data Sync — ingestion Open Data Lombardia")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync", help="Sincronizza i dataset tracciati in config/datasets.yaml")

    discover_parser = subparsers.add_parser("discover", help="Elenca i dataset di una categoria")
    discover_parser.add_argument("--category", default="Commercio", help="Categoria dati.lombardia.it")

    args = parser.parse_args()
    settings = AppSettings()

    if args.command == "sync":
        run_sync(settings)
    elif args.command == "discover":
        run_discover(settings, category=args.category)


if __name__ == "__main__":
    main()
