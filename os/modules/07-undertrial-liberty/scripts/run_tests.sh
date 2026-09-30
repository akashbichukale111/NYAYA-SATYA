#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
echo "==> Backend tests"
python3 -m pytest tests/ -v
cd ../frontend
echo "==> Frontend build (acts as the frontend correctness check for this build)"
npm run build
