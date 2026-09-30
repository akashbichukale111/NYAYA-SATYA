# Tests

The primary backend test suite lives in `backend/tests/` (run via
`scripts/test.sh` or `cd backend && pytest tests/`) since it needs to import
the FastAPI app.

This top-level `tests/` directory holds `test_safety_boundary.py`, a small
symlink-free copy-through test that exercises the safety boundary described
in `docs/SAFETY.md` end-to-end via the same `TestClient` approach, kept
separate so it's easy to point CI's "safety" job at just this file.

Run it the same way:

```bash
cd backend && . .venv/bin/activate && pytest ../tests/test_safety_boundary.py -q
```
