"""
Bottleneck Discovery Agent (Section 9).

Responsibility (bounded): inspect case state (dependencies + transitions),
identify candidate bottlenecks (unsatisfied/unknown/contradicted dependencies
that are the deepest unresolved point in a blocked transition's chain),
estimate confidence and attention from explainable factors, and
create/update Bottleneck rows. It does NOT plan actions and does NOT execute
anything — that is other agents' jobs (Section 35: bounded responsibilities).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Session, select

from ..models import (
    Bottleneck, BottleneckType, BottleneckStatus, ConfidenceLabel,
    AttentionState, BottleneckHistoryEntry, utcnow,
)
from ..graph import load_case_graph, CaseGraph

TYPE_MAP = {
    "document": BottleneckType.DOCUMENT_BLOCKER,
    "filing": BottleneckType.FILING_BLOCKER,
    "service": BottleneckType.SERVICE_BLOCKER,
    "evidence": BottleneckType.EVIDENCE_BLOCKER,
    "unknown": BottleneckType.UNKNOWN_BLOCKER,
}


def _confidence_for(dep) -> ConfidenceLabel:
    """Confidence is derived from status + evidence_refs only. `note` is a
    human-readable annotation for the UI, never a substitute for evidence —
    so it deliberately does NOT influence confidence (Section 38)."""
    if dep.status == "CONTRADICTED":
        return ConfidenceLabel.LIKELY  # contradiction itself is confirmed; underlying fact is not
    if dep.status == "UNKNOWN":
        return ConfidenceLabel.UNKNOWN
    if dep.status == "UNSATISFIED":
        return ConfidenceLabel.CONFIRMED if dep.evidence_refs else ConfidenceLabel.LIKELY
    return ConfidenceLabel.UNKNOWN


def _attention_for(confidence: ConfidenceLabel, affected_count: int, age_days: int) -> tuple[AttentionState, dict]:
    factors = {
        "affected_transitions": affected_count,
        "age_days": age_days,
        "confidence": confidence.value,
    }
    if confidence == ConfidenceLabel.UNKNOWN:
        return AttentionState.UNKNOWN, factors
    if affected_count >= 3 or (confidence == ConfidenceLabel.CONFIRMED and age_days > 30):
        return AttentionState.CRITICAL, factors
    if affected_count >= 2 or confidence == ConfidenceLabel.CONFIRMED:
        return AttentionState.HIGH, factors
    if confidence in (ConfidenceLabel.LIKELY, ConfidenceLabel.POSSIBLE):
        return AttentionState.NORMAL, factors
    return AttentionState.LOW, factors


def _bottleneck_type_for(dep) -> BottleneckType:
    if dep.status == "CONTRADICTED":
        return BottleneckType.CONTRADICTION_BLOCKER
    return TYPE_MAP.get(dep.type, BottleneckType.UNKNOWN_BLOCKER)


class BottleneckDiscoveryAgent:
    name = "bottleneck-discovery-agent"

    def run(self, session: Session, case_id: str) -> list[Bottleneck]:
        graph: CaseGraph = load_case_graph(session, case_id)
        candidate_leaf_ids: set[str] = set()

        for t in graph.blocked_transitions():
            for prereq_id in t.prerequisite_dependency_ids:
                dep = graph.dependencies.get(prereq_id)
                if not dep:
                    continue
                if dep.status == "CONTRADICTED":
                    candidate_leaf_ids.add(dep.id)
                    continue
                candidate_leaf_ids.update(graph.unsatisfied_leaf_dependencies(dep.id))

        results: list[Bottleneck] = []
        for leaf_id in candidate_leaf_ids:
            dep = graph.dependencies.get(leaf_id)
            if not dep:
                continue
            confidence = _confidence_for(dep)
            affected = graph.transitions_gated_by(leaf_id)
            age_days = (utcnow() - dep.since).days if dep.since else 0
            attention, factors = _attention_for(confidence, len(affected), age_days)
            blocked_items = [graph.transitions[tid].name for tid in affected if tid in graph.transitions]

            existing = session.exec(
                select(Bottleneck).where(Bottleneck.case_id == case_id)
            ).all()
            match = next((b for b in existing if b.dependency_refs == [leaf_id]), None)

            if match is None:
                bn = Bottleneck(
                    id=f"bn_{uuid.uuid4().hex[:10]}",
                    case_id=case_id,
                    type=_bottleneck_type_for(dep),
                    description=f"Blocked on: {dep.description}",
                    root_cause_candidate=dep.description,
                    evidence_refs=list(dep.evidence_refs),
                    dependency_refs=[leaf_id],
                    affected_transitions=affected,
                    blocked_items=blocked_items,
                    first_observed_at=dep.since or utcnow(),
                    last_confirmed_at=utcnow(),
                    last_updated_at=utcnow(),
                    severity_factors=factors,
                    attention_state=attention,
                    confidence=confidence,
                    status=BottleneckStatus.INVESTIGATING,
                    missing_evidence=[] if dep.evidence_refs else [f"No evidence on file for: {dep.description}"],
                    contradicting_evidence=list(dep.evidence_refs) if dep.status == "CONTRADICTED" else [],
                )
                session.add(bn)
                session.commit()
                session.refresh(bn)
                session.add(BottleneckHistoryEntry(
                    id=f"hist_{uuid.uuid4().hex[:10]}", bottleneck_id=bn.id, case_id=case_id,
                    from_status="NONE", to_status=bn.status.value,
                    note="Detected by Bottleneck Discovery Agent.",
                ))
                session.commit()
                results.append(bn)
            else:
                was_resolved = match.status == BottleneckStatus.RESOLVED
                match.evidence_refs = list(dep.evidence_refs)
                match.affected_transitions = affected
                match.blocked_items = blocked_items
                match.severity_factors = factors
                match.attention_state = attention
                match.confidence = confidence
                match.last_confirmed_at = utcnow()
                match.last_updated_at = utcnow()
                match.contradicting_evidence = list(dep.evidence_refs) if dep.status == "CONTRADICTED" else []
                if was_resolved:
                    match.recurrence_count += 1
                    match.status = BottleneckStatus.REOPENED
                    session.add(BottleneckHistoryEntry(
                        id=f"hist_{uuid.uuid4().hex[:10]}", bottleneck_id=match.id, case_id=case_id,
                        from_status=BottleneckStatus.RESOLVED.value, to_status=BottleneckStatus.REOPENED.value,
                        note="New evidence shows this dependency is unsatisfied again.",
                    ))
                session.add(match)
                session.commit()
                session.refresh(match)
                results.append(match)

        return results
