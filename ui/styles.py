"""Streamlit UI styles."""

CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a5f;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .recommendation-approve {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
        padding: 1rem 2rem;
        border-radius: 12px;
        font-size: 1.5rem;
        font-weight: 700;
        text-align: center;
        margin: 1rem 0;
    }
    .recommendation-review {
        background: linear-gradient(135deg, #d97706, #f59e0b);
        color: white;
        padding: 1rem 2rem;
        border-radius: 12px;
        font-size: 1.5rem;
        font-weight: 700;
        text-align: center;
        margin: 1rem 0;
    }
    .recommendation-decline {
        background: linear-gradient(135deg, #dc2626, #ef4444);
        color: white;
        padding: 1rem 2rem;
        border-radius: 12px;
        font-size: 1.5rem;
        font-weight: 700;
        text-align: center;
        margin: 1rem 0;
    }
    .trace-step {
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-left: 3px solid #10b981;
        background: #f0fdf4;
        border-radius: 0 8px 8px 0;
    }
    .disclaimer {
        font-size: 0.75rem;
        color: #94a3b8;
        border-top: 1px solid #e2e8f0;
        padding-top: 1rem;
        margin-top: 2rem;
    }
    .app-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
</style>
"""
