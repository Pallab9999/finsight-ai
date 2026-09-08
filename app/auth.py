"""
FinSight AI - Enterprise Authentication & Multi-Tenant Session Management
=========================================================================
Implements role-based access control (RBAC) separating SME CFOs from Corporate Accounting Advisory Firms.
Includes 1-click quick-evaluation demo credentials to facilitate frictionless executive testing.
"""

import hashlib
from typing import Dict, Any, Optional, Tuple
import streamlit as st

# Verified Enterprise Demo Users
ENTERPRISE_USERS = {
    "cfo@ecotex.it": {
        "email": "cfo@ecotex.it",
        "password_hash": hashlib.sha256("cfo2026".encode("utf-8")).hexdigest(),
        "role": "sme_cfo",
        "role_label": "SME CFO",
        "name": "Marco Valenti",
        "organization": "EcoTex Milano S.p.A.",
        "default_company_id": "ecotex",
        "allowed_companies": ["ecotex"]
    },
    "partner@studiocolombo.it": {
        "email": "partner@studiocolombo.it",
        "password_hash": hashlib.sha256("advisor2026".encode("utf-8")).hexdigest(),
        "role": "accounting_advisor",
        "role_label": "Accounting Advisor (Commercialista)",
        "name": "Dott. Andrea Colombo",
        "organization": "Studio Colombo & Associati (Milano)",
        "default_company_id": "ecotex",
        "allowed_companies": ["ecotex", "meccanica", "agrobio"]
    }
}


def verify_credentials(email: str, password: str, expected_role: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Verifies user credentials.
    Returns (user_profile, status_message).
    """
    email_clean = email.strip().lower()
    if email_clean not in ENTERPRISE_USERS:
        return None, "Invalid user email. Please use standard demo credentials."

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
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = "sme_cfo"
    if "user_role_label" not in st.session_state:
        st.session_state["user_role_label"] = "SME CFO"
    if "organization" not in st.session_state:
        st.session_state["organization"] = None
    if "active_company_id" not in st.session_state:
        st.session_state["active_company_id"] = "ecotex"
    if "allowed_companies" not in st.session_state:
        st.session_state["allowed_companies"] = ["ecotex"]
    if "auth_token" not in st.session_state:
        st.session_state["auth_token"] = None


def login_user(user: Dict[str, Any]):
    """
    Persists authenticated user profile into session state.
    """
    token_raw = f"{user['email']}:{user['role']}:finsight_enterprise_2026"
    token = hashlib.sha256(token_raw.encode("utf-8")).hexdigest()

    st.session_state["authenticated"] = True
    st.session_state["user_email"] = user["email"]
    st.session_state["user_name"] = user["name"]
    st.session_state["user_role"] = user["role"]
    st.session_state["user_role_label"] = user["role_label"]
    st.session_state["organization"] = user["organization"]
    st.session_state["active_company_id"] = user["default_company_id"]
    st.session_state["allowed_companies"] = user["allowed_companies"]
    st.session_state["auth_token"] = token


def logout_user():
    """
    Clears session state on logout.
    """
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None
    st.session_state["user_name"] = None
    st.session_state["user_role"] = "sme_cfo"
    st.session_state["user_role_label"] = "SME CFO"
    st.session_state["organization"] = None
    st.session_state["active_company_id"] = "ecotex"
    st.session_state["allowed_companies"] = ["ecotex"]
    st.session_state["auth_token"] = None
