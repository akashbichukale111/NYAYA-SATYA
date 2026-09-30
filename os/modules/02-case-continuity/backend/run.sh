#!/usr/bin/env bash
# Runs the Case Continuity Engine API + frontend as a single process.
# The frontend (../frontend) is served as static files by FastAPI itself,
# so opening http://localhost:8000 gives you the whole product.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f ".env" ] && [ -f "../.env.example" ]; then
  echo "No .env found - copying .env.example. Edit it to set LLM_PROVIDER/LLM_API_KEY if desired."
  cp ../.env.example .env
fi

export $(grep -v '^#' .env 2>/dev/null | xargs -d '\n' || true) 2>/dev/null || true

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
