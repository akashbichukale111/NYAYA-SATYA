# Demo Mode

Code: `backend/app/services/seed_demo.py`, `backend/app/routers/demo.py`.

## Seeding

```bash
curl -X POST http://localhost:8000/api/demo/seed
```

Idempotent: if any `is_demo=true` case already exists, it returns the
existing demo case ids rather than creating duplicates
(`seed_all_demo_cases`).

## The 3 cases

All three are built deterministically — same documents, same requirement
text, same objection text every time (no randomness anywhere in
`seed_demo.py`), then run through the real `precheck` pipeline (not
canned defect output) so the demo actually exercises the detection code.

1. **Demo A — Missing Attachment** (`seed_demo_a`): a petition's text
   references "Annexure A" and "Annexure B"; only Annexure A is uploaded.
   A `REFERENCE_REQUIRED` requirement targets Annexure B, sourced from a
   `USER_PROVIDED_CHECKLIST`. Precheck detects `MISSING_REFERENCED_ITEM`.

2. **Demo B — Metadata Conflict** (`seed_demo_b`): an affidavit declares
   `case_number=DEMO-B-001`; an application form in the same package
   declares `case_number=DEMO-B-002`. Precheck detects
   `IDENTIFIER_MISMATCH`, `status=UNRESOLVED` — the engine does not guess
   which is right.

3. **Demo C — Objection + Correction** (`seed_demo_c`): a
   `RegistryObjection` is recorded, precheck links it to an
   `UNRESOLVED_OBJECTION` defect, then a `CorrectionRequest` +
   `CorrectionSubmission` (`simulated=True`) + `Verification`
   (`result=PENDING`) are created to show the full
   objection → defect → correction → verification chain end to end.

## The "DEMONSTRATION DATA" marker

Every `Case` row created by the seed script has `is_demo=True`. The
frontend (`CommandCenterPage.tsx`, `CasesPage.tsx`, `CaseDetailPage.tsx`)
checks this flag and renders a
**"DEMONSTRATION DATA — NOT A REAL CASE"** badge wherever the case appears.
`GET /api/demo/marker` exposes the exact string so any future screen can
reuse it verbatim rather than re-typing it.

## Verifying it yourself

```bash
cd backend && . venv/bin/activate
python -c "
from app.core.database import init_db, SessionLocal
init_db()
db = SessionLocal()
from app.services.seed_demo import seed_all_demo_cases
print(seed_all_demo_cases(db))
"
```
This was run during development of this build and produced the expected
defects for all three cases (see the "Progress" notes in project history);
it is not a claim made without having actually executed it.
