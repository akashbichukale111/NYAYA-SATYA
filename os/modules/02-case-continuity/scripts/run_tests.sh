#!/usr/bin/env bash
# One reproducible command for the full test suite (section 51).
set -euo pipefail
cd "$(dirname "$0")/../backend"
python3 -m pip install -r requirements.txt --break-system-packages -q
python3 -m pytest -v
