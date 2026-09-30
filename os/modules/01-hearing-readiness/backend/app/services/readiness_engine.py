"""
Readiness Audit Engine (section 6).

Design principle: readiness is never a magic single percentage. It is
computed deterministically from evidence-backed Requirement rows using
the pure functions below (fully unit-testable, no LLM involved), then
aggregated per category, then to one overall state. The LLM provider is
never consulted for this calculation -- only for optional narrative
phrasing elsewhere.
"""
from __future__ import annotations

from app.models.requirement import READINESS_CATEGORIES

STATUS_SATISFIED = "SATISFIED"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_UNKNOWN = "UNKNOWN"

OVERALL_READY = "READY"
OVERALL_CONDITIONAL = "CONDITIONAL"
OVERALL_BLOCKED = "BLOCKED"
OVERALL_UNKNOWN = "UNKNOWN"

# Deterministic baseline severity per category -- used by blocker_engine.
# Not arbitrary in the sense of "random"; it's a documented, fixed policy
# table that a legal-ops reviewer can inspect and adjust.
SEVERITY_BY_CATEGORY = {
    "DEADLINES": "CRITICAL",
    "SERVICE": "HIGH",
    "ORDERS": "HIGH",
    "PROCEDURE": "HIGH",
    "APPLICATIONS": "MEDIUM",
    "EVIDENCE": "MEDIUM",
    "DOCUMENTS": "MEDIUM",
}


def compute_requirement_status(evidence_items: list[dict]) -> tuple[str, str, str]:
    """Pure function: (status, reason, confidence) from linked evidence dicts.
    evidence dicts need: label, availability, verification_state.
    """
    if not evidence_items:
        return (
            STATUS_UNKNOWN,
            "No evidence has been linked to this requirement yet.",
            "UNKNOWN",
        )

    missing = [e for e in evidence_items if e.get("availability") == "MISSING"]
    if missing:
        labels = ", ".join(e["label"] for e in missing)
        return (
            STATUS_UNRESOLVED,
            f"Required evidence is missing: {labels}.",
            "HIGH",
        )

    disputed = [e for e in evidence_items if e.get("verification_state") == "DISPUTED"]
    if disputed:
        labels = ", ".join(e["label"] for e in disputed)
        return (
            STATUS_UNRESOLVED,
            f"Evidence is present but disputed/contradictory: {labels}.",
            "MEDIUM",
        )

    unverified = [e for e in evidence_items if e.get("verification_state") == "UNVERIFIED"]
    if unverified:
        labels = ", ".join(e["label"] for e in unverified)
        return (
            STATUS_UNRESOLVED,
            f"Evidence is present but not yet verified: {labels}.",
            "MEDIUM",
        )

    partial = [e for e in evidence_items if e.get("availability") == "PARTIAL"]
    if partial:
        labels = ", ".join(e["label"] for e in partial)
        return (
            STATUS_UNRESOLVED,
            f"Evidence is only partially available: {labels}.",
            "MEDIUM",
        )

    unknown_avail = [e for e in evidence_items if e.get("availability") == "UNKNOWN"]
    if unknown_avail:
        labels = ", ".join(e["label"] for e in unknown_avail)
        return (
            STATUS_UNKNOWN,
            f"Availability of linked evidence could not be confirmed: {labels}.",
            "LOW",
        )

    return (
        STATUS_SATISFIED,
        "All linked evidence is available and verified.",
        "HIGH",
    )


def compute_category_state(requirement_statuses: list[str]) -> str:
    """Pure aggregation over one category's requirement statuses."""
    if not requirement_statuses:
        return STATUS_UNKNOWN
    if any(s == STATUS_UNRESOLVED for s in requirement_statuses):
        return STATUS_UNRESOLVED
    if any(s == STATUS_UNKNOWN for s in requirement_statuses):
        return STATUS_UNKNOWN
    return STATUS_SATISFIED


