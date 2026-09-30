"""
Readiness Simulator (section 14). Operates entirely on in-memory deep
copies of requirement/evidence/blocker dicts. Nothing here ever calls
db.add/db.commit against the live tables for case state -- only the
Simulation audit record itself is persisted (section 14: "Never modify
production case state during simulation.").
"""
from __future__ import annotations

import copy

from app.models.requirement import Requirement
from app.models.evidence import Evidence
from app.models.blocker import Blocker
from app.models.hearing import Hearing
from app.models.simulation import Simulation
from app.services.readiness_engine import (
    build_readiness_snapshot, compute_requirement_status,
)


def _load_state(db, case_id: str):
    reqs = [r.to_dict() for r in db.query(Requirement).filter(Requirement.case_id == case_id).all()]
    evid = {e.id: e.to_dict() for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()}
    blockers = [b.to_dict() for b in db.query(Blocker).filter(Blocker.case_id == case_id).all()]
    hearing = db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    hearing_uncertain = (hearing is None) or (hearing.purpose_status == "UNCERTAIN")
    return reqs, evid, blockers, hearing_uncertain


def _recompute(reqs, evid, blockers, hearing_uncertain):
    reqs = copy.deepcopy(reqs)
    for r in reqs:
        linked = [evid[eid] for eid in (r.get("evidence_refs") or []) if eid in evid]
        status, reason, confidence = compute_requirement_status(linked)
        r["status"], r["reason"], r["confidence"] = status, reason, confidence

    resolved_ids = {r["id"] for r in reqs if r["status"] == "SATISFIED"}
    blockers = copy.deepcopy(blockers)
    for b in blockers:
        if b["requirement_id"] in resolved_ids and b["status"] == "OPEN":
            b["status"] = "SIMULATED_RESOLVED"

    return reqs, blockers, build_readiness_snapshot(reqs, blockers, hearing_uncertain)


def simulate(db, case_id: str, hypothesis: list[dict]) -> Simulation:
    """
    hypothesis: list of steps like
      {"type": "resolve_evidence", "evidence_id": "..."}
      {"type": "resolve_requirement", "requirement_id": "..."}
    Applied in order to CLONED evidence/requirement dicts only.
    """
    reqs, evid, blockers, hearing_uncertain = _load_state(db, case_id)
    baseline = build_readiness_snapshot(reqs, blockers, hearing_uncertain)

    evid = copy.deepcopy(evid)
    reqs = copy.deepcopy(reqs)

    for step in hypothesis:
        if step.get("type") == "resolve_evidence" and step.get("evidence_id") in evid:
            e = evid[step["evidence_id"]]
            e["availability"] = "AVAILABLE"
            e["verification_state"] = "VERIFIED"
        elif step.get("type") == "resolve_requirement":
            rid = step.get("requirement_id")
            for r in reqs:
                if r["id"] == rid:
                    for eid in (r.get("evidence_refs") or []):
                        if eid in evid:
                            evid[eid]["availability"] = "AVAILABLE"
                            evid[eid]["verification_state"] = "VERIFIED"

    sim_reqs, sim_blockers, sim_snapshot = _recompute(reqs, evid, blockers, hearing_uncertain)

    diff = {
        "resolved_blockers": [
            b["id"] for b in sim_blockers if b["status"] == "SIMULATED_RESOLVED"
        ],
        "category_changes": {
            k: {"before": baseline["categories"].get(k), "after": sim_snapshot["categories"].get(k)}
            for k in sim_snapshot["categories"]
            if baseline["categories"].get(k) != sim_snapshot["categories"].get(k)
        },
        "overall_change": {"before": baseline["overall"], "after": sim_snapshot["overall"]},
    }

    record = Simulation(
        case_id=case_id, hypothesis=hypothesis,
        baseline_readiness=baseline, simulated_readiness=sim_snapshot, diff=diff,
    )
    db.add(record)
    db.flush()
    return record
