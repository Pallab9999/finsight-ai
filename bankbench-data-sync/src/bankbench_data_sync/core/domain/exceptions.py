"""
Modulo: exceptions.py
Descrizione: Gerarchia di eccezioni di dominio per il sync dei dataset.
"""
from __future__ import annotations


class DomainError(Exception):
    """Classe base per tutti gli errori di dominio del modulo."""


class DataSourceUnavailableError(DomainError):
    """La fonte dati esterna (Socrata) non ha risposto correttamente."""


class DatasetSchemaDriftError(DomainError):
    """Le colonne restituite dalla fonte non corrispondono più a quelle attese."""


class RepositoryWriteError(DomainError):
    """Errore durante la scrittura di record o watermark nello storage locale."""
