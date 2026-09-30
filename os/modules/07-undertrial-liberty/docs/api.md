# API Reference

Full interactive docs at `/docs` (Swagger UI) when the server is running.
Every endpoint from the master spec is implemented; verified by listing
FastAPI's route table directly during development. Auth: send
`X-Demo-Role` (one of `CITIZEN`/`LEGAL_AID`/`ADVOCATE`/`ADMIN`) and
`X-Demo-User` headers (see `docs/security.md`).

| Method | Path | Notes |
|---|---|---|
| POST | `/api/cases` | requires >= LEGAL_AID |
| GET | `/api/cases`, `/api/cases/{id}` | |
| POST | `/api/cases/{id}/documents` | multipart upload; triggers extraction pipeline |
| GET | `/api/cases/{id}/documents` | |
| GET | `/api/cases/{id}/custody`, `/timeline`, `/hearings`, `/orders`, `/bail-events`, `/release-events` | |
| GET | `/api/cases/{id}/digital-twin` | |
| GET | `/api/cases/{id}/attention` | |
| GET | `/api/cases/{id}/dependency-graph` | |
| GET | `/api/cases/{id}/conflicts` | |
| POST | `/api/conflicts/{id}/resolve` | requires >= ADVOCATE |
| GET/POST | `/api/cases/{id}/verification` | POST requires >= ADVOCATE |
| GET | `/api/cases/{id}/review-queue` | |
| POST | `/api/reviews/{id}/approve`, `/reject` | requires >= ADVOCATE |
| GET | `/api/cases/{id}/audit` | |
| GET | `/api/cases/{id}/time-machine` | optional `compare_a`/`compare_b` query params |
| POST | `/api/cases/{id}/time-machine/snapshot` | |
| POST | `/api/cases/{id}/simulation`, `/crash-test` | always rolls back (see architecture.md) |
| GET | `/api/cases/{id}/simulation/supported-events` | |
| GET | `/api/cases/{id}/evaluation` | |
| GET | `/api/cases/{id}/integration/nyaya-satya` | |
| POST | `/api/cases/{id}/custody-events/manual` | creates a `USER_REPORTED` event |

Errors follow a consistent shape: `{"error": "...", "code": <status>, "path": "..."}`
(see `app/main.py`'s exception handler).
