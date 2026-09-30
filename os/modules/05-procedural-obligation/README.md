# Module 05: Procedural Obligation Engine

**Status**: `PARTIAL / SECTION 1 PRESENT - GROUNDED IN UNWIND OBLIGATION ENGINE`

## Architectural Role
The Procedural Obligation Engine enforces non-adjudicative statutory compliance following the UNWIND core standard:
Every legal correction requires four non-negotiable elements:
1. **WHO**: Counterparties who were given assertions or filings that are no longer true or legally complete.
2. **WHAT**: Concrete, reversible actions that can and must be undertaken.
3. **LOSS**: Irreversible exposure range with stated assumptions (never a single false point estimate).
4. **SIGN**: The human legal gate approver who must review and execute the obligation.

## Endpoints
- `GET /health` - Service health & status note
- `GET /api/cases/{case_id}/obligations` - Active obligations for case
- `GET /api/obligations/{obligation_id}` - Fetch obligation details
- `POST /api/obligations/{obligation_id}/sign` - Human signature authorization
- `GET /api/obligations/{obligation_id}/render` - Formatted legal memo rendering
