"""
Modulo: client.py
Descrizione: Adapter outbound verso la SODA API e la Discovery API di Socrata.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from bankbench_data_sync.core.domain.exceptions import DataSourceUnavailableError
from bankbench_data_sync.core.ports.data_source import OpenDataSourcePort

logger = logging.getLogger(__name__)

SOCRATA_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DISCOVERY_API_URL = "https://api.us.socrata.com/api/catalog/v1"


class SocrataClient(OpenDataSourcePort):
    """Client per il portale Socrata di Regione Lombardia (dati.lombardia.it).

    Usa la SODA API (`/resource/{id}.json`) per il fetch incrementale via
    SoQL sui campi di sistema `:updated_at`, e la Discovery API per
    elencare i dataset di una categoria.
    """

    def __init__(
        self,
        domain: str,
        app_token: str | None = None,
        timeout_seconds: float = 30.0,
        max_pages: int = 200,
        client: httpx.Client | None = None,
    ) -> None:
        self._domain = domain
        self._app_token = app_token
        self._timeout_seconds = timeout_seconds
        self._max_pages = max_pages
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def fetch_updated_records(
        self,
        dataset_id: str,
        since: datetime | None,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Scarica in paginazione tutti i record modificati dopo ``since``.

        Raises:
            DataSourceUnavailableError: Se una richiesta fallisce dopo aver
                esaurito i tentativi impliciti di httpx o se il payload non
                è il JSON atteso.
        """
        url = f"https://{self._domain}/resource/{dataset_id}.json"
        params_base: dict[str, Any] = {"$order": ":updated_at ASC", "$limit": page_size}
        if since is not None:
            watermark_str = since.strftime(SOCRATA_ISO_FORMAT)[:-3]
            params_base["$where"] = f":updated_at > '{watermark_str}'"

        all_records: list[dict[str, Any]] = []
        offset = 0
        for page_number in range(self._max_pages):
            params = {**params_base, "$offset": offset}
            page = self._get_json(url, params)
            if not page:
                break
            all_records.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        else:
            logger.warning(
                "Raggiunto il tetto di sicurezza max_pages=%d per dataset=%s: "
                "possibile dataset anomalo o watermark bloccato.",
                self._max_pages,
                dataset_id,
            )

        return all_records

    def discover_dataset_ids(self, category: str, domain: str) -> list[dict[str, Any]]:
        """Interroga la Discovery API per elencare i dataset di una categoria.

        Nota: la Discovery API è cross-domain (api.us.socrata.com), separata
        dal dominio del singolo portale — per questo riceve ``domain`` come
        parametro invece di usare ``self._domain``.
        """
        params = {
            "domains": domain,
            "search_context": domain,
            "categories": category,
            "only": "datasets",
            "limit": 200,
        }
        payload = self._get_json(DISCOVERY_API_URL, params)
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [
            {
                "dataset_id": item.get("resource", {}).get("id"),
                "name": item.get("resource", {}).get("name"),
                "updated_at": item.get("resource", {}).get("updatedAt"),
                "description": item.get("resource", {}).get("description"),
            }
            for item in results
        ]

    def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        headers = {"X-App-Token": self._app_token} if self._app_token else {}
        try:
            response = self._client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            raise DataSourceUnavailableError(f"Chiamata fallita verso {url}: {err}") from err
        except ValueError as err:
            raise DataSourceUnavailableError(f"Risposta non-JSON da {url}: {err}") from err

    def close(self) -> None:
        """Chiude il client HTTP sottostante."""
        self._client.close()