def compute_overall_readiness(
    category_states: dict[str, str],
    hearing_context_uncertain: bool,
    open_blocker_severities: list[str],
) -> str:
    """Pure function combining category states + hearing-context certainty
    + open blocker severities into ONE explainable overall state."""
    if not category_states or hearing_context_uncertain:
        return OVERALL_UNKNOWN

    states = list(category_states.values())
    if all(s == STATUS_SATISFIED for s in states):
        return OVERALL_READY

    if any(s == STATUS_UNKNOWN for s in states) and not any(s == STATUS_UNRESOLVED for s in states):
        return OVERALL_UNKNOWN

    if any(sev in ("CRITICAL", "HIGH") for sev in open_blocker_severities):
        return OVERALL_BLOCKED

    if any(s == STATUS_UNRESOLVED for s in states):
        return OVERALL_CONDITIONAL

    return OVERALL_UNKNOWN


def build_readiness_snapshot(requirements: list[dict], blockers: list[dict],
                              hearing_context_uncertain: bool) -> dict:
    """Builds the full readiness object returned by the API / stored in
    CaseVersion snapshots. Pure function over plain dicts -> easy to test
    and to reuse identically inside simulation_engine / crash_test_engine."""
    # Only categories that actually have at least one requirement for THIS
    # case/hearing are scored -- a case with no ORDERS requirement, say,
    # should not be permanently stuck at UNKNOWN because of a category
    # that was never applicable to it.
    by_category: dict[str, list[str]] = {}
    for r in requirements:
        by_category.setdefault(r["category"], []).append(r["status"])

    category_states = {c: compute_category_state(v) for c, v in by_category.items()}

    open_sev = [b["severity"] for b in blockers if b.get("status") == "OPEN"]
    overall = compute_overall_readiness(category_states, hearing_context_uncertain, open_sev)

    return {
        "overall": overall,
        "categories": category_states,
        "hearing_context_uncertain": hearing_context_uncertain,
        "open_blocker_count": sum(1 for b in blockers if b.get("status") == "OPEN"),
        "requirement_count": len(requirements),
        "satisfied_count": sum(1 for r in requirements if r["status"] == STATUS_SATISFIED),
        "unresolved_count": sum(1 for r in requirements if r["status"] == STATUS_UNRESOLVED),
        "unknown_count": sum(1 for r in requirements if r["status"] == STATUS_UNKNOWN),
    }


# ---------------------------------------------------------------------
# DB orchestration (impure layer -- thin, delegates all logic above)
# ---------------------------------------------------------------------

def run_readiness_audit(db, case_id: str) -> dict:
    from app.models.requirement import Requirement
    from app.models.evidence import Evidence
    from app.models.blocker import Blocker
    from app.models.hearing import Hearing
    from app.services import blocker_engine, causal_graph, audit_service, time_machine
    import uuid

    correlation_id = uuid.uuid4().hex[:12]

    reqs = db.query(Requirement).filter(Requirement.case_id == case_id).all()
    evidence_by_id = {e.id: e for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()}

    for req in reqs:
        linked = [evidence_by_id[eid].to_dict() for eid in (req.evidence_refs or []) if eid in evidence_by_id]
        status, reason, confidence = compute_requirement_status(linked)
        req.status, req.reason, req.confidence = status, reason, confidence
    db.flush()

    hearing = (
        db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    )
    hearing_uncertain = (hearing is None) or (hearing.purpose_status == "UNCERTAIN")

    # Sync blockers from unresolved requirements (creates/updates/resolves).
    blocker_engine.sync_blockers(db, case_id)
    db.flush()

    blockers = [b.to_dict() for b in db.query(Blocker).filter(Blocker.case_id == case_id).all()]
    snapshot = build_readiness_snapshot([r.to_dict() for r in reqs], blockers, hearing_uncertain)

    causal_graph.sync_dependencies(db, case_id)
    version = time_machine.snapshot_version(db, case_id, trigger="readiness_audit")
    audit_service.log_event(
        db, case_id=case_id, actor="agent:readiness_agent", event_type="READINESS_AUDIT",
        action="run_readiness_audit", input_ref={"case_id": case_id},
        result={"overall": snapshot["overall"]}, correlation_id=correlation_id,
    )
    snapshot["version_id"] = version.id
    snapshot["version_number"] = version.version_number
    return snapshot
