# API reference

Every route below was read directly off the running application's OpenAPI
schema (`app.openapi()`), not hand-typed -- so it's guaranteed to match
what's actually registered. Full interactive docs with request/response
schemas are always available at `http://localhost:8000/docs` once the
server is running.

All routes are prefixed `/api`. Auth is via `X-User-Id` / `X-User-Role`
headers (see `docs/security.md`); omit both to get the backward-compatible
`ADMIN`/`system-user` default.

## Cases
| Method | Path | Notes |
|---|---|---|
| POST | `/cases` | Create a case; owner = calling actor |
| GET | `/cases` | List cases visible to the calling actor |
| GET | `/cases/{case_id}` | |
| POST | `/cases/demo/seed/{demo_key}` | `demo_key` is `A`, `B`, or `C`; no auth required, always open |

## Documents
| Method | Path | Notes |
|---|---|---|
| POST | `/cases/{case_id}/documents` | Multipart upload; validates, hashes, stores or quarantines |
| GET | `/cases/{case_id}/documents` | |
| GET | `/documents/{document_id}` | |
| POST | `/documents/{document_id}/process` | Runs the 12-agent extraction pipeline; document must be `INGESTED` |

## Evidence
| Method | Path | Notes |
|---|---|---|
| POST | `/cases/{case_id}/evidence` | Manual evidence entry |
| GET | `/cases/{case_id}/evidence` | |
| GET | `/evidence/{evidence_id}` | |

## Claims
| Method | Path |
|---|---|
| POST | `/cases/{case_id}/claims` |
| GET | `/cases/{case_id}/claims` |
| GET | `/claims/{claim_id}` |

## Issues
| Method | Path |
|---|---|
| POST | `/cases/{case_id}/issues` |
| GET | `/cases/{case_id}/issues` |
| GET | `/issues/{issue_id}` |

## Relationships
| Method | Path | Notes |
|---|---|---|
| POST | `/cases/{case_id}/relationships` | Direct creation (for a human/manual entry); agent-proposed relationships instead go through the review queue |
| GET | `/cases/{case_id}/relationships` | |

## Dependency graph
| Method | Path | Notes |
|---|---|---|
| GET | `/cases/{case_id}/dependency-graph` | Full node/edge list for React-Flow-style rendering |
| GET | `/cases/{case_id}/coverage` | Real-time coverage metrics (see docs/dependency-engine.md) |
| GET | `/cases/{case_id}/fragility` | Single-point-dependency report, sorted by risk |
| GET | `/cases/{case_id}/missing-evidence` | Unsupported claims/issues, conflicting-only support |

## Impact + crash test
| Method | Path | Notes |
|---|---|---|
| GET | `/evidence/{evidence_id}/impact` | |
| GET | `/claims/{claim_id}/impact` | |
| POST | `/evidence/{evidence_id}/crash-test` | Body: `{event_type, target_type, target_id}`; always non-destructive |

## Review queue (Human Legal Gate)
| Method | Path | Notes |
|---|---|---|
| GET | `/cases/{case_id}/review-queue` | |
| POST | `/reviews/{review_id}/approve` | Requires role `>= ADVOCATE`; applies the change |
| POST | `/reviews/{review_id}/reject` | Requires role `>= ADVOCATE`; no change applied |

## Audit
| Method | Path |
|---|---|
| GET | `/cases/{case_id}/audit` |

## Evaluation Lab
| Method | Path |
|---|---|
| GET | `/cases/{case_id}/evaluation` |

## Time Machine
| Method | Path | Notes |
|---|---|---|
| GET | `/evidence/{evidence_id}/history` | Full version list |
| GET | `/evidence/{evidence_id}/current-vs-previous` | Latest two versions + diff |
| GET | `/evidence/{evidence_id}/diff?from_version=&to_version=` | Diff between any two versions |
| GET | `/claims/{claim_id}/history` | Same pattern, for claims |
| GET | `/claims/{claim_id}/current-vs-previous` | |
| GET | `/claims/{claim_id}/diff?from_version=&to_version=` | |
| GET | `/cases/{case_id}/time-machine?at=<ISO8601>` | Whole-case reconstruction (evidence + claim states) at a past timestamp |

## NYAYA-SATYA integration
| Method | Path | Notes |
|---|---|---|
| GET | `/cases/{case_id}/integration-summary` | Stable contract for downstream modules; see docs/nyaya-satya-integration.md |

## Health
| Method | Path |
|---|---|
| GET | `/health` |
