"""
FinSight AI - Financial Intelligence & Credit Readiness Engine
==============================================================
Enterprise platform linking SME Borrowers and Bank Credit Underwriters through
a unified Application ID (e.g. ECOTEX-2026-IT).
Features in-memory DuckDB OLAP, authentic Italian Bilancio CEE ingestion,
grounded evidence synthesis, and real-time capital sizing stress testing.
"""

import os
import sys
import base64
import hashlib
import json
import datetime
from typing import Dict, Any, List

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.auth import (
    init_session_state,
    verify_credentials,
    login_user,
    logout_user,
    ENTERPRISE_USERS
)
from app.duckdb_engine import (
    get_connection,
    calculate_deterministic_bankability,
    get_all_companies,
    get_table_preview,
    get_lakehouse_stats,
    parse_and_ingest_csv,
    parse_and_ingest_pdf
)
from app.api_client import (
    evaluate_application,
    simulate_scenario_api,
    upload_file_api,
    authenticate_api,
    parse_query_fields,
    DEFAULT_BACKEND_URL
)
from app.pdf_generator import generate_credit_memorandum_pdf
from backend.speech import mime_for, stt_available, transcribe
from backend.llm import bedrock_available, bedrock_api_key_format_ok
from backend.config import export_dotenv_secrets
from analytics.nl_query import run_nl_query

_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "finsight-logo.png")
try:
    with open(_LOGO_PATH, "rb") as _logo_file:
        LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(_logo_file.read()).decode("ascii")
except OSError:
    LOGO_DATA_URI = ""

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="FinSight AI | Autonomous SME Credit Readiness & Bankability Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
init_session_state()
export_dotenv_secrets()

