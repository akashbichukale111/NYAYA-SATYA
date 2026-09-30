#!/usr/bin/env bash
# Run the backend dev server (DEMO mode, auto-seeds if db is missing).
set -euo pipefail
cd "$(dirname "$0")/../backend"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f spark.db ]; then
  python -m app.db.seed
fi

uvicorn app.main:app --reload --port 8000
