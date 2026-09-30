# API

Interactive docs (auto-generated from the actual Pydantic schemas): run the
backend and visit `http://localhost:8000/docs`.

All endpoints require an `X-User-Id` header identifying a real `User` row
(see `backend/app/routers/users.py` for how to create one) except
`/api/health`, `/api/demo/seed`, and `/api/demo/marker`.

## Cases & filing packages

| Method | Path | Notes |
|---|---|---|
| POST | `/api/cases` | Creates a case owned by the caller |
| GET | `/api/cases` | Lists the caller's cases (all cases if ADMIN) |
| GET | `/api/cases/{case_id}` | 403 if the caller doesn't own it and isn't ADMIN |
| POST | `/api/cases/{case_id}/filing-packages` | |
| GET | `/api/cases/{case_id}/filing-packages` | |

## Documents

| Method | Path | Notes |
|---|---|---|
| POST | `/api/filing-packages/{id}/documents` | multipart upload; requires `UPLOAD_DOCUMENT` capability |
| GET | `/api/filing-packages/{id}/documents` | |
| GET | `/api/documents/{id}/versions` | |

## Requirements & checklist

| Method | Path | Notes |
|---|---|---|
| POST | `/api/filing-packages/{id}/requirements` | requires `CREATE_REQUIREMENT` capability |
| GET | `/api/filing-packages/{id}/requirements` | |
| GET | `/api/filing-packages/{id}/checklist` | |

## Precheck, defects, objections, corrections

| Method | Path | Notes |
|---|---|---|
| POST | `/api/filing-packages/{id}/precheck` | requires `RUN_PRECHECK`; runs the full detection pipeline |
| GET | `/api/filing-packages/{id}/defects` | |
| GET | `/api/defects/{id}` | |
| POST | `/api/filing-packages/{id}/objections` | |
| GET | `/api/filing-packages/{id}/objections` | |
| POST | `/api/filing-packages/{id}/corrections` | |
| GET | `/api/filing-packages/{id}/corrections` | |

## Review & audit

| Method | Path | Notes |
|---|---|---|
| GET | `/api/filing-packages/{id}/review-queue` | pending `ReviewTask`s |
| POST | `/api/reviews/{review_id}/approve` | requires `APPROVE_REVIEW`; confirms the underlying defect |
| POST | `/api/reviews/{review_id}/reject` | requires `REJECT_REVIEW`; rejects the underlying defect |
| GET | `/api/filing-packages/{id}/audit` | requires `VIEW_AUDIT` |

## NYAYA-SATYA integration

| Method | Path | Notes |
|---|---|---|
| GET | `/api/integration/nyaya-satya/cases/{case_id}/summary` | read-only operational summary, see `docs/nyaya-satya-integration.md` |

## Demo & users

| Method | Path | Notes |
|---|---|---|
| POST | `/api/demo/seed` | idempotent; seeds the 3 fixed demo cases if not already present |
| GET | `/api/demo/marker` | returns the exact "DEMONSTRATION DATA" string the frontend displays |
| POST | `/api/users` | creates or returns a user by email — see limitations in docs/security.md |

## Error shape

Every error response is `{"error": "<CODE>", "detail": "<message>"}` — see
`backend/app/main.py`'s two exception handlers. `AccessDenied` → 403;
anything unexpected → 500, with the detail message but never a stack
trace. FastAPI's built-in validation errors (422) retain their standard
shape.

## Planned (Section 2)

`GET /api/filing-packages/{id}/dependency-graph`,
`GET /api/filing-packages/{id}/verification`,
`POST /api/filing-packages/{id}/simulation`,
`POST /api/filing-packages/{id}/crash-test`,
`GET /api/filing-packages/{id}/time-machine`,
`GET /api/filing-packages/{id}/evaluation` are in the original spec's API
list but not yet implemented — see the README's "Current build status"
section.
