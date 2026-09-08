# Start FinSight AI Streamlit UI (team dashboard)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
.\.venv\Scripts\streamlit run app/main.py
