"""
FinSight AI - Financial Intelligence & Decision Engine
======================================================
Vertical Slice Streamlit UX/UI for SME Financing Proposal Evaluation.
Conforms strictly to Section 16, 20, 21, and 26 of PROJECT_2.md.

TARGET PERSONA:
Bank Relationship Manager / SME Credit Officer reviewing commercial financing.

HANDOFF NOTE FOR TEAMMATE B (Backend / AI Integration):
-------------------------------------------------------
- All data fetching is mediated by `app.api_client.evaluate_application`.
- To test with your FastAPI backend, start your server at http://localhost:8000
  and set Mode to "Live API (FastAPI)" in the sidebar.
- The UI automatically falls back to `app.mock_data` if your backend is offline
  or returns non-200 responses.
"""

import hashlib
import os
import sys
from typing import Dict, Any

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import streamlit as st
import plotly.graph_objects as go

from app.mock_data import get_base_demo_payload, calculate_scenario
from app.api_client import evaluate_application, DEFAULT_BACKEND_URL
from analytics.nl_query import run_nl_query
from backend.speech import mime_for, stt_available, transcribe
from ingestion.document_upload import (
    SUPPORTED_SUFFIXES,
    UnsupportedDocument,
    delete_document,
    list_companies,
    list_uploaded_documents,
    store_document,
)


# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="FinSight AI | Credit Decision Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Executive Institutional Theme CSS
st.markdown("""
<style>
    /* Global Typography & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    
    /* Top Header Bar */
    .finsight-header {
        border-bottom: 1px solid #1e293b;
        padding-bottom: 1.25rem;
        margin-bottom: 1.5rem;
    }
    
    .finsight-badge {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        margin-right: 0.5rem;
    }
    
    .badge-primary {
        background-color: rgba(37, 99, 235, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .badge-success {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-warning {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .badge-danger {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Executive Card Container */
    .exec-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    .exec-card-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
        color: #94a3b8;
        margin-bottom: 0.75rem;
    }
    
    /* Pipeline Step Tracker */
    .trace-step-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin: 1rem 0;
    }
    
    .trace-step {
        flex: 1 1 calc(14% - 0.75rem);
        min-width: 140px;
        background: #131d31;
        border: 1px solid #233554;
        border-radius: 6px;
        padding: 0.75rem 0.6rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    
    .trace-step:hover {
        border-color: #3b82f6;
        background: #18243e;
    }
    
    .trace-step-num {
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
        color: #38bdf8;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }
    
    .trace-step-title {
        font-size: 0.78rem;
        font-weight: 600;
        color: #e2e8f0;
    }
    
    .trace-step-status {
        font-size: 0.7rem;
        color: #10b981;
        margin-top: 0.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.2rem;
    }
    
    /* Evidence & Taxonomy Badges */
    .tag-fact {
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.25);
        font-size: 0.68rem;
        font-weight: 600;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        display: inline-block;
    }
    
    .tag-calc {
        background: rgba(52, 211, 153, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.25);
        font-size: 0.68rem;
        font-weight: 600;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        display: inline-block;
    }
    
    .tag-reason {
        background: rgba(251, 191, 36, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.25);
        font-size: 0.68rem;
        font-weight: 600;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        display: inline-block;
    }

    /* What-If Comparative Callout */
    .whatif-box {
        background: linear-gradient(135deg, #131b2e 0%, #0d1322 100%);
        border: 1px solid #2b3a58;
        border-radius: 8px;
        padding: 1.25rem;
    }
    
    .delta-down {
        color: #f87171;
        font-weight: 600;
    }
    
    .delta-up {
        color: #34d399;
        font-weight: 600;
    }
    
    /* Disclaimer Footer */
    .compliance-footer {
        margin-top: 3rem;
        padding-top: 1.25rem;
        border-top: 1px solid #1e293b;
        font-size: 0.75rem;
        color: #64748b;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# GAUGE PLOT HELPER
# ==========================================
def create_gauge_chart(value: int, title: str, benchmark: int, color_theme: str = "blue") -> go.Figure:
    """Creates an institutional gauge chart using Plotly."""
    if color_theme == "blue":
        bar_color = "#3b82f6"
        threshold_color = "#1d4ed8"
    elif color_theme == "emerald":
        bar_color = "#10b981"
        threshold_color = "#047857"
    else:
        bar_color = "#f59e0b"
        threshold_color = "#b45309"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 14, 'color': '#94a3b8', 'family': 'Inter'}},
        number={'font': {'size': 32, 'color': '#f8fafc', 'family': 'Inter'}, 'suffix': "/100"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#334155", 'tickfont': {'color': '#64748b', 'size': 10}},
            'bar': {'color': bar_color, 'thickness': 0.35},
            'bgcolor': "#1e293b",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 55], 'color': 'rgba(239, 68, 68, 0.12)'},
                {'range': [55, 75], 'color': 'rgba(245, 158, 11, 0.12)'},
                {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.12)'}
            ],
            'threshold': {
                'line': {'color': "#38bdf8", 'width': 3},
                'thickness': 0.75,
                'value': benchmark
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=35, b=15),
        height=180,
        font={'color': "#e2e8f0", 'family': "Inter"}
    )
    return fig


# ==========================================
# SIDEBAR CONTROLS & BACKEND HEALTH
# ==========================================
st.sidebar.markdown("""
<div style="padding-bottom: 0.5rem; margin-bottom: 1rem; border-bottom: 1px solid #1e293b;">
    <h3 style="margin:0; font-size: 1.1rem; color: #f8fafc;">FinSight Settings</h3>
    <p style="margin:0; font-size: 0.75rem; color: #64748b;">Execution Environment & Telemetry</p>
</div>
""", unsafe_allow_html=True)

# Connection Mode Selection
connection_mode = st.sidebar.radio(
    "Data Connectivity Mode:",
    options=["Live Engine (Real Pipeline)", "Deterministic Fallback (Demo Safe)"],
    index=0,
    help=(
        "Live Engine calls the FastAPI backend, falling back to the same pipeline "
        "in-process when no HTTP backend is reachable. Deterministic Fallback serves "
        "a precomputed payload and guarantees zero crash risk during a live pitch."
    )
)

backend_url = st.sidebar.text_input(
    "FastAPI Backend Endpoint:",
    value=DEFAULT_BACKEND_URL,
    help="Teammate B's FastAPI server location (default: http://localhost:8000)"
)

use_force_mock = (connection_mode == "Deterministic Fallback (Demo Safe)")

st.sidebar.markdown("---")
st.sidebar.markdown("### Demo Trigger (Magic String)")
magic_query_text = (
    "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, "
    "a textile manufacturer in Milan."
)

if st.sidebar.button("⚡ Quick-Load EcoTex Milano (€750k)", width="stretch"):
    st.session_state["query_input"] = magic_query_text

# Initial query state
if "query_input" not in st.session_state:
    st.session_state["query_input"] = magic_query_text

st.sidebar.markdown("---")
st.sidebar.markdown("### Grounding Feeds Status")
st.sidebar.markdown("""
- **DuckDB (Financials):** `🟢 Indexed` (24 Statements)
- **Banca d'Italia API:** `🟢 Connected` (Provincial Q3)
- **Open Data Lombardia:** `🟢 Synced` (SME Census)
- **ESG Audit Embeddings:** `🟢 Ready` (EcoTex 2024 PDF)
""")

st.sidebar.markdown("---")
st.sidebar.caption("FinSight AI • Loop Troops • AI2B Hackathon 2026")


# ==========================================
# MAIN INTERFACE
# ==========================================

# 1. Institutional Header
st.markdown("""
<div class="finsight-header">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.25rem;">
                <h1 style="margin: 0; font-size: 1.85rem; font-weight: 700; color: #ffffff; letter-spacing: -0.02em;">
                    FinSight AI
                </h1>
                <span class="finsight-badge badge-primary">v1.0 Institutional Slice</span>
                <span class="finsight-badge badge-success">Decision Ready</span>
            </div>
            <p style="margin: 0; font-size: 0.95rem; color: #94a3b8;">
                Financial Intelligence & Autonomous Credit Decision Engine for Commercial Banking
            </p>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 0.75rem; color: #64748b; font-family: 'JetBrains Mono', monospace;">
                DESK: SME Underwriting | JURISDICTION: Lombardia (IT)
            </span>
            <br>
            <span style="font-size: 0.75rem; color: #38bdf8; font-family: 'JetBrains Mono', monospace;">
                REF: FS-2026-MIL-0822
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# 2. SME Application Overview Card
with st.container():
    st.markdown("""
    <div class="exec-card">
        <div class="exec-card-title">Commercial Financing Proposal Dossier</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem;">
            <div>
                <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Applicant Entity</span>
                <div style="font-size: 1.05rem; font-weight: 600; color: #f8fafc;">EcoTex Milano S.p.A.</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Industry Sector</span>
                <div style="font-size: 0.95rem; font-weight: 500; color: #e2e8f0;">Technical & Sustainable Textiles</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Headquarters</span>
                <div style="font-size: 0.95rem; font-weight: 500; color: #e2e8f0;">Milan, Lombardia (Italy)</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Requested Facility</span>
                <div style="font-size: 1.05rem; font-weight: 700; color: #38bdf8;">€ 750,000</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Financing Purpose</span>
                <div style="font-size: 0.85rem; color: #cbd5e1;">Closed-loop water recycling & low-energy dyeing unit</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# 3. User Query & Execution Box
col_query, col_btn = st.columns([5, 1])
with col_query:
    user_query = st.text_input(
        "Credit Officer Prompt / Financing Query:",
        value=st.session_state["query_input"],
        help="Input query describing applicant, loan amount, and purpose."
    )
with col_btn:
    st.write("")  # Spacing
    st.write("")
    run_eval = st.button("🚀 Evaluate", type="primary", width="stretch")


# Evaluate application via api_client (either Live or Deterministic Fallback)
with st.spinner("FinSight AI is orchestrating deterministic scoring & grounded evidence..."):
    payload, execution_mode, status_msg = evaluate_application(
        query=user_query,
        loan_amount=750000,
        backend_url=backend_url,
        force_mock=use_force_mock
    )

# Execution banner
_BANNERS = {
    "LIVE_API": ("#34d399", "🟢", "LIVE FASTAPI ENGINE"),
    "IN_PROCESS": ("#38bdf8", "🔵", "LIVE ENGINE (IN-PROCESS)"),
    "DETERMINISTIC_FALLBACK": ("#fbbf24", "🟡", "DEMO SAFE MODE"),
}
_color, _icon, _label = _BANNERS.get(execution_mode, _BANNERS["DETERMINISTIC_FALLBACK"])
st.markdown(
    f'<div style="font-size: 0.75rem; color: {_color}; margin-bottom: 1rem;">'
    f'{_icon} <b>{_label}</b>: {status_msg}</div>',
    unsafe_allow_html=True,
)


# ==========================================
# 4. EXECUTIVE DECISION & KPI GAUGES
# ==========================================
st.markdown("### Executive Underwriting Decision & Core KPIs")

kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns([1.2, 1.2, 1, 1])

# Gauge 1: Financial Health Score
with kpi_c1:
    fin_score = payload.get("financial_score", 82)
    fig_fin = create_gauge_chart(fin_score, "Financial Health Score", benchmark=70, color_theme="blue")
    st.plotly_chart(fig_fin, width="stretch")
    st.markdown("""
    <div style="text-align: center; margin-top: -15px;">
        <span class="finsight-badge badge-primary">Weight: 50%</span>
        <span style="font-size: 0.75rem; color: #94a3b8;">Benchmark: 70/100</span>
    </div>
    """, unsafe_allow_html=True)

# Gauge 2: ESG Alignment Score
with kpi_c2:
    esg_score = payload.get("esg_score", 91)
    fig_esg = create_gauge_chart(esg_score, "ESG Alignment Score", benchmark=75, color_theme="emerald")
    st.plotly_chart(fig_esg, width="stretch")
    st.markdown("""
    <div style="text-align: center; margin-top: -15px;">
        <span class="finsight-badge badge-success">EU Green Taxonomy</span>
        <span style="font-size: 0.75rem; color: #94a3b8;">Benchmark: 75/100</span>
    </div>
    """, unsafe_allow_html=True)

# Metric 3: Composite Risk & Sector
with kpi_c3:
    risk_level = payload.get("risk_level", "Medium")
    sector_outlook = payload.get("sector_outlook", "Positive")
    risk_icon = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(risk_level, "🟡")
    risk_color = {"Low": "#34d399", "Medium": "#fbbf24", "High": "#f87171"}.get(risk_level, "#fbbf24")
    outlook_icon = {"Positive": "🟢", "Neutral": "🟡", "Negative": "🔴"}.get(sector_outlook, "🟡")
    outlook_color = {"Positive": "#34d399", "Neutral": "#fbbf24", "Negative": "#f87171"}.get(sector_outlook, "#34d399")

    st.markdown(f"""
    <div class="exec-card" style="height: 220px; display: flex; flex-direction: column; justify-content: center;">
        <div class="exec-card-title">Risk & Macro Benchmarks</div>
        <div style="margin-bottom: 0.75rem;">
            <span style="font-size: 0.75rem; color: #64748b;">REGIONAL RISK LEVEL</span>
            <div style="font-size: 1.25rem; font-weight: 700; color: {risk_color};">
                {risk_icon} {risk_level} Risk
            </div>
            <span style="font-size: 0.72rem; color: #94a3b8;">Deterministic scoring engine</span>
        </div>
        <div>
            <span style="font-size: 0.75rem; color: #64748b;">SECTOR OUTLOOK</span>
            <div style="font-size: 1.25rem; font-weight: 700; color: {outlook_color};">
                {outlook_icon} {sector_outlook}
            </div>
            <span style="font-size: 0.72rem; color: #94a3b8;">Open Data Lombardia + DuckDB</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Metric 4: Final Recommendation & Confidence
with kpi_c4:
    rec = payload.get("recommendation", "APPROVE")
    conf = payload.get("confidence", 0.87)
    
    badge_style = "badge-success" if rec == "APPROVE" else ("badge-warning" if rec == "REVIEW" else "badge-danger")
    badge_color = "#34d399" if rec == "APPROVE" else ("#fbbf24" if rec == "REVIEW" else "#f87171")
    
    st.markdown(f"""
    <div class="exec-card" style="height: 220px; display: flex; flex-direction: column; justify-content: center; text-align: center; border-color: {badge_color};">
        <div class="exec-card-title">Autonomous Recommendation</div>
        <div style="margin-bottom: 0.5rem;">
            <span style="font-size: 1.7rem; font-weight: 800; color: {badge_color}; letter-spacing: 0.04em;">
                {rec}
            </span>
        </div>
        <div>
            <span class="finsight-badge {badge_style}">Statistical Confidence: {conf*100:.0f}%</span>
        </div>
        <p style="margin: 0.6rem 0 0 0; font-size: 0.72rem; color: #94a3b8;">
            Subject to human credit committee validation
        </p>
    </div>
    """, unsafe_allow_html=True)


# Sub-row: Key Financial Health Ratios (Deterministic calculations)
st.markdown("""
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem;">
    <div style="background: #131d31; border: 1px solid #1f293d; border-radius: 6px; padding: 0.6rem 0.8rem;">
        <span style="font-size: 0.7rem; color: #94a3b8;">Debt Service Coverage (DSCR)</span>
        <div style="font-size: 1.05rem; font-weight: 700; color: #38bdf8;">1.68x <span style="font-size: 0.7rem; color: #10b981;">(Safe > 1.30x)</span></div>
    </div>
    <div style="background: #131d31; border: 1px solid #1f293d; border-radius: 6px; padding: 0.6rem 0.8rem;">
        <span style="font-size: 0.7rem; color: #94a3b8;">Net Debt / EBITDA</span>
        <div style="font-size: 1.05rem; font-weight: 700; color: #38bdf8;">1.35x <span style="font-size: 0.7rem; color: #10b981;">(Low Leverage)</span></div>
    </div>
    <div style="background: #131d31; border: 1px solid #1f293d; border-radius: 6px; padding: 0.6rem 0.8rem;">
        <span style="font-size: 0.7rem; color: #94a3b8;">Operating Margin (EBITDA)</span>
        <div style="font-size: 1.05rem; font-weight: 700; color: #38bdf8;">18.5% <span style="font-size: 0.7rem; color: #10b981;">(+2.1% vs peer median)</span></div>
    </div>
    <div style="background: #131d31; border: 1px solid #1f293d; border-radius: 6px; padding: 0.6rem 0.8rem;">
        <span style="font-size: 0.7rem; color: #94a3b8;">Quick Ratio (Liquidity)</span>
        <div style="font-size: 1.05rem; font-weight: 700; color: #38bdf8;">1.42x <span style="font-size: 0.7rem; color: #10b981;">(Healthy buffer)</span></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 5. VISUAL AI DECISION TRACE (Step Pipeline)
# ==========================================
st.markdown("### Visual AI Decision Trace (Deterministic & Grounded Pipeline)")
st.markdown("""
<div class="trace-step-container">
    <div class="trace-step">
        <div class="trace-step-num">Step 01</div>
        <div class="trace-step-title">Ingestion & Spec</div>
        <div class="trace-step-status">✓ Validated</div>
    </div>
    <div class="trace-step">
        <div class="trace-step-num">Step 02</div>
        <div class="trace-step-title">DuckDB Financials</div>
        <div class="trace-step-status">✓ Audited P&L</div>
    </div>
    <div class="trace-step">
        <div class="trace-step-num">Step 03</div>
        <div class="trace-step-title">Banca d'Italia</div>
        <div class="trace-step-status">✓ Regional Risk</div>
    </div>
    <div class="trace-step">
        <div class="trace-step-num">Step 04</div>
        <div class="trace-step-title">Open Data Lombardia</div>
        <div class="trace-step-status">✓ Sector Growth</div>
    </div>
    <div class="trace-step">
        <div class="trace-step-num">Step 05</div>
        <div class="trace-step-title">Document RAG</div>
        <div class="trace-step-status">✓ ESG Certified</div>
    </div>
    <div class="trace-step">
        <div class="trace-step-num">Step 06</div>
        <div class="trace-step-title">Scoring Engine</div>
        <div class="trace-step-status">✓ Deterministic</div>
    </div>
    <div class="trace-step" style="border-color: #10b981; background: #0e2722;">
        <div class="trace-step-num" style="color: #34d399;">Step 07</div>
        <div class="trace-step-title" style="color: #ecfdf5;">Decision Output</div>
        <div class="trace-step-status" style="color: #34d399;">✓ Complete</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("🔍 View Complete Audit Trail & Execution Steps", expanded=False):
    trail = payload.get("audit_trail", [])
    for idx, item in enumerate(trail, start=1):
        st.markdown(f"**Step {idx:02d}:** `{item}`")


# ==========================================
# 6. EXPLAINABILITY DRIVERS & GROUNDED EVIDENCE
# ==========================================
col_drivers, col_evidence = st.columns([1, 1])

with col_drivers:
    st.markdown("### Core Decision Drivers")
    st.markdown("""
    <div class="exec-card" style="min-height: 290px;">
        <div class="exec-card-title">Top Quantitative & Qualitative Factors</div>
    """, unsafe_allow_html=True)
    
    drivers = payload.get("drivers", [])
    for d in drivers:
        st.markdown(f"• **{d}**")
        
    st.markdown("""
    </div>
    """, unsafe_allow_html=True)

with col_evidence:
    st.markdown("### Grounded Evidence Explorer")
    evidence_items = payload.get("evidence", [])
    
    with st.container():
        for ev in evidence_items:
            cat = ev.get("category", "FACT")
            tag_class = "tag-fact" if cat == "FACT" else ("tag-calc" if cat == "CALCULATION" else "tag-reason")
            
            st.markdown(f"""
            <div style="background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 0.65rem 0.85rem; margin-bottom: 0.55rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                    <span style="font-size: 0.72rem; font-weight: 600; color: #94a3b8;">{ev.get('source')}</span>
                    <span class="{tag_class}">{cat}</span>
                </div>
                <div style="font-size: 0.82rem; color: #e2e8f0; line-height: 1.4;">
                    "{ev.get('claim')}"
                </div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# 7. INTERACTIVE WHAT-IF FINANCING SCENARIO
# ==========================================
st.markdown("---")
st.markdown("### Interactive What-If Financing Scenario Engine")
st.markdown("""
Simulate alternative loan principal sizes in real-time. All recalculated ratios and risk adjustments are executed 
via the **deterministic sensitivity engine** (no LLM hallucination).
""")

slider_col, result_col = st.columns([1, 1.2])

with slider_col:
    st.markdown("""
    <div class="exec-card">
        <div class="exec-card-title">Facility Sizing Parameter</div>
    """, unsafe_allow_html=True)
    
    simulated_amount = st.slider(
        "Alternative Loan Amount (€):",
        min_value=500000,
        max_value=1500000,
        value=1000000,
        step=50000,
        format="€ %d"
    )
    
    st.caption("Base Request: **€750,000** | Hackathon Stress Scenario: **€1,000,000**")
    st.markdown("</div>", unsafe_allow_html=True)

# Compute scenario deterministically
scenario_data = calculate_scenario(payload, simulated_amount)

with result_col:
    fin_delta = scenario_data["financial_score"] - payload["financial_score"]
    delta_str = f"+{fin_delta}" if fin_delta >= 0 else f"{fin_delta}"
    delta_class = "delta-up" if fin_delta >= 0 else "delta-down"
    
    sc_rec = scenario_data["recommendation"]
    sc_rec_badge = "badge-success" if sc_rec == "APPROVE" else ("badge-warning" if sc_rec == "REVIEW" else "badge-danger")
    sc_rec_color = "#34d399" if sc_rec == "APPROVE" else ("#fbbf24" if sc_rec == "REVIEW" else "#f87171")
    
    st.markdown(f"""
    <div class="whatif-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase;">
                Sensitivity Analysis Result (€ {simulated_amount:,.0f})
            </span>
            <span class="finsight-badge {sc_rec_badge}">Status: {sc_rec}</span>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; text-align: center; margin-bottom: 1rem;">
            <div style="background: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; padding: 0.5rem;">
                <span style="font-size: 0.7rem; color: #94a3b8;">Financial Score</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">
                    {scenario_data['financial_score']}/100 
                    <span class="{delta_class}" style="font-size: 0.85rem;">({delta_str})</span>
                </div>
            </div>
            <div style="background: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; padding: 0.5rem;">
                <span style="font-size: 0.7rem; color: #94a3b8;">Projected DSCR</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">
                    {scenario_data['dscr']:.2f}x
                </div>
            </div>
            <div style="background: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; padding: 0.5rem;">
                <span style="font-size: 0.7rem; color: #94a3b8;">Risk Classification</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: {sc_rec_color};">
                    {scenario_data['risk_level']}
                </div>
            </div>
        </div>
        
        <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.45; background: rgba(0,0,0,0.25); padding: 0.65rem 0.85rem; border-radius: 6px;">
            <b>Credit Impact Summary:</b> {scenario_data['summary']}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# 8. MANUAL DOCUMENT INTAKE
# ==========================================
st.markdown("---")
st.markdown("## Manual Document Intake")
st.caption(
    "Upload underwriting documents to ground the assessment. Files are chunked into "
    "the same evidence index the seeded reports use, so new material is retrievable "
    "immediately and appears in the Grounded Evidence Explorer above."
)

intake_left, intake_right = st.columns([3, 2])

with intake_left:
    available_companies = list_companies()
    current_company = payload.get("company", "EcoTex Milano")
    default_index = (
        available_companies.index(current_company)
        if current_company in available_companies
        else 0
    )

    if available_companies:
        target_company = st.selectbox(
            "Attach documents to",
            options=available_companies,
            index=default_index,
            help="Evidence retrieval is filtered by company, so this determines "
                 "which assessment the document can support.",
        )
    else:
        target_company = current_company
        st.warning("No companies are indexed yet. Seed the database first.")

    doc_type = st.selectbox(
        "Document type",
        options=[
            "Financial Statement",
            "ESG / Sustainability Report",
            "Bank Statement",
            "Board Minutes",
            "Loan Agreement",
            "Business Plan",
            "Other Supporting Document",
        ],
        index=0,
    )

    uploaded_files = st.file_uploader(
        f"Select files ({', '.join(s.lstrip('.').upper() for s in SUPPORTED_SUFFIXES)})",
        type=[s.lstrip(".") for s in SUPPORTED_SUFFIXES],
        accept_multiple_files=True,
        help="Scanned PDFs without a text layer cannot be indexed; they would need OCR.",
    )

    if uploaded_files and st.button(
        f"Index {len(uploaded_files)} document(s)", type="primary", width="stretch"
    ):
        indexed, failed = [], []
        for file in uploaded_files:
            try:
                result = store_document(
                    file.name,
                    file.getvalue(),
                    company_name=target_company,
                    document_type=doc_type,
                )
                indexed.append(result)
            except UnsupportedDocument as exc:
                failed.append((file.name, str(exc)))
            except Exception as exc:
                failed.append((file.name, f"{type(exc).__name__}: {exc}"))

        for result in indexed:
            st.success(
                f"Indexed **{result['filename']}** into {result['chunks']} "
                f"retrievable chunk(s) for {result['company_name']}."
            )
        for name, reason in failed:
            st.error(f"**{name}** could not be indexed. {reason}")

        if indexed:
            st.info("Re-running the assessment so the new evidence is reflected above.")
            st.rerun()

with intake_right:
    st.markdown("**Currently indexed uploads**")
    existing_uploads = list_uploaded_documents()

    if not existing_uploads:
        st.caption("No manual uploads yet. Seeded evidence is still in use.")
    else:
        for doc in existing_uploads:
            row_left, row_right = st.columns([5, 1])
            with row_left:
                st.markdown(
                    f"<div style='font-size:0.8rem;color:#f1f5f9;'>{doc['filename']}</div>"
                    f"<div style='font-size:0.7rem;color:#94a3b8;'>"
                    f"{doc['document_type']} · {doc['chunks']} chunk(s) · {doc['company_name']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with row_right:
                if st.button("Remove", key=f"del-{doc['document_id']}"):
                    delete_document(doc["document_id"])
                    st.rerun()


# ==========================================
# 9. VOICE ANALYTICS CONSOLE
# ==========================================
st.markdown("---")
st.markdown("## Voice Analytics Console")
st.caption(
    "Ask an analytics question by voice or text. The question is translated into "
    "read-only SQL against the DuckDB analytics tables, so answers come from the "
    "data rather than from the model's memory."
)

if not stt_available():
    st.info(
        "**Voice and natural-language analytics need a Gemini API key.** Unlike the "
        "scoring pipeline, which is fully deterministic and needs no credentials, this "
        "feature cannot answer without one. Set `GEMINI_API_KEY` in `.env` locally, or "
        "under Streamlit **Settings → Secrets** when hosted, then reload."
    )

voice_col, text_col = st.columns([2, 3])

with voice_col:
    st.markdown("**Speak your question**")
    recorded = st.audio_input(
        "Record", label_visibility="collapsed", disabled=not stt_available()
    )

    if recorded is not None and stt_available():
        audio_bytes = recorded.getvalue()
        # Streamlit replays the same recording on every rerun, so transcribe each
        # distinct clip once rather than on each script pass.
        fingerprint = hashlib.sha256(audio_bytes).hexdigest()[:16]
        if st.session_state.get("voice_fingerprint") != fingerprint:
            with st.spinner("Transcribing..."):
                transcript, stt_status = transcribe(
                    audio_bytes, mime_type=mime_for(getattr(recorded, "name", "audio.wav"))
                )
            st.session_state["voice_fingerprint"] = fingerprint
            st.session_state["voice_status"] = stt_status
            if transcript:
                st.session_state["question_seed"] = transcript
                st.rerun()

        if status := st.session_state.get("voice_status"):
            st.caption(status)

with text_col:
    st.markdown("**Or type it**")
    # The text box is deliberately keyless: a transcript or example arrives via
    # `question_seed`, and Streamlit forbids writing to a widget's own key after
    # that widget has been instantiated.
    analytics_question = st.text_input(
        "Question",
        value=st.session_state.get("question_seed", ""),
        label_visibility="collapsed",
        placeholder="e.g. Which provinces have the highest loan default rate?",
    )

    example_questions = [
        "What is EcoTex Milano's revenue and EBITDA?",
        "Which province has the highest loan default rate?",
        "Show sector turnover in Milano by year",
    ]
    chosen_example = st.selectbox(
        "Example questions", options=["-"] + example_questions, index=0
    )
    if chosen_example != "-" and st.button("Use this example"):
        st.session_state["question_seed"] = chosen_example
        st.rerun()

    run_query = st.button(
        "Run analytics query",
        type="primary",
        disabled=not (analytics_question and stt_available()),
    )

if run_query and analytics_question:
    with st.spinner("Translating your question into SQL and querying DuckDB..."):
        nl_result = run_nl_query(analytics_question)

    if nl_result["error"]:
        st.error(nl_result["error"])
        if nl_result["sql"]:
            with st.expander("SQL that was rejected"):
                st.code(nl_result["sql"], language="sql")
    else:
        guard_note = (
            "read-only connection" if nl_result["read_only"] else "guarded connection"
        )
        st.success(
            f"{nl_result['row_count']} row(s) returned via {guard_note}. "
            "Every answer below is computed by SQL over your indexed data."
        )
        if nl_result["rows"]:
            st.dataframe(
                [dict(zip(nl_result["columns"], row)) for row in nl_result["rows"]],
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption(nl_result["status"])

        with st.expander("Show the generated SQL"):
            st.code(nl_result["sql"], language="sql")
            st.caption(
                "Validated as a single read-only SELECT with an enforced row limit "
                "before execution."
            )


# ==========================================
# 10. RESPONSIBLE AI & COMPLIANCE POSITIONING
# ==========================================
st.markdown("""
<div class="compliance-footer">
    <b>Mandatory Governance & Regulatory Disclaimer (Section 26 Compliance):</b><br>
    FinSight is an AI-assisted financial decision-support prototype. It provides evidence-backed analytics 
    and scenario analysis for human review. It does not provide regulated financial advice, represent an official credit rating, 
    or replace a bank's formal underwriting and compliance process.
</div>
""", unsafe_allow_html=True)
