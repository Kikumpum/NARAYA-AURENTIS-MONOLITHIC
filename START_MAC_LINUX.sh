#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
echo "DEMO ONLY - NO REAL PATIENT OR PAYMENT DATA"
echo "Open http://127.0.0.1:8000"
exec python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
