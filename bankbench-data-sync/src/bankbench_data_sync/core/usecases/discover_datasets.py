"""
Modulo: discover_datasets.py
Descrizione: Scoperta di dataset candidati per una categoria, tramite la fonte esterna.
"""
from __future__ import annotations

import logging
from typing import Any

from bankbench_data_sync.core.domain.exceptions import DataSourceUnavailableError
from bankbench_data_sync.core.ports.data_source import OpenDataSourcePort

logger = logging.getLogger(__name__)


class DiscoverDatasetsUseCase:
    """Interroga il catalogo della fonte per proporre dataset da tracciare.

    Non scrive nulla in autonomia: la scelta di quali dataset aggiungere a
    ``config/datasets.yaml`` resta una decisione umana (il catalogo può
    contenere dataset non pertinenti al caso d'uso di BankBench).
    """

    def __init__(self, data_source: OpenDataSourcePort) -> None:
        self._data_source = data_source

    def run(self, category: str, domain: str) -> list[dict[str, Any]]:
        """Restituisce i metadati grezzi dei dataset trovati per ``category``."""
        try:
            results = self._data_source.discover_dataset_ids(category=category, domain=domain)
        except DataSourceUnavailableError as err:
            logger.error("Discovery fallita per categoria=%s dominio=%s: %s", category, domain, err)
            return []
        logger.info("Trovati %d dataset candidati per categoria=%s", len(results), category)
        return results
