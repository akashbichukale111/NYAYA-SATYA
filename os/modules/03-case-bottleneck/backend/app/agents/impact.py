"""
Impact Agent (Section 11). Workflow impact only — never legal outcome impact.
"""
from __future__ import annotations

from sqlmodel import Session

from ..models import Bottleneck
from ..graph import load_case_graph


class ImpactAgent:
    name = "impact-agent"

    def run(self, session: Session, bottleneck: Bottleneck) -> dict:
        graph = load_case_graph(session, bottleneck.case_id)
        affected = bottleneck.affected_transitions
        all_transitions = list(graph.transitions.values())
        unaffected_pending = [
            t.name for t in all_transitions
            if t.id not in affected and t.status == "PENDING"
        ]
        return {
            "affected_transitions": [graph.transitions[t].name for t in affected if t in graph.transitions],
            "dependent_items": bottleneck.blocked_items,
            "downstream_consequences": (
                f"{len(affected)} workflow transition(s) cannot proceed until this is resolved."
                if affected else "No workflow transitions are currently gated by this — informational only."
            ),
            "blocked_work": bottleneck.blocked_items,
            "unblockable_work": unaffected_pending,
            "unknown_effects": (
                ["Effect on downstream steps beyond the immediate transition(s) is not modelled — run Simulation for a scoped estimate."]
            ),
        }
