#!/usr/bin/env bash
# (Re)seed the DEMO database from scratch.
set -euo pipefail
cd "$(dirname "$0")/../backend"
. .venv/bin/activate
rm -f spark.db
python -m app.db.seed
