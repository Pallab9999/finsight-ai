"""Reusable Streamlit components."""

import streamlit as st


def render_header() -> None:
    st.markdown('<p class="main-header">FinSight AI</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Financial Intelligence & Decision Engine</p>',
        unsafe_allow_html=True,
    )


def render_application_card(company: str, sector: str, province: str, loan: int, purpose: str) -> None:
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.metric("Company", company)
    col2.metric("Sector", sector)
    col3.metric("Province", province)
    col4, col5 = st.columns(2)
    col4.metric("Requested Financing", f"€{loan:,}")
    col5.metric("Purpose", purpose[:40] + ("..." if len(purpose) > 40 else ""))
    st.markdown("</div>", unsafe_allow_html=True)


def render_kpi_row(financial_score: int, esg_score: int, risk_level: str) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Financial Health", f"{financial_score}/100")
    col2.metric("ESG Alignment", f"{esg_score}/100")
    col3.metric("Risk Level", risk_level)


def render_recommendation(recommendation: str) -> None:
    css_class = {
        "APPROVE": "recommendation-approve",
        "REVIEW": "recommendation-review",
        "DECLINE": "recommendation-decline",
    }.get(recommendation, "recommendation-review")
    st.markdown(
        f'<div class="{css_class}">{recommendation}</div>',
        unsafe_allow_html=True,
    )


def render_audit_trail(steps: list[str]) -> None:
    st.subheader("AI Decision Trace")
    for step in steps:
        st.markdown(f'<div class="trace-step">✓ {step}</div>', unsafe_allow_html=True)


def render_drivers(drivers: list[str]) -> None:
    st.subheader("Why?")
    for driver in drivers:
        st.markdown(f"- {driver}")


def render_evidence(evidence: list[dict]) -> None:
    st.subheader("Evidence")
    for item in evidence:
        with st.expander(item.get("source", "Source")):
            st.write(item.get("claim", ""))


def render_scenario_comparison(base: dict, scenario: dict) -> None:
    st.subheader("What-if Scenario")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Current**")
        st.write(f"Loan: €{base.get('loan_amount', 0):,}")
        st.write(f"Financial Score: {base.get('financial_score', 0)}")
        st.write(f"Risk: {base.get('risk_level', 'N/A')}")
        st.write(f"Recommendation: {base.get('recommendation', 'N/A')}")
    with col2:
        st.markdown("**Scenario**")
        st.write(f"Loan: €{scenario.get('loan_amount', 0):,}")
        st.write(f"Financial Score: {scenario.get('financial_score', 0)}")
        st.write(f"Risk: {scenario.get('risk_level', 'N/A')}")
        st.write(f"Recommendation: {scenario.get('recommendation', 'N/A')}")


def render_disclaimer() -> None:
    st.markdown(
        '<p class="disclaimer">'
        "FinSight is an AI-assisted financial decision-support prototype. "
        "It provides evidence-backed analytics and scenario analysis for human review. "
        "It does not provide regulated financial advice, represent an official credit rating, "
        "or replace a bank's formal underwriting and compliance process."
        "</p>",
        unsafe_allow_html=True,
    )
