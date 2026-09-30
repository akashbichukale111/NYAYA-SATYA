# Domain Model

Full definitions: `backend/app/models/__init__.py`. Enums:
`backend/app/core/enums.py`.

## Entity groups

**Case hierarchy**: `Case` → `FilingPackage` → `FilingSubmission`. A case
holds one or more filing packages; a filing package is submitted (in the
simulated sense — see `docs/correction-workflow.md`) as a
`FilingSubmission` snapshot.

**Documents**: `Document` (the logical, named item — e.g. "Petition") has
one or more `DocumentVersion` rows (the actual uploaded bytes + extracted
text). A `DocumentVersion` has `DocumentSection` rows (page/paragraph/row
level, only when a real location was determined) and `DocumentMetadata`
rows (field/value pairs, either extracted or user-provided).

**Requirements**: `RequirementSet` (an imported/named group) contains
`Requirement` rows. Each `Requirement` always declares `source` and
carries `verification_status`. `ChecklistItem` links a `Requirement` to
its current FOUND/MISSING/... determination for one filing package.

**References**: `AttachmentReference` records a detected in-text reference
("Annexure B"); `AttachmentRequirement` links a reference to the
requirement it satisfies, when applicable.

**Integrity findings**: `DuplicateGroup`, `Conflict`, `Supersession` — all
purely descriptive; none of these tables has a code path that deletes or
auto-resolves anything (see `backend/app/services/duplicate_engine.py`,
`metadata_engine.py`).

**Defects**: `Defect` is the central finding row; `DefectEvidence` links it
to specific document/section/requirement evidence; `DefectResolution`
records how a human ultimately closed it.

**Registry feedback**: `RegistryObjection` (verbatim-preserved external
feedback) and `CorrectionRequest`/`CorrectionSubmission` (the planned and
simulated-submitted fix).

**Governance**: `ReviewTask` (the human-approval gate), `ActionProposal`
(a suggested next step), `Simulation` (crash-test/counterfactual runs, no
persistent side effects), `AuditEvent` (append-only), `ProvenanceRecord`
(where a piece of data actually came from), `Verification` (did a fix
actually take effect), `User`.

## Case isolation

Every case-scoped table has a `case_id` column, and every query in
`backend/app/routers/` and `backend/app/services/` filters on it. Access
control (`backend/app/core/security.assert_case_access`) additionally
checks the requesting user owns the case (or is `ADMIN`) before any
case-scoped query runs — so even a correct `case_id` filter is only ever
reached after that check.

## KNOWN / SOURCE_SUPPORTED / ... vocabulary

`VerificationStatus` (`backend/app/core/enums.py`) is used consistently
across `Requirement.verification_status`, `Defect.verification_status`,
and `DocumentMetadata.confidence` so the same "how sure are we, and how do
we know" vocabulary applies everywhere in the system:
`KNOWN, SOURCE_SUPPORTED, USER_REPORTED, SYSTEM_DETECTED, UNVERIFIED,
CONFLICTING, UNKNOWN, REQUIRES_HUMAN_REVIEW`.