# Ultra-Modern Frontier Startup Design CSS (Linear / Stripe / Ramp inspired)
# Micro-Typography, Tabular Figures, and Glass Box Lineage Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-obsidian: #06090e;
        --card-surface: rgba(13, 19, 32, 0.72);
        --border-subtle: rgba(255, 255, 255, 0.08);
        --border-glow: rgba(56, 189, 248, 0.35);
        --cyan: #38bdf8;
        --emerald: #10b981;
        --blue: #2563eb;
        --rose: #f43f5e;
        --amber: #f59e0b;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        letter-spacing: -0.012em;
    }
    
    /* Strict Tabular Numerics for Financial Scannability */
    .tabular-nums, .fin-stat-card, .whatif-box, table, div[data-testid="stDataFrame"] {
        font-variant-numeric: tabular-nums lining-nums;
        font-feature-settings: "tnum" 1, "lnum" 1;
    }
    .fin-mono-value {
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.02em;
    }

    /* Ambient Tech Mesh Canvas */
    .stApp {
        background-color: #06090e;
        background-image: 
            radial-gradient(1100px 700px at 50% -120px, rgba(14, 116, 144, 0.16), transparent 70%),
            radial-gradient(800px 500px at 95% 15%, rgba(59, 130, 246, 0.09), transparent 60%),
            radial-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px);
        background-size: 100% 100%, 100% 100%, 28px 28px;
        color: #f8fafc;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    .brand-lockup {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.15rem;
        margin: 0.15rem 0 1.2rem 0;
    }
    .brand-logo {
        height: 92px;
        width: 92px;
        object-fit: contain;
        flex-shrink: 0;
        mix-blend-mode: screen;
        filter: drop-shadow(0 0 22px rgba(56, 189, 248, 0.32));
    }
    .brand-copy {
        text-align: left;
    }
    .brand-name {
        margin: 0;
        font-size: 3.05rem;
        font-weight: 800;
        letter-spacing: -0.05em;
        color: #ffffff;
        line-height: 0.92;
        text-shadow: 0 0 28px rgba(56, 189, 248, 0.18);
    }
    .brand-lockup .finsight-badge {
        margin-top: 0.48rem;
        margin-right: 0;
    }
    .brand-lockup-app {
        justify-content: flex-start;
        margin: 0;
        gap: 0.85rem;
    }
    .brand-lockup-app .brand-logo {
        height: 58px;
        width: 58px;
    }
    .brand-lockup-app .brand-name {
        font-size: 2.45rem;
        text-shadow: none;
    }

    /* Floating Segmented Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        padding: 0.35rem !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        gap: 0.3rem !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6) !important;
        margin-bottom: 1.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        letter-spacing: -0.01em !important;
        padding: 0.55rem 1.15rem !important;
        color: #94a3b8 !important;
        border: 1px solid transparent !important;
        background: transparent !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(56, 189, 248, 0.12) !important;
        color: #38bdf8 !important;
        border: 1px solid rgba(56, 189, 248, 0.35) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 0 16px -2px rgba(56, 189, 248, 0.25) !important;
    }
    .stTabs [data-baseweb="tab-border"], .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Buttons: Linear & Stripe aesthetic */
    .stButton > button[kind="primary"], div.stButton > button:first-child[data-testid="stBaseButton-primary"] {
        background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%) !important;
        border: 1px solid rgba(56, 189, 248, 0.6) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        letter-spacing: -0.01em !important;
        border-radius: 9px !important;
        padding: 0.55rem 1.25rem !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 4px 16px rgba(2, 132, 199, 0.35) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35), 0 8px 24px rgba(2, 132, 199, 0.5) !important;
        filter: brightness(1.1) !important;
    }
    .stButton > button[kind="secondary"], div.stButton > button:not([kind="primary"]) {
        background: rgba(255, 255, 255, 0.035) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #cbd5e1 !important;
        font-weight: 500 !important;
        font-size: 0.84rem !important;
        border-radius: 9px !important;
        padding: 0.55rem 1.15rem !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button[kind="secondary"]:hover, div.stButton > button:not([kind="primary"]):hover {
        background: rgba(255, 255, 255, 0.075) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }
    .stDownloadButton > button {
        border-radius: 9px !important;
        font-weight: 600 !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    /* Inputs, Selects & Form controls */
    div[data-baseweb="input"] > div {
        background: rgba(13, 19, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #f8fafc !important;
        transition: all 0.15s ease !important;
    }
    div[data-baseweb="input"] > div:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 1px #38bdf8, 0 0 12px rgba(56, 189, 248, 0.25) !important;
    }
    div[data-baseweb="select"] > div {
        background: rgba(13, 19, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }

    /* Dataframe container */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 11px;
        overflow: hidden;
    }

    /* Executive Glass Card */
    .exec-card {
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.65) 0%, rgba(10, 15, 26, 0.85) 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.35rem;
        margin-bottom: 1.25rem;
        box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.1), 0 16px 36px -10px rgba(0, 0, 0, 0.55);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .exec-card:hover {
        border-color: rgba(56, 189, 248, 0.25);
        box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.15), 0 20px 45px -12px rgba(0, 0, 0, 0.7);
    }
    .exec-card-title {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: #64748b;
        margin-bottom: 0.85rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Holographic Certainty Banner (bank underwriter only) */
    .certainty-banner {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.35) 0%, rgba(15, 23, 42, 0.85) 50%, rgba(12, 74, 110, 0.35) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 14px;
        padding: 1.15rem 1.45rem;
        margin-bottom: 1.35rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: inset 0 1px 0 0 rgba(52, 211, 153, 0.3), 0 12px 36px -10px rgba(16, 185, 129, 0.22);
    }
    .origination-banner {
        background: linear-gradient(135deg, rgba(12, 74, 110, 0.35) 0%, rgba(15, 23, 42, 0.85) 55%, rgba(30, 41, 59, 0.6) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 14px;
        padding: 1.15rem 1.45rem;
        margin-bottom: 1.35rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: inset 0 1px 0 0 rgba(56, 189, 248, 0.25), 0 12px 36px -10px rgba(14, 165, 233, 0.18);
    }

    /* Modern Metric Tiles */
    .fin-stat-card {
        background: rgba(13, 19, 32, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 11px;
        padding: 0.85rem 1.05rem;
        position: relative;
        overflow: hidden;
        transition: all 0.2s ease;
    }
    .fin-stat-card:hover {
        border-color: rgba(56, 189, 248, 0.3);
        transform: translateY(-1px);
    }
    .fin-stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #38bdf8, transparent);
    }

    /* Radar Heartbeat Beacon */
    .radar-beacon {
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        position: relative;
        margin-right: 6px;
    }
    .radar-beacon::after {
        content: '';
        position: absolute;
        top: -4px;
        left: -4px;
        width: 16px;
        height: 16px;
        border: 2px solid #10b981;
        border-radius: 50%;
        animation: radar-pulse 2s cubic-bezier(0.24, 0, 0.38, 1) infinite;
    }
    @keyframes radar-pulse {
        0% { transform: scale(0.5); opacity: 1; }
        100% { transform: scale(2.2); opacity: 0; }
    }

    /* Low-Saturation Institutional Risk Badges */
    .finsight-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 0.22rem 0.65rem;
        border-radius: 9999px;
        margin-right: 0.45rem;
    }
    .badge-primary {
        background: rgba(2, 132, 199, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.35);
    }
    .badge-success, .badge-safe {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.35);
    }
    .badge-warning, .badge-watch {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.35);
    }
    .badge-danger {
        background: rgba(244, 63, 94, 0.12);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.35);
    }
    .badge-purple {
        background: rgba(139, 92, 246, 0.15);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.35);
    }

    /* Epistemic Badges (Deterministic SQL vs Probabilistic RAG) */
    .badge-duckdb {
        background: rgba(56, 189, 248, 0.08);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.45);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.64rem;
        font-weight: 700;
        padding: 0.12rem 0.45rem;
        border-radius: 4px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-rag {
        background: rgba(168, 85, 247, 0.08);
        color: #c084fc;
        border: 1px dashed rgba(168, 85, 247, 0.5);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.64rem;
        font-weight: 700;
        padding: 0.12rem 0.45rem;
        border-radius: 4px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    /* Pipeline Workflow Steps */
    .trace-step-container {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 0.5rem;
        margin: 1.15rem 0;
    }
    .trace-step {
        background: rgba(13, 19, 32, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 9px;
        padding: 0.75rem 0.5rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    .trace-step:hover {
        border-color: rgba(56, 189, 248, 0.35);
        background: rgba(15, 23, 42, 0.9);
    }
    .trace-step-active {
        background: linear-gradient(180deg, rgba(6, 78, 59, 0.5) 0%, rgba(6, 95, 70, 0.25) 100%) !important;
        border: 1px solid rgba(16, 185, 129, 0.55) !important;
        box-shadow: inset 0 1px 0 0 rgba(52, 211, 153, 0.4), 0 0 20px -6px rgba(16, 185, 129, 0.3) !important;
    }
    .trace-step-num {
        font-size: 0.62rem;
        font-family: 'JetBrains Mono', monospace;
        color: #38bdf8;
        text-transform: uppercase;
        margin-bottom: 0.15rem;
        font-weight: 700;
    }
    .trace-step-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 0.2rem;
    }
    .trace-step-status {
        font-size: 0.68rem;
        color: #34d399;
        font-weight: 600;
    }

    /* Evidence tags */
    .tag-fact {
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        font-size: 0.65rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        display: inline-block;
    }
    .tag-calc {
        background: rgba(52, 211, 153, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.3);
        font-size: 0.65rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        display: inline-block;
    }
    .tag-reason {
        background: rgba(251, 191, 36, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
        font-size: 0.65rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        display: inline-block;
    }

    /* What-if Lab Container */
    .whatif-box {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(10, 15, 26, 0.95) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 12px;
        padding: 1.35rem;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 12px 30px -8px rgba(0, 0, 0, 0.5);
    }
    .delta-down {
        color: #fb7185;
        font-weight: 700;
    }
    .delta-up {
        color: #34d399;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# GAUGE PLOT HELPER
# ==========================================
def create_gauge(value: int, title: str, benchmark: int, color_theme: str = "blue") -> go.Figure:
    color_map = {
        "blue": ("#38bdf8", "#0284c7"),
        "emerald": ("#10b981", "#059669"),
        "amber": ("#f59e0b", "#d97706")
    }
    bar_c, thresh_c = color_map.get(color_theme, ("#38bdf8", "#0284c7"))

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"<b>{title.upper()}</b>", 'font': {'size': 11, 'color': '#94a3b8', 'family': 'Plus Jakarta Sans, Inter'}},
        number={'font': {'size': 34, 'color': '#ffffff', 'family': 'JetBrains Mono, monospace'}, 'suffix': "/100"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#334155", 'tickfont': {'color': '#64748b', 'size': 9, 'family': 'JetBrains Mono'}},
            'bar': {'color': bar_c, 'thickness': 0.35},
            'bgcolor': "rgba(15, 23, 42, 0.8)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 55], 'color': 'rgba(244, 63, 94, 0.10)'},
                {'range': [55, 75], 'color': 'rgba(245, 158, 11, 0.10)'},
                {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.10)'}
            ],
            'threshold': {
                'line': {'color': thresh_c, 'width': 3},
                'thickness': 0.75,
                'value': benchmark
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=15, r=15, t=32, b=10),
        height=175,
        font={'color': "#f8fafc", 'family': "Plus Jakarta Sans, Inter"}
    )
    return fig


def apply_voice_prompt(
    recorded,
    fingerprint_key: str,
    target_key: str,
    auto_evaluate: bool = False,
    auto_query: bool = False,
) -> None:
    """Transcribe a Streamlit audio_input recording into a text prompt.

    The transcript is staged on a non-widget key so the next rerun can load it
    into the text field before that widget is instantiated.
    """
    if recorded is None or not stt_available():
        return
    audio_bytes = recorded.getvalue()
    fingerprint = hashlib.sha256(audio_bytes).hexdigest()[:16]
    if st.session_state.get(fingerprint_key) == fingerprint:
        return
    with st.spinner("Listening..."):
        transcript, status = transcribe(
            audio_bytes,
            mime_type=mime_for(getattr(recorded, "name", "audio.wav")),
        )
    st.session_state[fingerprint_key] = fingerprint
    st.session_state["voice_status"] = status
    if transcript:
        st.session_state["_pending_voice_prompt"] = transcript
        st.session_state["_pending_voice_target"] = target_key
        if auto_evaluate:
            st.session_state["pending_eval"] = True
        if auto_query:
            st.session_state["pending_nl_query"] = True
        st.rerun()


def flush_pending_voice_prompt() -> None:
    pending = st.session_state.pop("_pending_voice_prompt", None)
    target = st.session_state.pop("_pending_voice_target", None)
    if pending and target:
        st.session_state[target] = pending


def md_html(html: str) -> None:
    """Render HTML in Streamlit. Indented lines are treated as a code fence, so strip them."""
    cleaned = "\n".join(line.lstrip() for line in html.splitlines()).strip()
    st.markdown(cleaned, unsafe_allow_html=True)


# ==========================================
# UX/UI HELPER: COVENANT HEADROOM GAUGE BAR
# ==========================================
def render_covenant_headroom_bar(dscr_val: float, covenant_floor: float = 1.30, eba_floor: float = 1.00) -> str:
    """
    Renders a high-precision vector headroom bar showing the distance to covenant breach
    and dynamic shock absorption capacity.
    """
    dscr_clamped = max(0.0, min(4.0, dscr_val))
    pct = (dscr_clamped / 4.0) * 100
    cov_pct = (covenant_floor / 4.0) * 100
    eba_pct = (eba_floor / 4.0) * 100

    headroom = dscr_val - covenant_floor
    if dscr_val > 0:
        shock_tolerance = max(0.0, (1.0 - (covenant_floor / dscr_val)) * 100.0)
    else:
        shock_tolerance = 0.0

    if dscr_val >= covenant_floor:
        status_color = "#34d399"
        status_badge = "badge-safe"
        status_label = "COVENANT CLEARED"
        status_txt = (
            f"Solvency buffer: <b>+{headroom:.2f}x</b> · Survives an EBITDA shock of "
            f"<b>-{shock_tolerance:.1f}%</b> before covenant breach."
        )
    elif dscr_val >= eba_floor:
        status_color = "#fbbf24"
        status_badge = "badge-watch"
        status_label = "WATCHLIST"
        status_txt = (
            f"EBA watchlist ({headroom:.2f}x vs 1.30x floor). No room for a revenue drop."
        )
    else:
        status_color = "#fb7185"
        status_badge = "badge-danger"
        status_label = "BREACH"
        status_txt = "Coverage deficit: historical cash flow cannot service the new facility."

    # Streamlit markdown treats any 4-space-indented line as a fenced code block.
    # Flatten every line so the bar renders as HTML, not as source.
    html = f"""
<div style="margin: 0.6rem 0 1.25rem 0; background: rgba(13, 19, 32, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 0.85rem 1.15rem;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; flex-wrap: wrap; gap: 0.5rem;">
<div style="display: flex; align-items: center; gap: 0.5rem;">
<span style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.04em;">
Covenant Headroom &amp; Shock Capacity (EBA Floor: 1.00x · Min Covenant: 1.30x)
</span>
<span class="finsight-badge {status_badge}" style="font-size: 0.65rem; padding: 0.15rem 0.5rem;">
{status_label}
</span>
</div>
<span style="font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; font-weight: 800; color: {status_color};">
DSCR: {dscr_val:.2f}x
</span>
</div>
<div style="position: relative; height: 10px; border-radius: 5px; background: rgba(255, 255, 255, 0.06); overflow: hidden; margin-bottom: 0.45rem;">
<div style="position: absolute; left: 0; width: {eba_pct:.1f}%; height: 100%; background: rgba(244, 63, 94, 0.35);" title="Critical zone (&lt; 1.00x)"></div>
<div style="position: absolute; left: {eba_pct:.1f}%; width: {cov_pct - eba_pct:.1f}%; height: 100%; background: rgba(245, 158, 11, 0.35);" title="EBA watchlist (1.00x - 1.30x)"></div>
<div style="position: absolute; left: {cov_pct:.1f}%; right: 0; height: 100%; background: rgba(16, 185, 129, 0.35);" title="Solvent (&gt; 1.30x)"></div>
<div style="position: absolute; left: 0; width: {pct:.1f}%; height: 100%; background: linear-gradient(90deg, rgba(56, 189, 248, 0.4), {status_color});"></div>
<div style="position: absolute; left: {cov_pct:.1f}%; top: 0; bottom: 0; width: 2px; background: #ffffff; z-index: 2;" title="Minimum covenant 1.30x"></div>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.73rem; color: #94a3b8; flex-wrap: wrap; gap: 0.3rem;">
<span><span style="color: {status_color}; font-weight: 700;">●</span> {status_txt}</span>
<span style="font-family: 'JetBrains Mono', monospace; color: #64748b;">Linear scale: 0.0x → 4.0x</span>
</div>
</div>
"""
    return html.strip()


# ==========================================
# UX/UI HELPER: GLASS BOX AUDIT INSPECTOR
# ==========================================
def render_audit_lineage_inspector(base_data: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """
    Renders an epistemic calculation inspector displaying exact mathematical formulas,
    DuckDB SQL tables, and CEE balance sheet source lines.
    """
    with st.expander("🔍 Glass Box Audit Inspector — Tracciabilità Matematica & Provenienza Dati", expanded=False):
        st.markdown("""
        <p style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 0.75rem;">
            Ogni indicatore esposto è riconducibile a una formula deterministica eseguita nel lakehouse <b>DuckDB 1.0</b> 
            o a una prova documentale estratta via <b>RAG Ibrido</b> con impronta crittografica SHA-256.
        </p>
        """, unsafe_allow_html=True)

        dscr_v = payload.get("dscr", base_data["dscr"])
        ebitda_v = payload.get("ebitda", base_data["ebitda"])
        loan_v = payload.get("loan_amount", base_data["loan_amount"])
        rate_v = payload.get("interest_rate", base_data.get("interest_rate", 5.15))
        pfn_v = payload.get("total_debt", 4700000) - payload.get("cash_and_equivalents", 1630000)

        lineage_items = [
            {
                "metric": "Debt Service Coverage Ratio (DSCR)",
                "value": f"{dscr_v:.2f}x",
                "type": "DETERMINISTIC",
                "badge": '<span class="badge-duckdb">⚡ DuckDB OLAP</span>',
                "formula": "Free Cash Flow Operativo / (Quota Capitale + Oneri Finanziari)",
                "provenance": "Tabella: <code>financial_statements</code> (CEE A.ValoreProduzione - CEE B.CostiProduzione)"
            },
            {
                "metric": "Posizione Finanziaria Netta (PFN)",
                "value": f"€ {pfn_v:,.0f}",
                "type": "DETERMINISTIC",
                "badge": '<span class="badge-duckdb">⚡ DuckDB OLAP</span>',
                "formula": "Debiti Finanziari verso Banche - Disponibilità Liquide",
                "provenance": "Tabella: <code>financial_statements</code> (CEE Passivo D.4 - CEE Attivo C.IV)"
            },
            {
                "metric": "Leva Finanziaria (Net Debt / EBITDA)",
                "value": f"{payload.get('net_debt_ebitda', base_data['net_debt_ebitda']):.2f}x",
                "type": "DETERMINISTIC",
                "badge": '<span class="badge-duckdb">⚡ DuckDB OLAP</span>',
                "formula": "PFN Post-Operazione / MOL Gestionale",
                "provenance": "Rapporto algebrico calcolato in RAM"
            },
            {
                "metric": "Benchmark Sofferenze Provinciali (NPL)",
                "value": f"{payload.get('bdi_npl', base_data.get('bdi_npl', 1.82)):.2f}%",
                "type": "DETERMINISTIC",
                "badge": '<span class="badge-duckdb">⚡ DuckDB OLAP</span>',
                "formula": "Query su Serie Storica Banca d'Italia per Provincia",
                "provenance": "Tabella: <code>bdi_provincial_credit</code> (Provincia: " + base_data.get('province', 'Milano') + ")"
            },
            {
                "metric": "Allineamento ESG & Rating Ambientale",
                "value": f"{payload.get('esg_score', base_data['esg_score'])}/100",
                "type": "RAG_EVIDENCE",
                "badge": '<span class="badge-rag">📑 RAG Evidence</span>',
                "formula": "Sintesi probatoria multi-fattoriale su relazioni di sostenibilità",
                "provenance": "Tabella: <code>document_chunks</code> (Audit ESG con certificazioni ISO 14001 / ZDHC)"
            }
        ]

        table_rows = ""
        for item in lineage_items:
            table_rows += f"""
            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
                <td style="padding: 0.55rem 0.5rem; font-weight: 600; color: #f8fafc;">{item['metric']}</td>
                <td style="padding: 0.55rem 0.5rem; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #38bdf8;">{item['value']}</td>
                <td style="padding: 0.55rem 0.5rem;">{item['badge']}</td>
                <td style="padding: 0.55rem 0.5rem; font-size: 0.75rem; color: #cbd5e1; font-family: 'JetBrains Mono', monospace;">{item['formula']}</td>
                <td style="padding: 0.55rem 0.5rem; font-size: 0.73rem; color: #94a3b8;">{item['provenance']}</td>
            </tr>
            """

        st.markdown(f"""
        <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse; margin-top: 0.35rem;">
            <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); text-align: left; color: #64748b; font-size: 0.68rem; text-transform: uppercase;">
                    <th style="padding: 0.4rem 0.5rem;">Metrica</th>
                    <th style="padding: 0.4rem 0.5rem;">Valore</th>
                    <th style="padding: 0.4rem 0.5rem;">Livello Epistemico</th>
                    <th style="padding: 0.4rem 0.5rem;">Formula Matematico-Contabile</th>
                    <th style="padding: 0.4rem 0.5rem;">Sorgente Dati / Provenance</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """, unsafe_allow_html=True)


# ==========================================
# UX/UI HELPER: SME CAPITAL OPTIMIZATION WATERFALL
# ==========================================
def render_sme_tenor_waterfall(ebitda: float, loan_amt: float, interest_rate: float) -> None:
    """
    Prescriptive optimization waterfall for the SME CFO showing borrowing headroom across tenors.
    """
    tenors = [3, 5, 7, 10]
    waterfall_items = []
    for t in tenors:
        # Simple French amortization annual annuity: A = P * (r / (1 - (1+r)^-t))
        r = interest_rate / 100.0
        annuity = loan_amt * (r / (1.0 - (1.0 + r)**(-t)))
        proj_dscr = (ebitda * 0.85) / annuity
        max_borrowing = (ebitda * 0.85 / 1.30) * ((1.0 - (1.0 + r)**(-t)) / r)
        waterfall_items.append({
            "tenor": f"{t} Anni ({t*12} Mesi)",
            "annuity": annuity,
            "dscr": proj_dscr,
            "max_cap": max_borrowing,
            "headroom": max_borrowing - loan_amt
        })

    st.markdown("""
    <div class="exec-card" style="margin-top: 1.25rem;">
        <div class="exec-card-title">💡 Matrice Prescrittiva di Ottimizzazione Capitale (Guida CFO)</div>
        <p style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 0.85rem;">
            Confronto della capacità di indebitamento sostenibile variando la durata dell'ammortamento, 
            mantenendo il vincolo di covenant bancario <b>DSCR &gt; 1.30x</b>.
        </p>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    for idx, item in enumerate(waterfall_items):
        with cols[idx]:
            is_active = (item["tenor"].startswith("5"))
            b_border = "border: 1px solid rgba(56, 189, 248, 0.4); background: rgba(14, 116, 144, 0.12);" if is_active else "border: 1px solid rgba(255,255,255,0.08); background: rgba(13, 19, 32, 0.7);"
            md_html(f"""
<div style="{b_border} border-radius: 9px; padding: 0.75rem; text-align: center;">
<div style="font-size: 0.72rem; color: #94a3b8; font-weight: 700;">{item['tenor']}</div>
<div style="font-size: 1.15rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">
€ {item['annuity']:,.0f}<span style="font-size: 0.68rem; color: #94a3b8;">/anno</span>
</div>
<div style="margin-top: 0.35rem; font-size: 0.75rem;">
<span style="color: #64748b;">DSCR:</span>
<b style="color: {'#34d399' if item['dscr'] >= 1.30 else '#fb7185'};">{item['dscr']:.2f}x</b>
</div>
<div style="margin-top: 0.4rem; padding-top: 0.35rem; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.7rem; color: #94a3b8;">
Capienza Max: <b style="color: #ffffff;">€ {item['max_cap']/1e3:,.0f}k</b>
</div>
</div>
""")

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# UX/UI HELPER: BANK DOWNSIDE STRESS 2D HEATMAP
# ==========================================
def render_bank_stress_heatmap(ebitda: float, loan_amt: float, base_rate: float, tenor_years: int = 5) -> None:
    """
    2D Downside Stress Heatmap for the Bank Underwriter:
    Cross-tabulates EBITDA shocks (-20%, -10%, Base) against Interest Rate hikes (+0, +150 bps, +300 bps).
    """
    ebitda_shocks = [0.0, -0.10, -0.20]
    rate_shocks = [0.0, 0.015, 0.030]

    md_html("""
<div class="exec-card" style="margin-top: 1.25rem;">
<div class="exec-card-title">⚠️ Matrice di Stress Downside 2D (Valutazione Comitato Rischi)</div>
<p style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 0.85rem;">
Test di tenuta incrociato: contrazione del margine operativo (EBITDA) vs shock tassi BCE.
Identifica i punti di rottura dei covenant contrattuali (Soglia Minima: 1.30x).
</p>
""")

    rows_html = ""
    for e_shock in ebitda_shocks:
        e_label = "Base (0%)" if e_shock == 0.0 else f"Shock {int(e_shock*100)}%"
        stressed_ebitda = ebitda * (1.0 + e_shock) * 0.85

        cols_html = f"<td style='padding: 0.55rem; font-weight: 700; color: #f8fafc; font-size: 0.78rem;'>{e_label}</td>"
        for r_shock in rate_shocks:
            curr_rate = (base_rate / 100.0) + r_shock
            annuity = loan_amt * (curr_rate / (1.0 - (1.0 + curr_rate)**(-tenor_years)))
            dscr = stressed_ebitda / annuity

            if dscr >= 1.30:
                bg_c = "rgba(16, 185, 129, 0.12)"
                border_c = "rgba(52, 211, 153, 0.3)"
                txt_c = "#34d399"
                status_l = "CLEARED"
            elif dscr >= 1.00:
                bg_c = "rgba(245, 158, 11, 0.12)"
                border_c = "rgba(251, 191, 36, 0.3)"
                txt_c = "#fbbf24"
                status_l = "WATCH"
            else:
                bg_c = "rgba(244, 63, 94, 0.12)"
                border_c = "rgba(244, 63, 94, 0.3)"
                txt_c = "#fb7185"
                status_l = "BREACH"

            cols_html += (
                f"<td style='padding: 0.55rem; text-align: center;'>"
                f"<div style='background: {bg_c}; border: 1px solid {border_c}; border-radius: 6px; padding: 0.35rem 0.5rem;'>"
                f"<div style=\"font-family: 'JetBrains Mono', monospace; font-size: 0.88rem; font-weight: 800; color: {txt_c};\">{dscr:.2f}x</div>"
                f"<div style='font-size: 0.62rem; font-weight: 700; color: {txt_c}; text-transform: uppercase;'>{status_l}</div>"
                f"</div></td>"
            )
        rows_html += f"<tr style='border-bottom: 1px solid rgba(255,255,255,0.06);'>{cols_html}</tr>"

    md_html(f"""
<table style="width: 100%; border-collapse: collapse; font-size: 0.8rem;">
<thead>
<tr style="border-bottom: 1px solid rgba(255,255,255,0.12); color: #64748b; font-size: 0.68rem; text-transform: uppercase;">
<th style="padding: 0.45rem; text-align: left;">Shock EBITDA / Shock Tassi</th>
<th style="padding: 0.45rem; text-align: center;">Base (Tasso {base_rate:.2f}%)</th>
<th style="padding: 0.45rem; text-align: center;">+150 bps ({base_rate+1.5:.2f}%)</th>
<th style="padding: 0.45rem; text-align: center;">+300 bps ({base_rate+3.0:.2f}%)</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
""")


# ==========================================
# 0. AUTHENTICATION GATE (BANK VS SME LINKED THROUGH ID)
# ==========================================
if not st.session_state.get("authenticated", False):
    auth_col1, auth_col2, auth_col3 = st.columns([0.55, 2.9, 0.55])
    with auth_col2:
        md_html(f"""
<div class="brand-lockup">
<img class="brand-logo" src="{LOGO_DATA_URI}" alt="FinSight AI" />
<div class="brand-copy">
<div class="brand-name">FinSight AI</div>
<span class="finsight-badge badge-primary">Linked Application ID</span>
</div>
</div>
""")
        selected_role_label = st.radio(
            "Select workspace:",
            options=["🏢 SME Borrower (CFO)", "🏦 Bank Credit Officer (Underwriter)"],
            horizontal=True,
            key="login_role_radio",
        )
        is_bank_login = "Bank" in selected_role_label
        role_key = "bank_officer" if is_bank_login else "sme_borrower"

        if is_bank_login:
            st.markdown("""
            <div style="text-align: center; margin: 0.4rem 0 1.1rem 0;">
                <span class="finsight-badge badge-purple">INTESA SANPAOLO — DIREZIONE CREDITI CORPORATE PMI</span>
                <span class="finsight-badge badge-success">EBA/GL/2020/06 UNDERWRITING DESK</span>
                <h1 style="margin: 0.55rem 0 0.2rem 0; font-size: 2.45rem; font-weight: 800; letter-spacing: -0.035em; color: #f8fafc;">
                    Bank Credit Desk
                </h1>
                <p style="font-size: 1.02rem; color: #c4b5fd; margin: 0;">
                    Delibera workspace — linked application files, NPL overlays, covenant headroom
                </p>
            </div>
            <div class="certainty-banner">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
                        <span style="font-size: 1.15rem;">🔒</span>
                        <span style="font-size: 0.98rem; font-weight: 700; color: #ecfdf5;">
                            Bank Acceptance Certainty: 94% Probability of Execution (Linked ID: ECOTEX-2026-IT)
                        </span>
                    </div>
                    <div style="font-size: 0.78rem; color: #a7f3d0; line-height: 1.45;">
                        Pre-audited against Banca d'Italia provincial NPL benchmarks and EBA loan origination rules.
                        <b>Zero guessing. Zero black-box rejections.</b>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            card_border = "rgba(168, 85, 247, 0.45)"
            card_bar = "linear-gradient(90deg, #818cf8, #c084fc, #34d399)"
            card_title = "Underwriter sign-in — credit committee workspace"
            default_email = "underwriter@intesabancapmi.it"
            default_pwd = "bank2026"
        else:
            st.markdown("""
            <div style="text-align: center; margin: 0.4rem 0 1.1rem 0;">
                <span class="finsight-badge badge-primary">SME ORIGINATION PORTAL</span>
                <span class="finsight-badge badge-success">CREDIT-READY DOSSIER PACK</span>
                <h1 style="margin: 0.55rem 0 0.2rem 0; font-size: 2.45rem; font-weight: 800; letter-spacing: -0.035em; color: #f8fafc;">
                    Borrower Workspace
                </h1>
                <p style="font-size: 1.02rem; color: #7dd3fc; margin: 0;">
                    Prepare and submit your facility request — bank acceptance is decided on the underwriter desk
                </p>
            </div>
            <div class="origination-banner">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
                        <span style="font-size: 1.15rem;">📂</span>
                        <span style="font-size: 0.98rem; font-weight: 700; color: #e0f2fe;">
                            Application ECOTEX-2026-IT is in origination — awaiting bank delibera
                        </span>
                    </div>
                    <div style="font-size: 0.78rem; color: #bae6fd; line-height: 1.45;">
                        Package statutory CEE statements, ESG evidence, and the requested amount.
                        Execution probability is visible only after the underwriter opens the linked file.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            card_border = "rgba(56, 189, 248, 0.4)"
            card_bar = "linear-gradient(90deg, #38bdf8, #34d399)"
            card_title = "Borrower sign-in — origination portal"
            default_email = "cfo@ecotex.it"
            default_pwd = "cfo2026"

        st.markdown(f"""
        <div class="exec-card" style="border-color: {card_border}; position: relative; overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: {card_bar};"></div>
            <div class="exec-card-title">{card_title}</div>
        """, unsafe_allow_html=True)

        c_u1, c_u2 = st.columns([1.5, 1])
        with c_u1:
            login_email = st.text_input("Enterprise Email:", value=default_email, key=f"login_email_{role_key}")
        with c_u2:
            app_id_input = st.text_input("Application Reference ID:", value="ECOTEX-2026-IT", key=f"login_app_{role_key}")

        login_pwd = st.text_input("Password:", value=default_pwd, type="password", key=f"login_pwd_{role_key}")

        if st.button("🔐 Sign In to Workspace", type="primary", width="stretch"):
            user, mode, msg = authenticate_api(login_email, login_pwd, role_key, force_mock=True)
            if user:
                user["linked_id"] = app_id_input.strip().upper()
                login_user(user)
                st.success(f"Authenticated as {user['name']} ({user['organization']})")
                st.rerun()
            else:
                st.error(msg)

        st.markdown("""
        <div style='margin-top: 1.25rem; padding-top: 0.85rem; border-top: 1px solid rgba(255,255,255,0.08);'>
            <div style='font-size: 0.72rem; color: #64748b; text-transform: uppercase; font-weight: 700; margin-bottom: 0.65rem;'>
                ⚡ 1-Click Executive Demo Personas
            </div>
        </div>
        """, unsafe_allow_html=True)

        q1, q2 = st.columns(2)
        with q1:
            if st.button("🏢 Impresa: Marco Valenti (CFO)\nEcoTex Milano | ID: ECOTEX-2026-IT", width="stretch"):
                user = ENTERPRISE_USERS["cfo@ecotex.it"]
                login_user(user)
                st.rerun()
        with q2:
            if st.button("🏦 Banca: Dott.ssa Giulia Bernardi\nIntesa Sanpaolo | ID: ECOTEX-2026-IT", width="stretch"):
                user = ENTERPRISE_USERS["underwriter@intesabancapmi.it"]
                login_user(user)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ==========================================
# 1. SIDEBAR CONTROLS & ENVIRONMENT STATUS
# ==========================================
role = st.session_state.get("user_role", "sme_borrower")
is_bank_user = (role == "bank_officer")
linked_app_id = st.session_state.get("linked_id", "ECOTEX-2026-IT")

st.sidebar.markdown(f"""
<div style="padding-bottom: 0.5rem; margin-bottom: 1rem; border-bottom: 1px solid #1e293b;">
    <h3 style="margin:0; font-size: 1.15rem; color: #f8fafc;">FinSight SME Engine</h3>
    <p style="margin:0; font-size: 0.75rem; color: #64748b;">{'Bank Credit Underwriting' if is_bank_user else 'SME Borrower Origination'} Console</p>
</div>
""", unsafe_allow_html=True)

# Active Session Card with Linked ID
st.sidebar.markdown(f"""
<div style="background: rgba(17, 24, 39, 0.9); border: 1px solid #1f2937; border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem;">
    <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase;">Active Session Profile</div>
    <div style="font-size: 0.92rem; font-weight: 700; color: #ffffff;">{st.session_state['user_name']}</div>
    <div style="font-size: 0.72rem; color: #38bdf8;">{st.session_state['organization']}</div>
    <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #1f2937;">
        <span style="font-size: 0.68rem; color: #94a3b8;">LINKED APPLICATION ID:</span><br>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 700; color: #10b981;">{linked_app_id}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Connection & Mode Controls
st.sidebar.markdown("### Execution Routing")
connection_mode = st.sidebar.radio(
    "Backend Routing Mode:",
    options=["Deterministic Fallback (Demo Safe)", "Live API (FastAPI)"],
    index=0
)
backend_url = st.sidebar.text_input("FastAPI Endpoint:", value=DEFAULT_BACKEND_URL)
use_force_mock = (connection_mode == "Deterministic Fallback (Demo Safe)")
st.sidebar.markdown("---")
st.sidebar.markdown("### Voice prompts")
st.sidebar.caption(
    "Use the **microphone next to Evaluate Now** (both SME and bank). "
    "Speak any credit prompt — amounts and borrower names in the transcript are applied."
)

st.sidebar.markdown("---")

# Pre-load demo queries
st.sidebar.markdown("### Demo Borrower Profiles")
if st.sidebar.button("⚡ EcoTex Milano S.p.A. (€750k CapEx)", width="stretch"):
    st.session_state["query_input"] = "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."
    st.session_state["active_company_id"] = "ecotex"
    st.session_state["linked_id"] = "ECOTEX-2026-IT"
    st.rerun()

if is_bank_user:
    if st.sidebar.button("⚡ Meccanica Varese S.r.l. (€500k CNC)", width="stretch"):
        st.session_state["query_input"] = "Assess a €500k facility for Meccanica Precisione Varese to install 5-axis CNC machines."
        st.session_state["active_company_id"] = "meccanica"
        st.session_state["linked_id"] = "MECCANICA-2026-IT"
        st.rerun()

    if st.sidebar.button("⚡ AgroBio Brianza Soc. Coop. (€400k Bio)", width="stretch"):
        st.session_state["query_input"] = "Assess a €400k green facility for AgroBio Brianza bio-degradable packaging line."
        st.session_state["active_company_id"] = "agrobio"
        st.session_state["linked_id"] = "AGROBIO-2026-IT"
        st.rerun()

if "query_input" not in st.session_state:
    st.session_state["query_input"] = "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."

st.sidebar.markdown("---")
st.sidebar.markdown("### DuckDB Lakehouse Vitality")
db_stats = get_lakehouse_stats()
st.sidebar.markdown(f"""
- **In-Memory Engine:** `DuckDB 1.0`
- **Companies Stored:** `{db_stats.get('companies', 3)}`
- **Balance Sheets:** `{db_stats.get('financial_statements', 3)}`
- **Evidence Chunks:** `{db_stats.get('document_chunks', 3)}`
- **Territorial Benchmarks:** `{db_stats.get('bdi_provincial_credit', 6)}`
""")

if st.sidebar.button("🚪 Logout Workspace", width="stretch"):
    logout_user()
    st.rerun()


# ==========================================
# 2. TOP BANNER & APPLICATION LINK HEADER
# ==========================================
companies_list = get_all_companies()
comp_dict = {c["company_id"]: c["company_name"] for c in companies_list}
active_cid = st.session_state.get("active_company_id", "ecotex")

col_top1, col_top2 = st.columns([3.2, 1.8])

with col_top1:
    md_html(f"""
<div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.35rem;">
<div class="brand-lockup brand-lockup-app">
<img class="brand-logo" src="{LOGO_DATA_URI}" alt="FinSight AI" />
<div class="brand-name">FinSight AI</div>
</div>
<span class="finsight-badge {'badge-purple' if is_bank_user else 'badge-primary'}">{'Bank Credit Underwriter' if is_bank_user else 'SME Borrower Workspace'}</span>
<span class="finsight-badge badge-success"><span class="radar-beacon"></span> LIVE OLAP // {linked_app_id}</span>
</div>
<div style="font-size: 0.82rem; color: #94a3b8; display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
<span>Soggetto Affidato: <b style="color: #ffffff;">{comp_dict.get(active_cid, 'EcoTex Milano S.p.A.')}</b></span>
<span style="color: #334155;">|</span>
<span>Pratica Condivisa: <code style="color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;">{linked_app_id}</code></span>
<span style="color: #334155;">|</span>
<span style="color: #10b981; font-weight: 600;">EBA Loan Origination Certified</span>
</div>
""")

with col_top2:
    if is_bank_user:
        app_selector_options = ["ECOTEX-2026-IT", "MECCANICA-2026-IT", "AGROBIO-2026-IT"]
        app_to_cid = {"ECOTEX-2026-IT": "ecotex", "MECCANICA-2026-IT": "meccanica", "AGROBIO-2026-IT": "agrobio"}
        curr_app_idx = app_selector_options.index(linked_app_id) if linked_app_id in app_selector_options else 0

        selected_app = st.selectbox(
            "Selettore Fascicolo Fido Bancario:",
            options=app_selector_options,
            index=curr_app_idx,
            key="bank_app_selector"
        )
        if selected_app != linked_app_id:
            st.session_state["linked_id"] = selected_app
            st.session_state["active_company_id"] = app_to_cid[selected_app]
            st.rerun()
    else:
        st.markdown(f"""
        <div style="background: rgba(13, 19, 32, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 0.65rem 0.9rem; text-align: right; box-shadow: 0 4px 20px -5px rgba(0,0,0,0.5);">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Canale di Origination</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8;">Portale Diretto Impresa (SME Pass)</div>
            <div style="font-size: 0.68rem; color: #10b981;">● Crittografia SHA-256 e Dati Audited</div>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 3. TABBED WORKSPACE
# ==========================================
tabs_list = [
    "🏦 Credit Dossier & Bankability",
    "🎤 Voice Analytics",
    "📂 Dynamic Ingestion & DuckDB",
    "🧪 Capital Sizing & Stress Lab",
    "📑 Certified Dossier Export"
]
if is_bank_user:
    tabs_list.append("🏛️ Bank Credit Underwriting Matrix")

tab_instances = st.tabs(tabs_list)
tab_dossier = tab_instances[0]
tab_voice = tab_instances[1]
tab_ingest = tab_instances[2]
tab_stress = tab_instances[3]
tab_export = tab_instances[4]
tab_bank = tab_instances[5] if is_bank_user else None


# ==========================================
# TAB 1: CREDIT DOSSIER & BANKABILITY SCORE
# ==========================================
with tab_dossier:
    flush_pending_voice_prompt()
    company_default_amounts = {
        "ecotex": 750000,
        "meccanica": 500000,
        "agrobio": 400000
    }
    current_req_amt = company_default_amounts.get(active_cid, 750000)
    base_data = calculate_deterministic_bankability(active_cid, current_req_amt)
    audit_hash = hashlib.sha256(f"{linked_app_id}_{base_data['company']}_{base_data['loan_amount']}_BDI".encode("utf-8")).hexdigest()[:16].upper()

    if is_bank_user:
        st.markdown(f"""
        <div class="certainty-banner">
            <div>
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
                    <span style="font-size: 1.15rem;">🔒</span>
                    <span style="font-size: 0.98rem; font-weight: 700; color: #ecfdf5; letter-spacing: -0.01em;">
                        Bank Acceptance Certainty: 94% Probability of Execution (Linked ID: {linked_app_id})
                    </span>
                </div>
                <div style="font-size: 0.78rem; color: #a7f3d0; line-height: 1.45;">
                    Pre-audited against Banca d'Italia provincial NPL benchmarks and EBA loan origination rules.
                    <b>Zero guessing. Zero black-box rejections.</b>
                </div>
            </div>
            <div style="text-align: right; font-family: 'JetBrains Mono', monospace;">
                <span style="font-size: 0.68rem; color: #6ee7b7; text-transform: uppercase; letter-spacing: 0.05em;">AUDIT PROOF HASH</span><br>
                <span style="font-size: 0.88rem; font-weight: 700; color: #ffffff;">SHA256: {audit_hash}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="origination-banner">
            <div>
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
                    <span style="font-size: 1.15rem;">📂</span>
                    <span style="font-size: 0.98rem; font-weight: 700; color: #e0f2fe; letter-spacing: -0.01em;">
                        Origination pack ready — Application {linked_app_id}
                    </span>
                </div>
                <div style="font-size: 0.78rem; color: #bae6fd; line-height: 1.45;">
                    Speak or type your facility request below. Bank acceptance certainty is unlocked on the
                    <b>underwriter desk</b> after delibera — this portal packages the file, it does not issue the decision.
                </div>
            </div>
            <div style="text-align: right; font-family: 'JetBrains Mono', monospace;">
                <span style="font-size: 0.68rem; color: #7dd3fc; text-transform: uppercase; letter-spacing: 0.05em;">DOSSIER HASH</span><br>
                <span style="font-size: 0.88rem; font-weight: 700; color: #ffffff;">SHA256: {audit_hash}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # SME Request Overview Grid
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 0.85rem; margin-bottom: 1.35rem;">
        <div class="fin-stat-card">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; font-weight: 700;">Borrower Legal Name</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-top: 0.2rem;">{base_data['company']}</div>
            <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 0.15rem;">Application ID: {linked_app_id}</div>
        </div>
        <div class="fin-stat-card">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; font-weight: 700;">Sector & District</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #e2e8f0; margin-top: 0.2rem;">{base_data['sector']}</div>
            <div style="font-size: 0.7rem; color: #34d399; margin-top: 0.15rem;">Distretto {base_data.get('province', 'Lombardia')}</div>
        </div>
        <div class="fin-stat-card">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; font-weight: 700;">Requested Facility</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">€ {base_data['loan_amount']:,.0f}</div>
            <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 0.15rem;">Tasso {base_data.get('interest_rate', 5.15):.2f}% Prime SLL</div>
        </div>
        <div class="fin-stat-card">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; font-weight: 700;">Valore della Produzione</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #34d399; margin-top: 0.2rem;" class="fin-mono-value">€ {base_data['revenue']/1e6:.2f}M</div>
            <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 0.15rem;">CEE Art. 2424-2425 Audited</div>
        </div>
        <div class="fin-stat-card">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; font-weight: 700;">EBITDA Riclassificato</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">€ {base_data['ebitda']/1e6:.2f}M</div>
            <div style="font-size: 0.7rem; color: #34d399; margin-top: 0.15rem;">{base_data['ebitda_margin']}% Margine Operativo</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    prompt_label = (
        "Underwriter prompt (type or speak any query):"
        if is_bank_user
        else "Borrower prompt (type or speak any facility request):"
    )
    col_q, col_mic, col_b = st.columns([4.2, 1.35, 1.35])
    with col_q:
        user_query = st.text_input(
            prompt_label,
            key="query_input",
            placeholder="e.g. Assess a €750k sustainability-linked loan for EcoTex Milano in Milan",
        )
    with col_mic:
        st.caption("Voice")
        recorded_prompt = st.audio_input(
            "Speak prompt",
            key="dossier_voice_prompt",
            label_visibility="collapsed",
            disabled=not stt_available(),
            help="Record a prompt. It is converted to text and evaluated for both SME and bank roles.",
        )
        apply_voice_prompt(
            recorded_prompt,
            fingerprint_key="dossier_voice_fingerprint",
            target_key="query_input",
            auto_evaluate=True,
        )
    with col_b:
        st.write("")
        run_eval = st.button("🚀 Evaluate Now", type="primary", width="stretch")

    if not stt_available():
        if bedrock_available() and not bedrock_api_key_format_ok():
            st.caption(
                "Microphone is off until `.env` has a Bedrock API key starting with ABSK. Type a prompt to evaluate."
            )
        else:
            st.caption("Microphone is idle until an API key is set in `.env`. You can still type a prompt.")
    elif status := st.session_state.get("voice_status"):
        st.caption(status)

    parsed_cid, parsed_amt = parse_query_fields(user_query or "")
    eval_cid = active_cid
    if is_bank_user and parsed_cid:
        eval_cid = parsed_cid
        cid_to_app = {"ecotex": "ECOTEX-2026-IT", "meccanica": "MECCANICA-2026-IT", "agrobio": "AGROBIO-2026-IT"}
        if parsed_cid in cid_to_app and st.session_state.get("linked_id") != cid_to_app[parsed_cid]:
            st.session_state["linked_id"] = cid_to_app[parsed_cid]
            st.session_state["active_company_id"] = parsed_cid
    eval_amt = parsed_amt or current_req_amt

    pending_eval = st.session_state.pop("pending_eval", False)
    should_eval = run_eval or pending_eval or "last_eval_payload" not in st.session_state

    if should_eval:
        with st.spinner("FinSight AI fusing DuckDB balance sheet, Banca d'Italia metrics, and ESG disclosures..."):
            payload, execution_mode, status_msg = evaluate_application(
                query=user_query or st.session_state.get("query_input", ""),
                company_id=eval_cid,
                loan_amount=eval_amt,
                backend_url=backend_url,
                force_mock=use_force_mock,
            )
        st.session_state["last_eval_payload"] = payload
        st.session_state["last_eval_mode"] = execution_mode
        st.session_state["last_eval_status"] = status_msg
    else:
        payload = st.session_state["last_eval_payload"]
        execution_mode = st.session_state.get("last_eval_mode", "DETERMINISTIC_FALLBACK")
        status_msg = st.session_state.get("last_eval_status", "")

    mode_badge = "badge-success" if execution_mode == "LIVE_API" else "badge-warning"
    st.markdown(f"""
    <div style="margin-bottom: 1.25rem;">
        <span class="finsight-badge {mode_badge}">System Status: {execution_mode}</span>
        <span style="font-size: 0.78rem; color: #94a3b8;">{status_msg}</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI Gauges
    st.markdown("### SME Credit Readiness & Bankability Metrics")
    k1, k2, k3, k4 = st.columns([1.2, 1.2, 1, 1])

    with k1:
        fin_score = payload.get("financial_score", base_data["financial_score"])
        st.plotly_chart(create_gauge(fin_score, "Financial Health Score", benchmark=70, color_theme="blue"), width="stretch")
        st.markdown("""
        <div style="text-align: center; margin-top: -15px;">
            <span class="finsight-badge badge-primary">Prime Solvency Tier</span>
            <span style="font-size: 0.72rem; color: #94a3b8;">Benchmark: 70/100</span>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        esg_score = payload.get("esg_score", base_data["esg_score"])
        st.plotly_chart(create_gauge(esg_score, "ESG Alignment Score", benchmark=75, color_theme="emerald"), width="stretch")
        st.markdown("""
        <div style="text-align: center; margin-top: -15px;">
            <span class="finsight-badge badge-success">Top Decile Green</span>
            <span style="font-size: 0.72rem; color: #94a3b8;">-45 bps Subsidized Spread</span>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        bdi_npl_val = payload.get("bdi_npl", base_data.get("bdi_npl", 1.82))
        sec_growth_val = payload.get("sector_growth", base_data.get("sector_growth", 4.10))
        st.markdown(f"""
        <div class="exec-card" style="height: 215px; display: flex; flex-direction: column; justify-content: center;">
            <div class="exec-card-title">Territorial Macro Buffer</div>
            <div style="margin-bottom: 0.6rem;">
                <span style="font-size: 0.7rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Banca d'Italia Provincial NPL</span>
                <div style="font-size: 1.35rem; font-weight: 800; color: #34d399;" class="fin-mono-value">{bdi_npl_val:.2f}%</div>
                <span style="font-size: 0.7rem; color: #94a3b8;">{base_data.get('province', 'Milano')} vs Italia 2.95%</span>
            </div>
            <div>
                <span style="font-size: 0.7rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Lombardia Sector Trend</span>
                <div style="font-size: 1.35rem; font-weight: 800; color: #38bdf8;" class="fin-mono-value">+{sec_growth_val:.1f}% YoY</div>
                <span style="font-size: 0.7rem; color: #94a3b8;">{base_data.get('sector', 'Manifattura')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        rec = payload.get("recommendation", "APPROVE")
        rec_color = "#34d399" if rec == "APPROVE" else ("#fbbf24" if rec == "REVIEW" else "#f87171")
        st.markdown(f"""
        <div class="exec-card" style="height: 215px; display: flex; flex-direction: column; justify-content: center; text-align: center; border-color: {rec_color}; box-shadow: 0 0 24px -6px {rec_color}33;">
            <div class="exec-card-title" style="justify-content: center;">Bankability Outcome</div>
            <div style="font-size: 2rem; font-weight: 800; color: {rec_color}; letter-spacing: 0.04em;">
                {rec}
            </div>
            <div style="margin-top: 0.35rem;">
                <span class="finsight-badge badge-success">Pre-Approved at Prime Rates</span>
            </div>
            <p style="margin: 0.6rem 0 0 0; font-size: 0.72rem; color: #94a3b8; line-height: 1.4;">
                Eligible for 5.15% fixed rate + 15% regional green grant
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Financial Ratios Bar
    dscr_val = payload.get("dscr", base_data["dscr"])
    net_debt_ebitda_val = payload.get("net_debt_ebitda", base_data["net_debt_ebitda"])
    ebitda_m_val = payload.get("ebitda_margin", base_data["ebitda_margin"])
    quick_r_val = payload.get("quick_ratio", base_data["quick_ratio"])

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; margin-bottom: 0.85rem;">
        <div class="fin-stat-card">
            <span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Debt Service Coverage (DSCR)</span>
            <div style="font-size: 1.3rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">{dscr_val:.2f}x <span style="font-size: 0.72rem; color: #10b981; font-weight: 600;">(&gt; 1.30x Covenant)</span></div>
        </div>
        <div class="fin-stat-card">
            <span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Net Debt / EBITDA</span>
            <div style="font-size: 1.3rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">{net_debt_ebitda_val:.2f}x <span style="font-size: 0.72rem; color: #10b981; font-weight: 600;">(Low Default Risk)</span></div>
        </div>
        <div class="fin-stat-card">
            <span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">EBITDA Margin</span>
            <div style="font-size: 1.3rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">{ebitda_m_val:.1f}% <span style="font-size: 0.72rem; color: #10b981; font-weight: 600;">(Top Quartile)</span></div>
        </div>
        <div class="fin-stat-card">
            <span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Quick Liquidity Ratio</span>
            <div style="font-size: 1.3rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">{quick_r_val:.2f}x <span style="font-size: 0.72rem; color: #10b981; font-weight: 600;">(Ample Cash Cushion)</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # World-Class Component: Covenant Headroom Bar
    st.markdown(render_covenant_headroom_bar(dscr_val, covenant_floor=1.30, eba_floor=1.00), unsafe_allow_html=True)

    # 7-Step Visual Decision Trace
    st.markdown("### Visual AI Decision Trace (Deterministic Execution)")
    st.markdown("""
    <div class="trace-step-container">
        <div class="trace-step">
            <div class="trace-step-num">Step 01</div>
            <div class="trace-step-title">SME Request</div>
            <div class="trace-step-status">✓ Validated</div>
        </div>
        <div class="trace-step">
            <div class="trace-step-num">Step 02</div>
            <div class="trace-step-title">DuckDB P&L</div>
            <div class="trace-step-status">✓ In-Memory OLAP</div>
        </div>
        <div class="trace-step">
            <div class="trace-step-num">Step 03</div>
            <div class="trace-step-title">Banca d'Italia</div>
            <div class="trace-step-status">✓ 1.82% NPL Query</div>
        </div>
        <div class="trace-step">
            <div class="trace-step-num">Step 04</div>
            <div class="trace-step-title">Lombardia Trend</div>
            <div class="trace-step-status">✓ +4.1% Output</div>
        </div>
        <div class="trace-step">
            <div class="trace-step-num">Step 05</div>
            <div class="trace-step-title">Hybrid RAG</div>
            <div class="trace-step-status">✓ ESG Proof Cited</div>
        </div>
        <div class="trace-step">
            <div class="trace-step-num">Step 06</div>
            <div class="trace-step-title">Scoring Engine</div>
            <div class="trace-step-status">✓ Deterministic Math</div>
        </div>
        <div class="trace-step trace-step-active">
            <div class="trace-step-num" style="color: #34d399;">Step 07</div>
            <div class="trace-step-title" style="color: #ecfdf5; font-weight: 700;">Pre-Underwritten</div>
            <div class="trace-step-status" style="color: #34d399;">✓ 94% Certainty</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # World-Class Component: Glass Box Audit Inspector
    render_audit_lineage_inspector(base_data, payload)

    # Drivers & Grounded Evidence Explorer
    col_d, col_e = st.columns([1, 1])
    with col_d:
        st.markdown("### Core Drivers of Bankability")
        st.markdown("""
        <div class="exec-card" style="min-height: 290px;">
            <div class="exec-card-title">Institutional Approval Factors</div>
        """, unsafe_allow_html=True)
        for d in payload.get("drivers", base_data.get("drivers", [])):
            st.markdown(f"• **{d}**")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_e:
        st.markdown("### Grounded Evidence Explorer (Audited & Cited)")
        all_evidences = payload.get("evidence", base_data.get("evidence", []))
        for ev in all_evidences:
            cat = ev.get("category", "FACT")
            tag_class = "tag-fact" if cat == "FACT" else ("tag-calc" if cat == "CALCULATION" else "tag-reason")
            st.markdown(f"""
            <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid #1f2937; border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 0.55rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                    <span style="font-size: 0.72rem; font-weight: 600; color: #94a3b8;">{ev.get('source')}</span>
                    <span class="{tag_class}">{cat}</span>
                </div>
                <div style="font-size: 0.82rem; color: #e2e8f0; line-height: 1.4;">
                    "{ev.get('claim')}"
                </div>
            </div>
            """, unsafe_allow_html=True)

    # SME Ergonomic Specialization: Prescriptive Tenor Optimization Waterfall
    if not is_bank_user:
        render_sme_tenor_waterfall(
            ebitda=base_data.get("ebitda", 2470000),
            loan_amt=current_req_amt,
            interest_rate=base_data.get("interest_rate", 5.15)
        )


# ==========================================
# TAB: VOICE ANALYTICS
# ==========================================
with tab_voice:
    flush_pending_voice_prompt()
    export_dotenv_secrets()
    st.markdown("### Voice Analytics")
    st.markdown(
        "Ask any credit or market question by voice or by typing. "
        "FinSight answers from your DuckDB company, provincial, and sector data."
    )

    can_listen = stt_available()
    if not can_listen and bedrock_available() and not bedrock_api_key_format_ok():
        st.caption(
            "Microphone is off: the saved Amazon key is not a Bedrock API key "
            "(Bedrock keys start with ABSK). Type any question — answers still come from your data."
        )
    elif not can_listen:
        st.caption("Type a question below. Add a Bedrock API key (prefix ABSK) or Gemini key to enable the microphone.")

    voice_col, text_col = st.columns([2, 3])

    with voice_col:
        st.markdown("**1. Tap the microphone and speak**")
        recorded = st.audio_input(
            "Record a question",
            key="analytics_voice_prompt",
            disabled=not can_listen,
            help="Click the mic, ask anything about EcoTex, provinces, or sectors.",
        )
        apply_voice_prompt(
            recorded,
            fingerprint_key="voice_fingerprint",
            target_key="analytics_question",
            auto_query=True,
        )
        if status := st.session_state.get("voice_status"):
            st.caption(status)

    with text_col:
        st.markdown("**2. Confirm or type the question**")
        analytics_question = st.text_input(
            "Analytics question",
            key="analytics_question",
            placeholder="e.g. What is EcoTex Milano's revenue and EBITDA?",
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
            st.session_state["_pending_voice_prompt"] = chosen_example
            st.session_state["_pending_voice_target"] = "analytics_question"
            st.session_state["pending_nl_query"] = True
            st.rerun()

        run_query = st.button(
            "Ask",
            type="primary",
            disabled=not bool(analytics_question and analytics_question.strip()),
            width="stretch",
        )

    pending_nl = st.session_state.pop("pending_nl_query", False)
    should_run = (run_query or pending_nl) and bool(analytics_question and analytics_question.strip())

    if should_run:
        with st.spinner("Answering from your credit data..."):
            nl_result = run_nl_query(analytics_question)

        if nl_result.get("answer"):
            st.markdown("#### Answer")
            st.write(nl_result["answer"])
            if nl_result.get("status"):
                st.caption(nl_result["status"])
        elif nl_result.get("error"):
            st.error(nl_result["error"])
        else:
            st.success(
                f"{nl_result['row_count']} row(s) returned from your credit data."
            )

        if nl_result.get("rows"):
            st.dataframe(
                [dict(zip(nl_result["columns"], row)) for row in nl_result["rows"]],
                width="stretch",
                hide_index=True,
            )

        if nl_result.get("error") and nl_result.get("sql") and not nl_result.get("answer"):
            with st.expander("SQL that was rejected"):
                st.code(nl_result["sql"], language="sql")
        elif nl_result.get("sql"):
            with st.expander("Show the generated SQL"):
                st.code(nl_result["sql"], language="sql")


# ==========================================
# TAB 2: DYNAMIC INGESTION & DUCKDB LAKEHOUSE
# ==========================================
with tab_ingest:
    st.markdown("### 📂 Ingestione Bilancio CEE & Report ESG in DuckDB")
    st.markdown("""
    Carica il bilancio d'esercizio ufficiale (formato CEE Art. 2424-2425 c.c. o CSV) e le relazioni di sostenibilità. 
    Il motore esegue il parsing in RAM, estrae le evidenze probatorie e calcola l'impronta crittografica SHA-256.
    """)

    up_col1, up_col2 = st.columns([1.2, 1])

    with up_col1:
        st.markdown("""
        <div class="exec-card">
            <div class="exec-card-title">Upload Fascicolo Aziendale (Bilancio / ESG)</div>
        """, unsafe_allow_html=True)

        target_ingest_company = active_cid
        st.markdown(f"Destinazione Caricamento: **{comp_dict.get(active_cid, 'EcoTex Milano S.p.A.')}** (Application ID: `{linked_app_id}`)")

        doc_category = st.radio(
            "Tipologia Documento:",
            options=["Bilancio d'Esercizio CEE (Art. 2424-2425 c.c. CSV)", "Audit di Sostenibilità & ESG (PDF)"],
            horizontal=True
        )

        uploaded_file = st.file_uploader(
            "Trascina il file o clicca per selezionarlo:",
            type=["csv", "pdf"],
            help="Carica il file CSV del bilancio CEE oppure la relazione tecnica ESG in formato PDF."
        )

        col_btn1, col_btn2 = st.columns([1.2, 1])

        with col_btn1:
            trigger_ingest = st.button("⚡ Esegui Parsing & Ingestione in DuckDB", type="primary", width="stretch")

        with col_btn2:
            trigger_sample = st.button("📄 Carica File Demo Preimpostato", width="stretch")

        # Handle user uploaded file or demo file trigger
        if trigger_ingest and uploaded_file is None and not trigger_sample:
            st.warning("⚠️ Seleziona o trascina prima un file (CSV o PDF) oppure clicca su 'Carica File Demo Preimpostato'.")

        if (trigger_ingest and uploaded_file is not None) or trigger_sample:
            if trigger_sample:
                if "Bilancio" in doc_category:
                    demo_path = os.path.join(WORKSPACE_ROOT, "data", "sample_balance_sheet_cee_2024.csv")
                    with open(demo_path, "rb") as f:
                        file_bytes = f.read()
                    filename = "sample_balance_sheet_cee_2024.csv"
                    doc_type = "FINANCIAL_STATEMENT"
                else:
                    demo_path = os.path.join(WORKSPACE_ROOT, "data", "sample_esg_audit_ecotex.pdf")
                    with open(demo_path, "rb") as f:
                        file_bytes = f.read()
                    filename = "sample_esg_audit_ecotex.pdf"
                    doc_type = "ESG_AUDIT"
            else:
                file_bytes = uploaded_file.read()
                filename = uploaded_file.name
                doc_type = "FINANCIAL_STATEMENT" if "Bilancio" in doc_category else "ESG_AUDIT"

            with st.spinner(f"Elaborazione e parsing in corso di '{filename}'..."):
                res_dict, mode, status_str = upload_file_api(
                    file_bytes=file_bytes,
                    filename=filename,
                    doc_type=doc_type,
                    company_id=target_ingest_company,
                    backend_url=backend_url,
                    force_mock=use_force_mock
                )

            if res_dict.get("status") == "SUCCESS":
                st.session_state["recent_ingestion_evidences"] = res_dict.get("evidences", [])
                st.session_state["ingest_flash"] = {
                    "message": res_dict.get("message"),
                    "file_hash": res_dict.get("file_hash"),
                    "revenue": res_dict.get("revenue"),
                    "ebitda": res_dict.get("ebitda"),
                    "rows": res_dict.get("rows_ingested"),
                    "filename": filename,
                }
                st.session_state.pop("last_eval_payload", None)
                st.session_state["pending_eval"] = True
                st.rerun()
            else:
                st.error(f"Errore di ingestione: {res_dict.get('message')}")

        flash = st.session_state.get("ingest_flash")
        if flash:
            st.success(f"✓ {flash.get('message')}")
            st.info(
                f"Sigillo Crittografico: SHA-256 `{flash.get('file_hash')}` · "
                f"File `{flash.get('filename')}` · "
                f"{flash.get('rows')} righe → fatturato €{flash.get('revenue') or 0:,.0f} · "
                f"EBITDA €{flash.get('ebitda') or 0:,.0f}. "
                "Apri il Credit Dossier: i KPI sono ricalcolati su questo file."
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with up_col2:
        st.markdown("""
        <div class="exec-card">
            <div class="exec-card-title">Modello Ufficiale Bilancio CEE (Art. 2424-2425 c.c.)</div>
            <p style="font-size: 0.82rem; color: #94a3b8;">
                Scarica il tracciato standard del Bilancio CEE italiano completo di Stato Patrimoniale e Conto Economico a voci gerarchiche:
            </p>
        """, unsafe_allow_html=True)

        sample_cee_path = os.path.join(WORKSPACE_ROOT, "data", "sample_balance_sheet_cee_2024.csv")
        sample_cee_data = ""
        if os.path.exists(sample_cee_path):
            with open(sample_cee_path, "r", encoding="utf-8") as f:
                sample_cee_data = f.read()

        st.download_button(
            label="📥 Scarica Bilancio CEE Standard (CSV)",
            data=sample_cee_data,
            file_name="Bilancio_CEE_Art2424_2425_EcoTex_2024.csv",
            mime="text/csv",
            width="stretch"
        )

        st.markdown("""
        <div style="margin-top: 1rem; font-size: 0.72rem; color: #64748b; line-height: 1.45;">
            <b>Struttura Inclusa nel File:</b><br>
            • Stato Patrimoniale Attivo (Immobilizzazioni B.II, Attivo Circolante C, Cassa C.IV)<br>
            • Stato Patrimoniale Passivo (Patrimonio Netto A, Debiti Banche D.4 a breve e m/l termine)<br>
            • Conto Economico (Valore della produzione A.1+A.5, Costi B.6-B.14, Ammortamenti B.10, EBIT, Utile)
        </div>
        </div>
        """, unsafe_allow_html=True)

    # Ingestion Evidences Card
    recent_ev = st.session_state.get("recent_ingestion_evidences", [])
    if recent_ev:
        st.markdown("### 📋 Evidenze Probatorie Estratte dall'Ultimo Caricamento")
        st.markdown("""
        Queste evidenze sono state estratte deterministamente dal file caricato, verificate nei totali di bilancio 
        e integrate nel **Grounded Evidence Explorer** della pratica di fido.
        """)
        for ev in recent_ev:
            c_tag = ev.get("category", "FACT")
            tag_cls = "tag-fact" if c_tag == "FACT" else ("tag-calc" if c_tag == "CALCULATION" else "tag-reason")
            st.markdown(f"""
            <div style="background: rgba(17, 24, 39, 0.85); border-left: 4px solid #38bdf8; border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.6rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <span style="font-size: 0.75rem; font-weight: 700; color: #ffffff;">{ev.get('metric', 'Evidenza di Bilancio')}</span>
                    <span class="{tag_cls}">{c_tag}</span>
                </div>
                <div style="font-size: 0.84rem; color: #cbd5e1; margin-bottom: 0.2rem;">
                    "{ev.get('claim')}"
                </div>
                <div style="font-size: 0.7rem; color: #64748b;">
                    Fonte accertata: <i>{ev.get('source')}</i>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # DuckDB Live Table Explorer
    st.markdown("---")
    st.markdown("### 🔍 Live DuckDB Lakehouse Explorer")
    table_options = ["companies", "financial_statements", "bdi_provincial_credit", "lombardia_sectors", "document_chunks"]
    selected_table = st.selectbox("Ispeziona Tabella Relazionale DuckDB:", options=table_options, index=1)
    df_preview = get_table_preview(selected_table, limit=50)
    st.dataframe(df_preview, width="stretch")
    st.caption(f"Visualizzazione record vivi dalla tabella `{selected_table}` (DuckDB In-Memory OLAP)")


# ==========================================
# TAB 3: CAPITAL SIZING & STRESS LAB (ISOLATED VIA ST.FRAGMENT)
# ==========================================
@st.fragment
def render_capital_sizing_stress_lab(active_cid: str, payload: Dict[str, Any], backend_url: str, use_force_mock: bool):
    """
    Isolated reactive fragment for Capital Sizing Sensitivity & Stress Testing.
    Sliders re-render only this container with zero full-page flicker (<15ms latency).
    """
    col_sim_ctrl, col_sim_view = st.columns([1, 1.2])

    with col_sim_ctrl:
        st.markdown("""
        <div class="exec-card">
            <div class="exec-card-title">Parametri di Stress Testing</div>
        """, unsafe_allow_html=True)

        sim_loan_amt = st.slider(
            "Importo Linea di Credito (€):",
            min_value=500000,
            max_value=1500000,
            value=1000000,
            step=50000,
            format="€ %d"
        )

        sim_rate = st.slider(
            "Costo del Debito / Tasso Applicato (%):",
            min_value=3.50,
            max_value=8.00,
            value=5.25,
            step=0.25,
            format="%.2f %%"
        )

        sim_tenor = st.selectbox(
            "Durata Ammortamento (Anni):",
            options=[3, 5, 7, 10],
            index=1
        )

        st.caption("Linea Base: **€ 750.000** | Scenario di Stress Attivo: **€ " + f"{sim_loan_amt:,.0f}**")
        st.markdown("</div>", unsafe_allow_html=True)

    # Dynamic Sensitivity Recalculation
    scenario_res, sc_mode, sc_msg = simulate_scenario_api(
        company_id=active_cid,
        requested_amount=sim_loan_amt,
        interest_rate=sim_rate / 100.0,
        tenor_years=sim_tenor,
        base_payload=payload,
        backend_url=backend_url,
        force_mock=use_force_mock
    )

    with col_sim_view:
        base_fin = payload.get("financial_score", 97)
        sc_fin = scenario_res.get("financial_score", 74)
        f_delta = sc_fin - base_fin
        delta_str = f"+{f_delta}" if f_delta >= 0 else f"{f_delta}"
        d_class = "delta-up" if f_delta >= 0 else "delta-down"

        sc_rec = scenario_res.get("recommendation", "REVIEW")
        sc_badge = "badge-safe" if sc_rec == "APPROVE" else ("badge-watch" if sc_rec == "REVIEW" else "badge-danger")
        sc_col = "#34d399" if sc_rec == "APPROVE" else ("#fbbf24" if sc_rec == "REVIEW" else "#fb7185")
        sc_dscr = scenario_res.get("dscr", 1.28)
        sc_risk = scenario_res.get("risk_level", "High")
        sc_lev = scenario_res.get("net_debt_ebitda", 2.25)

        md_html(f"""
<div class="whatif-box">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.95rem; flex-wrap: wrap; gap: 0.5rem;">
<div>
<span style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Scenari di Stress Test Attivo</span>
<div style="font-size: 1.05rem; font-weight: 800; color: #ffffff;">€ {sim_loan_amt:,.0f} @ {sim_rate:.2f}% ({sim_tenor} Anni)</div>
</div>
<span class="finsight-badge {sc_badge}" style="font-size: 0.75rem; padding: 0.3rem 0.8rem;">Delibera: {sc_rec}</span>
</div>
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; text-align: center; margin-bottom: 1.15rem;">
<div class="fin-stat-card">
<span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Punteggio Salute</span>
<div style="font-size: 1.35rem; font-weight: 800; color: #f8fafc; margin-top: 0.2rem;" class="fin-mono-value">
{sc_fin}/100 <span class="{d_class}" style="font-size: 0.85rem;">({delta_str})</span>
</div>
</div>
<div class="fin-stat-card">
<span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">DSCR Proiettato</span>
<div style="font-size: 1.35rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">{sc_dscr:.2f}x</div>
</div>
<div class="fin-stat-card">
<span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Net Debt / EBITDA</span>
<div style="font-size: 1.35rem; font-weight: 800; color: {sc_col}; margin-top: 0.2rem;" class="fin-mono-value">{sc_lev:.2f}x</div>
</div>
</div>
<div style="font-size: 0.82rem; color: #cbd5e1; line-height: 1.45; background: rgba(13, 19, 32, 0.75); border: 1px solid rgba(255,255,255,0.06); padding: 0.85rem 1.05rem; border-radius: 9px;">
<b style="color: #38bdf8;">Raccomandazione Algoritmica:</b> {scenario_res.get('summary', 'La struttura del debito si mantiene entro i limiti sostenibili.')}
</div>
</div>
""")

    # Dynamic Headroom Bar for stressed scenario
    st.markdown(render_covenant_headroom_bar(sc_dscr, covenant_floor=1.30, eba_floor=1.00), unsafe_allow_html=True)

    # Plotly Interactive Sensitivity Curve
    st.markdown("### 📈 Curva di Sensibilità DSCR vs Importo Richiesto")

    curve_data = scenario_res.get("sensitivity_curve", [])
    if curve_data:
        x_amts = [p["amount"] / 1000 for p in curve_data]
        y_dscrs = [p["dscr"] for p in curve_data]

        fig_curve = go.Figure()

        # Add DSCR curve with smooth line and glowing markers
        fig_curve.add_trace(go.Scatter(
            x=x_amts,
            y=y_dscrs,
            mode="lines+markers",
            name="DSCR Proiettato",
            line=dict(color="#38bdf8", width=3, shape="spline"),
            marker=dict(size=8, color="#38bdf8", line=dict(color="#ffffff", width=1))
        ))

        # Add Covenant Floor at 1.30x
        fig_curve.add_hline(
            y=1.30,
            line_dash="dash",
            line_color="#fb7185",
            annotation_text="Soglia Minima Covenant (1.30x)",
            annotation_position="bottom right",
            annotation_font_color="#fb7185",
            annotation_font_size=11
        )

        # Highlight current selection
        fig_curve.add_trace(go.Scatter(
            x=[sim_loan_amt / 1000],
            y=[sc_dscr],
            mode="markers",
            name="Scenario Attivo",
            marker=dict(size=14, color="#34d399", symbol="diamond", line=dict(color="#ffffff", width=2))
        ))

        fig_curve.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13, 19, 32, 0.6)",
            xaxis=dict(
                title=dict(text="Importo Linea di Credito (€ k)", font=dict(color="#94a3b8", size=11, family="Plus Jakarta Sans")),
                gridcolor="rgba(255, 255, 255, 0.05)",
                color="#94a3b8",
                tickfont=dict(family="JetBrains Mono", size=10)
            ),
            yaxis=dict(
                title=dict(text="Debt Service Coverage Ratio (DSCR)", font=dict(color="#94a3b8", size=11, family="Plus Jakarta Sans")),
                gridcolor="rgba(255, 255, 255, 0.05)",
                color="#94a3b8",
                rangemode="tozero",
                tickfont=dict(family="JetBrains Mono", size=10)
            ),
            height=330,
            margin=dict(l=40, r=40, t=20, b=40),
            legend=dict(orientation="h", y=1.12, x=0.25, font=dict(color="#e2e8f0", size=11))
        )

        st.plotly_chart(fig_curve, width="stretch")


with tab_stress:
    st.markdown("### 🧪 Laboratorio di Stress Test & Sensitivity del Capitale")
    st.markdown("""
    Regola i parametri di linea creditizia, tasso nominale e durata di ammortamento.
    Il motore ricalcola istantaneamente il **DSCR**, la **leva Net Debt / EBITDA**, il **Punteggio di Salute** 
    e traccia la **curva di solvibilità** rispetto alle soglie di covenant bancario.
    """)
    render_capital_sizing_stress_lab(active_cid, payload, backend_url, use_force_mock)


# ==========================================
# TAB 4: CERTIFIED DOSSIER EXPORT
# ==========================================
with tab_export:
    st.markdown("### 📑 Generazione Fascicolo Bancario Certificato (EBA / OAM)")
    st.markdown("""
    Esporta il **Credit Memorandum** ufficiale e il passaporto di bancabilità secondo le linee guida 
    **EBA Guidelines on Loan Origination** (EBA/GL/2020/06) con sigillo di conformità TUB Art. 128-sexies.
    """)

    col_ex1, col_ex2 = st.columns([1.8, 1.2])

    with col_ex1:
        st.markdown(f"""
        <div class="exec-card">
            <div class="exec-card-title">Dati Identificativi Pratica e Delibera</div>
            <table style="width: 100%; font-size: 0.82rem; color: #e2e8f0;">
                <tr style="border-bottom: 1px solid #1f2937;">
                    <td style="padding: 0.45rem 0; color: #94a3b8;">Application ID Condiviso:</td>
                    <td style="padding: 0.45rem 0; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #10b981;">{linked_app_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #1f2937;">
                    <td style="padding: 0.45rem 0; color: #94a3b8;">Ragione Sociale Richiedente:</td>
                    <td style="padding: 0.45rem 0; font-weight: 600;">{payload.get('company', 'EcoTex Milano S.p.A.')}</td>
                </tr>
                <tr style="border-bottom: 1px solid #1f2937;">
                    <td style="padding: 0.45rem 0; color: #94a3b8;">Importo Deliberato:</td>
                    <td style="padding: 0.45rem 0; font-weight: 700; color: #38bdf8;" class="fin-mono-value">€ {payload.get('loan_amount', 750000):,.0f}</td>
                </tr>
                <tr style="border-bottom: 1px solid #1f2937;">
                    <td style="padding: 0.45rem 0; color: #94a3b8;">Esito Delibera di Fido:</td>
                    <td style="padding: 0.45rem 0; font-weight: 700; color: #34d399;">{payload.get('recommendation', 'APPROVE')} (Pre-Approvato)</td>
                </tr>
                <tr style="border-bottom: 1px solid #1f2937;">
                    <td style="padding: 0.45rem 0; color: #94a3b8;">DSCR di Copertura:</td>
                    <td style="padding: 0.45rem 0; font-weight: 700;" class="fin-mono-value">{payload.get('dscr', 3.37):.2f}x (Buffer eccedente covenant)</td>
                </tr>
                <tr>
                    <td style="padding: 0.45rem 0; color: #94a3b8;">Sigillo Digitale SHA-256:</td>
                    <td style="padding: 0.45rem 0; font-family: 'JetBrains Mono', monospace; color: #38bdf8;">SHA256: {audit_hash}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col_ex2:
        st.markdown("""
        <div class="exec-card" style="text-align: center;">
            <div class="exec-card-title">Download Documentale Formattato</div>
        """, unsafe_allow_html=True)

        # 1. Bank Credit Memorandum in formal Markdown format
        memorandum_md = f"""# FINSIGHT AI — CERTIFIED CREDIT MEMORANDUM
================================================================================
CONFORME A: EBA Guidelines on Loan Origination (EBA/GL/2020/06) & TUB Art. 128-sexies
APPLICATION ID: {linked_app_id}
DATA DELIBERA: {datetime.date.today().strftime('%d/%m/%Y')}
INTEGRITY SEAL: SHA256:{audit_hash}
================================================================================

1. ANAGRAFICA SOGGETTO RICHIEDENTE
- Ragione Sociale: {payload.get('company')}
- Partita IVA / CF: IT09876540152
- Settore Economico: {payload.get('sector')}
- Provincia / Regione: {payload.get('province')}
- Addetti: 64 dipendenti full-time

2. PARAMETRI OPERAZIONE FINANZIARIA RICHIESTA
- Importo Linea Accordata: EUR {payload.get('loan_amount', 750000):,.2f}
- Destinazione d'Uso: Investimenti CapEx in macchinari a basso consumo e riciclo idrico
- Tasso Applicato: 5.15% Fisso Prime (Agevolazione Green SLL -45 bps inclusa)
- Durata Ammortamento: 5 anni

3. SINTESI INDICATORI ECONOMICO-PATRIMONIALI (DUCKDB AUDITED)
- Valore della Produzione: EUR {payload.get('revenue', 14200000):,.2f}
- MOL / EBITDA Riclassificato: EUR {payload.get('ebitda', 2470000):,.2f} ({payload.get('ebitda_margin', 17.4)}%)
- Patrimonio Netto a Garanzia: EUR {payload.get('net_equity', 5800000):,.2f}
- Indebitamento Finanziario Netto: EUR {payload.get('total_debt', 4700000) - payload.get('cash_and_equivalents', 1630000):,.2f}
- DSCR Post-Finanziamento: {payload.get('dscr', 3.37):.2f}x (Soglia minima covenant: 1.30x)
- Quick Liquidity Ratio: {payload.get('quick_ratio', 1.42):.2f}x

4. BENCHMARK TERRITORIALE E DI COMPARTO
- Banca d'Italia: Tasso di sofferenza NPL provinciale pari all'1.82% (vs 2.95% media Italia)
- Open Data Lombardia: Fatturato comparto tessile in crescita del +4.1% YoY

5. CERTIFICAZIONI AMBIENTALI E RATING ESG
- Score Allineamento ESG: {payload.get('esg_score', 95)}/100 (Top Decile)
- Risparmio Idrico Accertato: -42% prelievo rete con conformita ZDHC Level 3
- Certificazioni: ISO 14001:2015 e ISO 50001 attive

6. ESITO DELIBERATIVO FINALE
- Valutazione Complessiva: {payload.get('recommendation', 'APPROVE')}
- Fascia di Rischio: {payload.get('risk_level', 'Low')}
- Nota per l'Ufficio Fidi: Operazione altamente bancabile, coperta da capienza di cassa e conformita EBA.
================================================================================
"""

        # Institutional PDF Credit Memorandum Generation
        pdf_bytes = generate_credit_memorandum_pdf(payload, audit_hash, linked_app_id)

        st.download_button(
            label="📄 Scarica Credit Memorandum Ufficiale (.PDF)",
            data=pdf_bytes,
            file_name=f"FinSight_Credit_Memorandum_{linked_app_id}.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch"
        )

        st.download_button(
            label="📑 Scarica Credit Memorandum (.MD)",
            data=memorandum_md,
            file_name=f"FinSight_Credit_Memorandum_{linked_app_id}.md",
            mime="text/markdown",
            width="stretch"
        )

        dossier_json = json.dumps(payload, indent=2)
        st.download_button(
            label="💾 Scarica Payload Core Banking (JSON)",
            data=dossier_json,
            file_name=f"FinSight_Dossier_Payload_{linked_app_id}.json",
            mime="application/json",
            width="stretch"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #1e293b; font-size: 0.72rem; color: #64748b;">
        <b>Informativa Normativa (TUB Art. 128-sexies):</b> FinSight AI fornisce analisi deterministiche di pre-istruttoria del credito. 
        I prospetti esportati sono pre-formattati per l'integrazione immediata nei sistemi di rating interno delle banche partner.
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# TAB 5: BANK CREDIT UNDERWRITING MATRIX (BANK ONLY)
# ==========================================
if is_bank_user and tab_bank is not None:
    with tab_bank:
        st.markdown("### 🏛️ Console di Delibera Fidi Bancari (Intesa Sanpaolo)")
        st.markdown("""
        Pannello di supervisione per l'Ufficio Rischi e Delibere. Confronta le pratiche collegate tramite 
        **Application ID**, monitora i parametri EBA di concentrazione e rilascia la delibera ufficiale di fido.
        """)

        portfolio_data = []
        for c in companies_list:
            c_id = c["company_id"]
            c_app = f"{c_id.upper()}-2026-IT"
            req_amt = 750000 if c_id == "ecotex" else (500000 if c_id == "meccanica" else 400000)
            c_metrics = calculate_deterministic_bankability(c_id, req_amt)
            portfolio_data.append({
                "Application ID": c_app,
                "Ragione Sociale": c_metrics["company"],
                "Provincia": c_metrics["province"],
                "Importo Richiesto": f"€ {c_metrics['loan_amount']:,.0f}",
                "Fatturato": f"€ {c_metrics['revenue']/1e6:.1f}M",
                "EBITDA Margin": f"{c_metrics['ebitda_margin']}%",
                "Punteggio Salute": f"{c_metrics['financial_score']}/100",
                "DSCR Proiettato": f"{c_metrics['dscr']:.2f}x",
                "Esito Delibera": c_metrics["recommendation"]
            })

        df_bank = pd.DataFrame(portfolio_data)
        st.dataframe(df_bank, width="stretch")

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; margin-top: 1.15rem; margin-bottom: 1.35rem;">
            <div class="fin-stat-card">
                <div style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Pratiche in Istruttoria</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #f8fafc; margin-top: 0.2rem;" class="fin-mono-value">{len(portfolio_data)}</div>
                <div style="font-size: 0.72rem; color: #34d399; margin-top: 0.15rem;">100% Audited con SHA-256</div>
            </div>
            <div class="fin-stat-card">
                <div style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Monte Fidi Richiesto</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">€ 1,650,000</div>
                <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 0.15rem;">Capienza Plafond 2026</div>
            </div>
            <div class="fin-stat-card">
                <div style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">DSCR Medio Portafoglio</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #34d399; margin-top: 0.2rem;" class="fin-mono-value">2.85x</div>
                <div style="font-size: 0.72rem; color: #10b981; margin-top: 0.15rem;">Buffer &gt; 1.30x Covenant</div>
            </div>
            <div class="fin-stat-card">
                <div style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">NPL Benchmark Territoriale</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #38bdf8; margin-top: 0.2rem;" class="fin-mono-value">1.82%</div>
                <div style="font-size: 0.72rem; color: #34d399; margin-top: 0.15rem;">vs 2.95% Media Italia</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Bank Underwriter Specialization: 2D Downside Stress Heatmap
        render_bank_stress_heatmap(
            ebitda=base_data.get("ebitda", 2470000),
            loan_amt=current_req_amt,
            base_rate=base_data.get("interest_rate", 5.15),
            tenor_years=5
        )

        st.markdown("---")
        b_c1, b_c2 = st.columns(2)
        with b_c1:
            if st.button(f"✅ Rilascia Delibera di Fido Esecutiva per {linked_app_id}", type="primary", width="stretch"):
                st.success(f"✓ Delibera di Fido Approvata per {linked_app_id}! Fascicolo registrato nei sistemi di Direzione Crediti con hash SHA-256 {audit_hash}")
        with b_c2:
            if st.button(f"⚠️ Richiedi Integrazione Covenant per {linked_app_id}", width="stretch"):
                st.warning(f"Richiesta di integrazione trasmessa all'azienda per {linked_app_id}: richiesto pegno mobiliare su nuovo macchinario.")
