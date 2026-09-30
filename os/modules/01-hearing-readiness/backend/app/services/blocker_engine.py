"""
Blocker Intelligence Engine (section 7).

A blocker is only created for a requirement that is UNRESOLVED -- never
merely because a document is absent in isolation. downstream_impact is
always phrased in terms of the specific hearing dependency, per the
spec's explicit warning against calling something a blocker without
explaining why it matters right now.
"""
from __future__ import annotations

from app.models.requirement import Requirement
from app.models.blocker import Blocker
from app.models.hearing import Hearing
from app.services.readiness_engine import SEVERITY_BY_CATEGORY
from app.models.mixins import utcnow

SUGGESTED_ACTION_BY_CATEGORY = {
    "DOCUMENTS": "prepare_checklist",
    "PROCEDURE": "prepare_checklist",
    "SERVICE": "draft_reminder_notice",
    "EVIDENCE": "compile_evidence_index",
    "APPLICATIONS": "draft_reminder_notice",
    "ORDERS": "prepare_checklist",
    "DEADLINES": "draft_reminder_notice",
}

DOWNSTREAM_IMPACT_TEMPLATE = (
    "The next hearing ({hearing_purpose}) relies on the '{category}' "
    "readiness category. Requirement '{description}' is unresolved, so the "
    "bench may not be able to proceed on this point without it."
)


def sync_blockers(db, case_id: str) -> None:
    reqs = db.query(Requirement).filter(Requirement.case_id == case_id).all()
    existing = {b.requirement_id: b for b in db.query(Blocker).filter(Blocker.case_id == case_id).all()}
    hearing = db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    hearing_purpose = (hearing.purpose if hearing and hearing.purpose else "purpose not yet determined")

    for req in reqs:
        blocker = existing.get(req.id)
        if req.status == "UNRESOLVED":
            severity = SEVERITY_BY_CATEGORY.get(req.category, "MEDIUM")
            impact = DOWNSTREAM_IMPACT_TEMPLATE.format(
                hearing_purpose=hearing_purpose, category=req.category, description=req.description,
            )
            suggested = SUGGESTED_ACTION_BY_CATEGORY.get(req.category, "prepare_checklist")
            if blocker is None:
                blocker = Blocker(
                    case_id=case_id,
                    requirement_id=req.id,
                    description=f"Unresolved: {req.description}",
                    category=req.category,
                    severity=severity,
                    evidence_refs=req.evidence_refs or [],
                    dependent_requirements=[req.id],
                    downstream_impact=impact,
                    responsible_actor=req.responsible_actor,
                    deadline=None,
                    status="OPEN",
                    confidence=req.confidence,
                    suggested_safe_action=suggested,
                    history=[{"event": "CREATED", "timestamp": utcnow().isoformat()}],
                )
                db.add(blocker)
            else:
                if blocker.status != "OPEN":
                    blocker.history = (blocker.history or []) + [
                        {"event": "REOPENED", "timestamp": utcnow().isoformat()}
                    ]
                blocker.status = "OPEN"
                blocker.severity = severity
                blocker.downstream_impact = impact
                blocker.confidence = req.confidence
                blocker.evidence_refs = req.evidence_refs or []
        else:
            if blocker is not None and blocker.status == "OPEN":
                blocker.status = "RESOLVED"
                blocker.history = (blocker.history or []) + [
                    {"event": "RESOLVED", "timestamp": utcnow().isoformat()}
                ]
