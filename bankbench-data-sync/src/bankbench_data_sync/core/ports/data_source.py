"""
Modulo: data_source.py
Descrizione: Contratto astratto per una fonte dati Open Data esterna (Socrata o altro).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class OpenDataSourcePort(ABC):
    """Porta astratta verso una fonte di open data con supporto a fetch incrementale."""

    @abstractmethod
    def fetch_updated_records(
        self,
        dataset_id: str,
        since: datetime | None,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Recupera tutti i record di ``dataset_id`` modificati dopo ``since``.

        Args:
            dataset_id: Identificativo del dataset presso la fonte.
            since: Timestamp di ultimo sync noto. Se None, scarica tutto lo storico.
            page_size: Dimensione di pagina per la paginazione lato fonte.

        Returns:
            Lista di record grezzi (dict), ordinati per data di modifica crescente.

        Raises:
            DataSourceUnavailableError: Se la fonte non risponde o risponde con errore.
        """

    @abstractmethod
    def discover_dataset_ids(self, category: str, domain: str) -> list[dict[str, Any]]:
        """Interroga il catalogo della fonte per elencare i dataset di una categoria.

        Args:
            category: Categoria da filtrare (es. 'Commercio').
            domain: Dominio del portale open data (es. 'www.dati.lombardia.it').

        Returns:
            Lista di metadati grezzi dei dataset trovati (id, nome, ultimo aggiornamento).
        """
