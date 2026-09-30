#!/usr/bin/env bash
# Runs the backend (FastAPI/uvicorn) and serves the frontend as static files.
# Usage: ./scripts/run.sh
set -e
cd "$(dirname "$0")/.."

echo "Installing backend dependencies..."
pip install -r backend/requirements.txt --quiet

echo "Starting backend on http://127.0.0.1:8000 ..."
(cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

echo "Serving frontend on http://127.0.0.1:5173 ..."
(cd frontend && python3 -m http.server 5173) &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://127.0.0.1:8000  (docs at /docs)"
echo "Frontend: http://127.0.0.1:5173"
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
