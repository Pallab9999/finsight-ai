# BankBench Data Sync

Modulo di ingestion continua dei dataset **Open Data Regione Lombardia**
(`dati.lombardia.it`, portale Socrata) — layer dati per BankBench Lombardia.

## ⚠️ Leggi prima di tutto: cosa c'è davvero in "Commercio"

Ho verificato un dataset reale della categoria (`98xy-uigr`, "Mappa
commercio al dettaglio in Lombardia"): contiene l'**anagrafica dei punti
vendita** (Esercizi di Vicinato / Medie e Grandi Strutture — comune,
superficie di vendita, tipologia, localizzazione). È un'ottima fonte per
**densità e struttura commerciale per territorio/settore merceologico**,
non per **margini economici o redditività per settore**.

Per la logica di BankBench (stimare se un tasso è "sopra mercato" per il
settore dell'SME) i margini per ATECO andranno cercati altrove:
Camera di Commercio/InfoCamere (Excelsior, bilanci), ISTAT (conti
economici delle imprese), o dataset commerciali come Cerved/AIDA. Questo
modulo resta comunque utile come fonte di contesto territoriale/settoriale,
e l'architettura è pensata per aggiungere una seconda fonte (Banca d'Italia,
Camera di Commercio) senza toccare `core/` — basta un nuovo adapter che
implementa `OpenDataSourcePort`.

## Perché SODA API e non lo scraping di `/browse`

`dati.lombardia.it` blocca lo scraping automatico della UI (`robots.txt`).
Il modo corretto è la **SODA API** (`/resource/{id}.json`, query SoQL) per
leggere i dati, e la **Discovery API** di Socrata per elencare i dataset di
una categoria. Vedi `ARCHITECTURE.md` per i dettagli tecnici.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # su Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Copia `.env.example` in `.env` se vuoi impostare un `SOCRATA_APP_TOKEN`
(opzionale, alza i rate limit — richiedibile gratis su dev.socrata.com).

## Uso

```bash
# 1. Scopri i dataset disponibili per una categoria (non scrive nulla)
python main.py discover --category Commercio

# 2. Aggiungi manualmente gli id rilevanti a config/datasets.yaml

# 3. Sincronizza (incrementale: la prima volta scarica tutto, poi solo i delta)
python main.py sync
```

I dati finiscono in `data/bankbench_data_sync.db` (SQLite):
- tabella `raw_records`: record grezzi come JSON, deduplicati per hash
- tabella `sync_state`: watermark `:updated_at` per dataset, per il fetch incrementale

## Tenerlo sempre aggiornato

Stesso pattern del tuo Intelligence Engine (Windows Task Scheduler):

1. Apri **Utilità di pianificazione** → **Crea attività**
2. Trigger: giornaliero (i dataset di Regione Lombardia si aggiornano al
   massimo con cadenza annuale/mensile a seconda del dataset — sync più
   frequenti di 1x/giorno non portano dati nuovi, solo carico inutile sull'API)
3. Azione: `Avvia programma`
   - Programma: `<percorso>\.venv\Scripts\python.exe`
   - Argomenti: `main.py sync`
   - Cartella di lavoro: percorso del progetto

In alternativa, per un loop long-running invece di un task schedulato, si
può aggiungere un adapter con APScheduler senza toccare `core/` — fammelo
sapere se preferisci questa strada.

## Test

```bash
python -m pytest -v
```

Tutti i test girano offline con fake adapter (nessuna chiamata di rete
reale) — l'ho verificato in questa sessione: 5/5 passati, più uno smoke
test manuale su SQLite (dedup + watermark) e sul parsing di
`config/datasets.yaml`.

**Nota**: il sandbox in cui ho scritto questo codice non ha accesso di rete
a `dati.lombardia.it`, quindi non ho potuto testare la vera chiamata
`SocrataClient.fetch_updated_records` contro l'API live. La query SoQL è
costruita secondo la documentazione ufficiale Socrata (`:updated_at` come
campo di sistema), ma il primo `python main.py sync` sulla tua macchina è
il vero collaudo — se restituisce un errore HTTP, incollamelo e sistemiamo.

## Prossimi passi possibili

- Adapter per Banca d'Italia (tassi effettivi globali medi / TEGM per
  categoria di operazione) — fonte diversa, richiede un nuovo
  `OpenDataSourcePort` adapter.
- Adapter per margini/redditività di settore (Camera di Commercio / ISTAT).
- Layer di normalizzazione dei `raw_records` JSON in tabelle tipizzate per
  query analitiche (oggi sono JSON grezzo per non essere legati a uno
  schema che Socrata può cambiare).
- API FastAPI di sola lettura su `adapters/inbound/api/` per esporre i dati
  sincronizzati al resto di BankBench.
