# DEMO Mode

DEMO mode is the default (`DEMO_MODE=true`). It runs entirely on SQLite with
**zero external API keys** and seeds clearly-labeled fictional data — no real
case data is ever used outside DEMO mode.

## Running the demo

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # source .venv/bin/activate on bash
pip install -r requirements.txt
python -m app.db.seed        # creates spark.db and seeds demo users/cases
uvicorn app.main:app --reload
```

Or via Docker:

```bash
docker compose up
```

## Demo accounts

All demo accounts use the password `DemoPass123!`:

| Email | Role |
|---|---|
| demo.advocate@example.com | advocate |
| demo.legalaid@example.com | legal_aid |
| demo.admin@example.com | admin |

## What's seeded

The seed script (`backend/app/db/seed.py`) creates demo users, a workspace,
a handful of fictional cases with case memberships, sample attention items,
tasks (including a blocked task with a dependency), deadlines with a mix of
`SOURCE_STATED`/`SYSTEM_DERIVED`/`UNKNOWN` date sources, a pending review, a
pending approval request, and DEMO-labeled stub `EngineConnection` rows for
every upstream engine (Evidence Dependency, Procedural Obligation, Case
Continuity, Case Bottleneck, Hearing Readiness, Legal-Aid Handoff, Registry
Defect, Undertrial Liberty Sentinel, Deadline Guardian, Workflow Autopilot).
These stubs are explicitly marked `status="demo_stub"` — they are not live
integrations, and the UI/API must never present them as such.
