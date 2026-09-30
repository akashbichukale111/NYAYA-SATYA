# Spark Personal OS

> One workspace for every case, every obligation, every alert, every decision,
> and every next safe action.

**Project 10** in the NYAYA-SATYA legal-tech system. Spark is the
human-facing operational workspace that aggregates output from upstream
specialized engines into one coherent command center — it is **not** a legal
reasoning authority, not a judge, and does not make legal decisions or
predict outcomes. See [`docs/SAFETY.md`](docs/SAFETY.md) for the enforced
safety boundary and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how
the system is built.

## Status

This repository is built across 4 sections, same repo throughout.

- [x] **Section 1** — repo scaffold, full domain model (28 entities), auth +
      server-side RBAC, LLMProvider abstraction (Mock/OpenAI/Anthropic/Groq),
      DEMO seed data, passing test suite.
- [ ] **Section 2** — Attention Engine lifecycle, Task dependencies, Deadline/
      tracked-date views, mock upstream `EngineEvent` adapters.
- [ ] **Section 3** — Reviews, Approvals, Recent Changes, Case Digest,
      Notifications with dedup, Saved Views, Pinned Cases.
- [ ] **Section 4** — Frontend workspace UI, Command Palette, Calendar,
      Global Search, explainability panels, final test/docs pass.

## Quickstart (DEMO mode — no API keys required)

```bash
git clone <this-repo>
cd spark-personal-os
cp .env.example backend/.env   # optional; defaults already work
./scripts/dev.sh               # installs deps, seeds DEMO data, runs the API
```

API will be live at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. Demo accounts are listed in
[`demo/README.md`](demo/README.md) (password `DemoPass123!` for all).

Or with Docker:

```bash
docker compose up
```

Run tests:

```bash
./scripts/test.sh
```

## Repository layout

```
spark-personal-os/
├── frontend/        React + TS + Vite + Tailwind (skeleton; full UI in Section 4)
├── backend/          FastAPI + SQLAlchemy + Pydantic, SQLite by default, Postgres-ready
├── demo/             DEMO mode notes and seeded account list
├── docs/             ARCHITECTURE.md, SAFETY.md
├── tests/            Cross-cutting safety-boundary regression tests
├── scripts/          dev.sh / seed.sh / test.sh convenience scripts
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
└── docker-compose.yml
```

## What this is not

Per the project's non-negotiable build rule, this is not a tutorial, a
dashboard mockup, a fake SaaS, a static frontend, or a system that makes
autonomous legal decisions. Every attention item, deadline, and change
carries real provenance (source engine, source entity, case ID, status,
timestamp) back to its origin, and every consequential action requires an
explicit human decision. DEMO mode uses clearly-labeled fictional case data
only; there is no real case data anywhere in this repository.
