#!/usr/bin/env bash
# Seeds the 8 synthetic demo cases (A-H) against a running instance.
# Usage: ./scripts/seed_demo.sh [base_url]
set -euo pipefail
BASE_URL="${1:-http://localhost:8000}"
curl -s -X POST "$BASE_URL/api/demo/seed" | python3 -m json.tool
