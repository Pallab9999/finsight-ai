# FinSight AI

Financial Intelligence & Decision Engine for SME financing assessment.

Uses:
- **UI** from [ai2b-loop-troops](https://github.com/FRA-0023/ai2b-loop-troops) (`app/main.py`)
- **Data** from [bankbench-data-sync](https://github.com/FRA-0023/ai2b-loop-troops/tree/master/bankbench-data-sync/bankbench-data-sync) (Open Data Lombardia)
- **Backend** FinSight FastAPI + DuckDB + deterministic scoring (this repo)

## Quick Start

```powershell
cd c:\Users\palla\Downloads\FinsightAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

# Sync Lombardia data + seed DuckDB
pip install -e bankbench-data-sync
python scripts/sync_and_seed.py

# Terminal 1 — API
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — UI (team dashboard)
streamlit run app/main.py
```

In the sidebar, switch to **Live API (FastAPI)** to use the real backend.

## Demo Query

```
Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan.
```

## LLM provider (optional)

The executive summary is the only LLM-generated field; every score is deterministic,
so the demo runs with no provider configured. Providers are tried in order:

1. **Amazon Bedrock** — set `AWS_BEARER_TOKEN_BEDROCK` in `.env` (or standard
   `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN`)
2. **Google Gemini** — set `GEMINI_API_KEY`
3. **Deterministic template** — no credentials needed

The `audit_trail` in every response records which provider produced the summary.

Credentials live only in `.env`, which is gitignored. Never commit them.

## Project Layout

```
FinsightAI/
├── app/                    # Team Streamlit UI (from ai2b-loop-troops)
├── bankbench-data-sync/    # Lombardia data ingestion (from ai2b-loop-troops)
├── backend/                # FastAPI + agent + tools
├── analytics/              # Deterministic scoring engines
├── ingestion/              # DuckDB loaders
├── data/finsight.duckdb    # Structured data for tools
└── scripts/                # sync_and_seed.py, seed_demo.py
```
