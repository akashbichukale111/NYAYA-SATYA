"""
Root Cause Investigator Agent (Section 10).

Recursively walks the dependency chain behind a bottleneck's leaf dependency,
building an inspectable step-by-step chain (Section 7/48). Stops when:
  - the chain reaches a dependency with no further unresolved ancestors
    (root reached), or
  - MAX_DEPTH is hit (loop guard — Section 10: "never loop indefinitely").

For CONTRADICTED dependencies, runs a lightweight structured-disagreement
check (Section 37) instead of pretending a single answer exists.
"""
from __future__ import annotations

import uuid

from sqlmodel import Session, select

from ..models import Bottleneck, RootCauseCandidate, Transition, Dependency, ConfidenceLabel
from ..graph import load_case_graph

MAX_DEPTH = 6


class RootCauseInvestigatorAgent:
    name = "root-cause-investigator"

    def run(self, session: Session, bottleneck: Bottleneck) -> RootCauseCandidate:
        graph = load_case_graph(session, bottleneck.case_id)
        leaf_id = bottleneck.dependency_refs[0] if bottleneck.dependency_refs else None
        leaf_dep = graph.dependencies.get(leaf_id) if leaf_id else None

        chain: list[dict] = []

        # Step 1: the pending transition(s) this bottleneck affects
        affected_names = [graph.transitions[t].name for t in bottleneck.affected_transitions if t in graph.transitions]
        chain.append({
            "step": "Pending Transition",
            "description": "; ".join(affected_names) or "Unknown transition",
            "evidence": [],
            "confidence": ConfidenceLabel.CONFIRMED.value,
        })

        if leaf_dep and leaf_dep.status == "CONTRADICTED":
            chain.append({
                "step": "Immediate Blocker",
                "description": leaf_dep.description,
                "evidence": leaf_dep.evidence_refs,
                "confidence": ConfidenceLabel.LIKELY.value,
            })
            debate = [
                {"agent": "Agent A", "claim": f"Evidence {leaf_dep.evidence_refs[0]} supports the dependency being satisfied."} if leaf_dep.evidence_refs else None,
                {"agent": "Agent B", "claim": f"Evidence {leaf_dep.evidence_refs[1]} contradicts that." } if len(leaf_dep.evidence_refs) > 1 else None,
                {"agent": "Agent C", "claim": "Evidence is contradictory — confidence cannot exceed LIKELY. Human review required before treating either source as authoritative."},
            ]
            chain.append({
                "step": "Multi-Agent Debate",
                "description": "Sources disagree; no single answer is asserted.",
                "debate": [d for d in debate if d],
                "confidence": ConfidenceLabel.LIKELY.value,
            })
            candidate = RootCauseCandidate(
                id=f"rcc_{uuid.uuid4().hex[:10]}", bottleneck_id=bottleneck.id, case_id=bottleneck.case_id,
                chain=chain, confidence=ConfidenceLabel.LIKELY, is_primary=True,
            )
            session.add(candidate)
            session.commit()
            session.refresh(candidate)
            return candidate

        # Walk the depends_on chain from the immediate prerequisite down to the leaf
        current_id = leaf_id
        depth = 0
        path: list[str] = []
        # Reconstruct the path by walking forward from any transition prerequisite
        # that transitively reaches this leaf (there may be several; take the first).
        start_ids = [
            pid for t in graph.transitions.values() for pid in t.prerequisite_dependency_ids
            if pid in graph.dependencies
        ]
        visited = set()
        for start in start_ids:
            found_path = self._path_to_leaf(graph, start, leaf_id, [], visited)
            if found_path:
                path = found_path
                break
        if not path and leaf_id:
            path = [leaf_id]

        for i, dep_id in enumerate(path[:MAX_DEPTH]):
            dep = graph.dependencies.get(dep_id)
            if not dep:
                continue
            label = "Immediate Blocker" if i == 0 else ("Root Cause Candidate" if dep_id == leaf_id else "Dependency")
            chain.append({
                "step": label,
                "description": dep.description,
                "evidence": dep.evidence_refs,
                "confidence": (ConfidenceLabel.CONFIRMED.value if dep.evidence_refs
                               else ConfidenceLabel.POSSIBLE.value if dep.note
                               else ConfidenceLabel.UNKNOWN.value),
            })
            depth += 1

        overall_confidence = bottleneck.confidence
        candidate = RootCauseCandidate(
            id=f"rcc_{uuid.uuid4().hex[:10]}", bottleneck_id=bottleneck.id, case_id=bottleneck.case_id,
            chain=chain, confidence=overall_confidence, is_primary=True,
        )
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        return candidate

    def _path_to_leaf(self, graph, current_id, target_id, path, visited) -> list[str] | None:
        if current_id in visited:
            return None
        visited = visited | {current_id}
        path = path + [current_id]
        if current_id == target_id:
            return path
        dep = graph.dependencies.get(current_id)
        if not dep:
            return None
        for child in dep.depends_on:
            result = self._path_to_leaf(graph, child, target_id, path, visited)
            if result:
                return result
        return None
