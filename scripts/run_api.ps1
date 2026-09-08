# Start FinSight AI API
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
.\.venv\Scripts\uvicorn backend.main:app --reload --port 8000
