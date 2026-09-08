# BankBench Data Sync — Architettura

Modulo di ingestion continua per i dataset Open Data di Regione Lombardia
(dati.lombardia.it, portale Socrata), pensato come layer dati per BankBench
Lombardia (densità/competitività commerciale per territorio, da incrociare
in futuro con tassi Banca d'Italia e margini di settore).

## Perché non si scrapa la pagina `/browse`

`dati.lombardia.it` è un portale **Socrata**. La pagina `/browse` è UI
client-side e il suo `robots.txt` ne vieta l'accesso automatico. Il modo
corretto e supportato per leggere/aggiornare dati è la **SODA API**
(`/resource/{id}.json`, linguaggio di query SoQL) più, per scoprire nuovi
dataset, la **Discovery API** di Socrata
(`api.us.socrata.com/api/catalog/v1`).

## Confini (Ports & Adapters)

```
core/                          ← nessuna dipendenza da adapters/, nessun I/O diretto
  domain/entities.py           ← TrackedDataset, SyncWatermark, SyncOutcome
  domain/exceptions.py         ← gerarchia errori di dominio
  ports/data_source.py         ← contratto astratto: come si legge una fonte dati esterna
  ports/repository.py          ← contratti astratti: stato di sync + storage record
  usecases/sync_datasets.py    ← orchestrazione: per ogni dataset tracciato, fetch incrementale → valida → upsert → aggiorna watermark
  usecases/discover_datasets.py← orchestrazione: interroga Discovery API per categoria e propone nuovi dataset da tracciare
  config/settings.py           ← Pydantic Settings (env-based), nessun os.getenv() sparso

adapters/
  outbound/socrata/client.py       ← implementa OpenDataSourcePort via SODA API (httpx)
  outbound/database/sqlite_repository.py ← implementa i repository port su SQLite
  inbound/cli/run.py               ← entrypoint eseguibile (per Task Scheduler / cron)
```

## Strategia di sync incrementale

Ogni dataset Socrata (NBE) espone i campi di sistema `:id`, `:created_at`,
`:updated_at`, interrogabili in SoQL. Per ogni dataset tracciato salviamo un
**watermark** (`last_synced_at`) in `sync_state`. Ad ogni run:

```
$where = :updated_at > '<ultimo watermark ISO8601>'
$order = :updated_at ASC
$limit = 1000 (paginato con $offset)
```

Se il watermark è assente (prima esecuzione), si scarica tutto lo storico
disponibile. I record vengono salvati come JSON grezzo (schema per dataset
non è fisso lato Socrata) più validazione Pandera "leggera" (tipi, non
vuoto, colonne attese secondo la config del dataset) — vedi
`data-validation` skill: fail-soft con log per l'ingestion continua, non
fail-fast bloccante, perché non vogliamo che un singolo dataset rotto
fermi la sync degli altri.

## Cosa NON fa (ancora) questo modulo

- Non normalizza/aggrega i dati per uso analitico (query engine di
  BankBench — layer successivo).
- Non integra Banca d'Italia (tassi territoriali) né margini di settore:
  vedi nota nel README, sono fonti diverse da dati.lombardia.it.
- Non espone un'API HTTP: è un job di ingestion. Se serve un livello di
  query, si aggiunge un adapter inbound FastAPI su `adapters/inbound/api/`
  senza toccare `core/`.

## Checklist

- [x] `ARCHITECTURE.md` creato prima del codice
- [x] `core/` non importa nulla da `adapters/`
- [x] Tutte le dipendenze esterne iniettate via Port (ABC)
- [x] Fake adapter nei test (nessuna dipendenza da rete/DB reale)
- [x] `main.py` unico punto di bootstrap/DI
