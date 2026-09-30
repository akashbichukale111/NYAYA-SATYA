#!/usr/bin/env bash
# Sets up backend + frontend from a clean checkout.
set -e
cd "$(dirname "$0")/.."

echo "==> Installing backend dependencies"
cd backend
pip install -r requirements.txt --break-system-packages
cd ..

echo "==> Installing frontend dependencies"
cd frontend
npm install
cd ..

echo "==> Setup complete. Next: ./scripts/seed_demo.sh then ./scripts/run_backend.sh"
