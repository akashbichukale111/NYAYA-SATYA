# Demo

`walkthrough.py` narrates the flagship demo flow against a **live, running
backend** — every line it prints comes from a real HTTP call, nothing is
canned. It implements the exact sequence required by the spec:

```
Open Demo Case → Inspect Custody Timeline → Open Source → Inspect Hearing
→ Detect Missing/Conflicting Event → Open Attention Center
→ Inspect Dependency → Run Crash Test → Review Result
→ Open Time Machine → Inspect Audit
```

## Run it

```bash
# terminal 1
cd backend
python -m app.db.seed_demo
uvicorn app.main:app --port 8000

# terminal 2
python demo/walkthrough.py --case A   # clean timeline
python demo/walkthrough.py --case B   # conflicting records (default)
python demo/walkthrough.py --case C   # missing event chain
```

For the automated, assertion-based version of this same flow (used in CI /
regression checking rather than for live narration), see
`tests/e2e_regression.py`.

See `docs/demo.md` for what each of the three seeded cases represents.
