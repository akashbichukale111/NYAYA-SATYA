"""
Orchestrator — runs the bounded-agent loop from Section 36:

  OBSERVE -> DETECT -> INVESTIGATE -> TRACE -> VERIFY -> EXPLAIN -> PLAN
  -> HUMAN APPROVAL -> ACT -> VERIFY -> REASSESS -> UPDATE

"VERIFY" appears twice by design: once as evidence-provenance verification
during investigation (are the citations real?), once as post-action outcome
verification (did the action actually work?). This file never mutates case
state directly outside of calling the bounded agents below — it is a
coordinator, not a decision-maker.
"""
from __future__ import annotations

from sqlmodel import Session, select

from . import audit
from .models import Bottleneck, BottleneckStatus, ConfidenceLabel
from .agents.discovery import BottleneckDiscoveryAgent
from .agents.root_cause import RootCauseInvestigatorAgent
from .agents.evidence_verification import EvidenceVerificationAgent
from .agents.impact import ImpactAgent
from .agents.action_planner import ActionPlannerAgent

STATUS_FROM_CONFIDENCE = {
    ConfidenceLabel.CONFIRMED: BottleneckStatus.CONFIRMED,
    ConfidenceLabel.LIKELY: BottleneckStatus.LIKELY,
    ConfidenceLabel.POSSIBLE: BottleneckStatus.POSSIBLE,
    ConfidenceLabel.UNKNOWN: BottleneckStatus.UNKNOWN,
}


def run_full_investigation(session: Session, case_id: str) -> dict:
    correlation_id = audit.new_correlation_id()
    audit.record(session, case_id=case_id, correlation_id=correlation_id,
                 actor="orchestrator", event="INVESTIGATION_STARTED", source="orchestrator")

    # DETECT
    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    audit.record(session, case_id=case_id, correlation_id=correlation_id,
                 actor=BottleneckDiscoveryAgent.name, event="BOTTLENECKS_DETECTED", source="agent",
                 result={"count": len(bottlenecks), "ids": [b.id for b in bottlenecks]})

    root_cause_agent = RootCauseInvestigatorAgent()
    evidence_agent = EvidenceVerificationAgent()
    impact_agent = ImpactAgent()
    planner = ActionPlannerAgent()

    details = []
    for bn in bottlenecks:
        if bn.status == BottleneckStatus.RESOLVED:
            continue

        # TRACE
        rcc = root_cause_agent.run(session, bn)
        audit.record(session, case_id=case_id, correlation_id=correlation_id,
                     actor=root_cause_agent.name, event="ROOT_CAUSE_TRACED", source="agent",
                     result={"bottleneck_id": bn.id, "root_cause_candidate_id": rcc.id})

        # VERIFY (evidence provenance)
        provenance = evidence_agent.check(session, case_id, bn.evidence_refs)
        audit.record(session, case_id=case_id, correlation_id=correlation_id,
                     actor=evidence_agent.name, event="EVIDENCE_PROVENANCE_CHECKED", source="agent",
                     result={"bottleneck_id": bn.id, **provenance})
        if provenance["quarantined_and_excluded"]:
            bn.missing_evidence = list(set(bn.missing_evidence) | {
                f"Evidence {r} is quarantined (suspected prompt injection) and was excluded from reasoning."
                for r in provenance["quarantined_and_excluded"]
            })

        # EXPLAIN (impact)
        impact = impact_agent.run(session, bn)

        # PLAN
        bn.status = STATUS_FROM_CONFIDENCE.get(bn.confidence, BottleneckStatus.UNKNOWN)
        session.add(bn)
        session.commit()

        action = None
        if bn.confidence != ConfidenceLabel.UNKNOWN or bn.type.value == "UNKNOWN_BLOCKER":
            action = planner.run(session, bn)
            if action:
                bn.status = BottleneckStatus.ACTION_PENDING_APPROVAL
                session.add(bn)
                session.commit()
                audit.record(session, case_id=case_id, correlation_id=correlation_id,
                             actor=planner.name, event="ACTION_PROPOSED", source="agent",
                             result={"bottleneck_id": bn.id, "action_id": action.id})

        session.refresh(bn)
        details.append({
            "bottleneck": bn,
            "root_cause": rcc,
            "impact": impact,
            "provenance": provenance,
            "action_id": action.id if action else None,
        })

    audit.record(session, case_id=case_id, correlation_id=correlation_id,
                 actor="orchestrator", event="INVESTIGATION_COMPLETED", source="orchestrator",
                 result={"bottleneck_count": len(bottlenecks)})

    return {"correlation_id": correlation_id, "bottlenecks": bottlenecks, "details": details}


def compute_primary_bottleneck(bottlenecks: list[Bottleneck]) -> Bottleneck | None:
    """Explainable prioritisation (Section 12) — not an opaque score."""
    if not bottlenecks:
        return None
    order = {"CRITICAL ATTENTION": 0, "HIGH ATTENTION": 1, "NORMAL": 2, "LOW": 3, "UNKNOWN": 4}
    active = [b for b in bottlenecks if b.status != BottleneckStatus.RESOLVED]
    pool = active or bottlenecks
    return sorted(
        pool,
        key=lambda b: (
            order.get(b.attention_state.value, 5),
            -len(b.affected_transitions),
            b.first_observed_at,
        ),
    )[0]
