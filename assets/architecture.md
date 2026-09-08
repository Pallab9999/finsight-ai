# FinSight AI Architecture

```mermaid
flowchart TB
    User[Bank User] --> Streamlit[Streamlit Dashboard]
    Streamlit -->|POST /evaluate| FastAPI[FastAPI Backend]
    FastAPI --> Agent[Agent Orchestrator]
    Agent --> Tools[Tool Layer]
    Tools --> DuckDB[(DuckDB)]
    Agent --> Scoring[Deterministic Scoring]
    Agent --> Gemini[Gemini LLM]
    Scoring --> Agent
    Gemini --> Agent
    Agent --> Response[Structured JSON]
    Response --> Streamlit
```

## Data Sources

- **company_financials**: EcoTex Milano synthetic SME data
- **regional_risk**: Lombardia credit conditions (Banca d'Italia style)
- **sector_performance**: Open Data Lombardia + synthetic
- **esg_data**: Company ESG indicators
- **documents**: Chunked sustainability reports for RAG

## Key Principle

The LLM explains trusted calculations — it does NOT calculate financial scores.
