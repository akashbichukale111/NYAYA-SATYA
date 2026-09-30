#!/usr/bin/env bash
# Run the backend test suite.
set -euo pipefail
cd "$(dirname "$0")/../backend"
. .venv/bin/activate
pip install -q -r requirements.txt
python -m pytest tests/ -q "$@"
