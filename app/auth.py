"""
FinSight AI - Enterprise Authentication & Multi-Tenant Session Management
=========================================================================
Implements dual-entity authentication linking SME Borrowers and Bank Credit Underwriters
through a shared unique Application Identifier (e.g. ECOTEX-2026-IT).
"""

import hashlib
from typing import Dict, Any, Optional, Tuple, List
import streamlit as st

# Verified Enterprise Demo Users (Linked by Application ID)
ENTERPRISE_USERS = {
    "cfo@ecotex.it": {
        "email": "cfo@ecotex.it",
        "password_hash": hashlib.sha256("cfo2026".encode("utf-8")).hexdigest(),
        "role": "sme_borrower",
        "role_label": "SME Borrower (CFO)",
        "name": "Marco Valenti",
        "title": "Chief Financial Officer",
        "organization": "EcoTex Milano S.p.A.",
        "linked_id": "ECOTEX-2026-IT",
        "default_company_id": "ecotex",
        "allowed_companies": ["ecotex"]
    },
    "underwriter@intesabancapmi.it": {
        "email": "underwriter@intesabancapmi.it",
        "password_hash": hashlib.sha256("bank2026".encode("utf-8")).hexdigest(),
        "role": "bank_officer",
        "role_label": "Bank Credit Officer (Underwriter)",
        "name": "Dott.ssa Giulia Bernardi",
        "title": "Senior Corporate Credit Underwriter",
        "organization": "Intesa Sanpaolo — Direzione Crediti Corporate PMI",
        "linked_id": "ECOTEX-2026-IT",
        "default_company_id": "ecotex",
        "allowed_companies": ["ecotex", "meccanica", "agrobio"],
        "available_applications": [
            {"app_id": "ECOTEX-2026-IT", "company_id": "ecotex", "borrower": "EcoTex Milano S.p.A.", "amount": 750000, "status": "READY_FOR_DELIBERA"},
            {"app_id": "MECCANICA-2026-IT", "company_id": "meccanica", "borrower": "Meccanica Precisione Varese S.r.l.", "amount": 500000, "status": "IN_REVIEW"},
            {"app_id": "AGROBIO-2026-IT", "company_id": "agrobio", "borrower": "AgroBio Brianza Soc. Coop.", "amount": 400000, "status": "READY_FOR_DELIBERA"}
        ]
    },
    # Backwards compatibility for advisor role
    "partner@studiocolombo.it": {
        "email": "partner@studiocolombo.it",
        "password_hash": hashlib.sha256("advisor2026".encode("utf-8")).hexdigest(),
        "role": "bank_officer",
        "role_label": "Corporate Accounting Advisor / Underwriter",
        "name": "Dott. Andrea Colombo",
        "title": "Managing Partner & Corporate Debt Advisor",
        "organization": "Studio Colombo & Associati (Milano)",
        "linked_id": "ECOTEX-2026-IT",
        "default_company_id": "ecotex",
        "allowed_companies": ["ecotex", "meccanica", "agrobio"],
        "available_applications": [
            {"app_id": "ECOTEX-2026-IT", "company_id": "ecotex", "borrower": "EcoTex Milano S.p.A.", "amount": 750000, "status": "READY_FOR_DELIBERA"},
            {"app_id": "MECCANICA-2026-IT", "company_id": "meccanica", "borrower": "Meccanica Precisione Varese S.r.l.", "amount": 500000, "status": "IN_REVIEW"},
            {"app_id": "AGROBIO-2026-IT", "company_id": "agrobio", "borrower": "AgroBio Brianza Soc. Coop.", "amount": 400000, "status": "READY_FOR_DELIBERA"}
        ]
    }
}


def verify_credentials(email: str, password: str, expected_role: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Verifies user credentials against enterprise demo dictionary.
    Returns (user_profile, status_message).
    """
    email_clean = email.strip().lower()
    if email_clean not in ENTERPRISE_USERS:
        return None, "Invalid user email. Use standard demo credentials."

    user = ENTERPRISE_USERS[email_clean]
    pwd_hash = hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

    if pwd_hash != user["password_hash"]:
        return None, "Invalid password. Hint: check demo credentials."

    if expected_role and user["role"] != expected_role:
        return None, f"Role mismatch: account is registered as '{user['role_label']}'."

    return user, "Authentication successful."


def init_session_state():
    """
    Initializes Streamlit session state keys for enterprise authentication.
    """
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None
    if "user_title" not in st.session_state:
        st.session_state["user_title"] = None
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = "sme_borrower"
    if "user_role_label" not in st.session_state:
        st.session_state["user_role_label"] = "SME Borrower (CFO)"
    if "organization" not in st.session_state:
        st.session_state["organization"] = None
    if "linked_id" not in st.session_state:
        st.session_state["linked_id"] = "ECOTEX-2026-IT"
    if "active_company_id" not in st.session_state:
        st.session_state["active_company_id"] = "ecotex"
    if "allowed_companies" not in st.session_state:
        st.session_state["allowed_companies"] = ["ecotex"]
    if "auth_token" not in st.session_state:
        st.session_state["auth_token"] = None
    if "recent_ingestion_evidences" not in st.session_state:
        st.session_state["recent_ingestion_evidences"] = []


def login_user(user: Dict[str, Any]):
    """
    Persists authenticated user profile into session state.
    """
    token_raw = f"{user['email']}:{user['role']}:{user.get('linked_id', 'ECOTEX-2026-IT')}"
    token = hashlib.sha256(token_raw.encode("utf-8")).hexdigest()

    st.session_state["authenticated"] = True
    st.session_state["user_email"] = user["email"]
    st.session_state["user_name"] = user["name"]
    st.session_state["user_title"] = user.get("title", "")
    st.session_state["user_role"] = user["role"]
    st.session_state["user_role_label"] = user["role_label"]
    st.session_state["organization"] = user["organization"]
    st.session_state["linked_id"] = user.get("linked_id", "ECOTEX-2026-IT")
    st.session_state["active_company_id"] = user.get("default_company_id", "ecotex")
    st.session_state["allowed_companies"] = user.get("allowed_companies", ["ecotex"])
    st.session_state["auth_token"] = token


def logout_user():
    """
    Clears session state on logout.
    """
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None
    st.session_state["user_name"] = None
    st.session_state["user_title"] = None
    st.session_state["user_role"] = "sme_borrower"
    st.session_state["user_role_label"] = "SME Borrower (CFO)"
    st.session_state["organization"] = None
    st.session_state["linked_id"] = "ECOTEX-2026-IT"
    st.session_state["active_company_id"] = "ecotex"
    st.session_state["allowed_companies"] = ["ecotex"]
    st.session_state["auth_token"] = None
    st.session_state["recent_ingestion_evidences"] = []
