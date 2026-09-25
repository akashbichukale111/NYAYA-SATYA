"""Graph structures for NYAYA-SATYA Case Digital Twin."""

from __future__ import annotations

from nyaya_twin.graph.case_graph import CaseGraph
from nyaya_twin.graph.claim_graph import ClaimGraph
from nyaya_twin.graph.dependency_graph import DependencyGraph
from nyaya_twin.graph.evidence_graph import EvidenceGraph
from nyaya_twin.graph.timeline_graph import TimelineGraph

__all__ = [
    "CaseGraph",
    "ClaimGraph",
    "DependencyGraph",
    "EvidenceGraph",
    "TimelineGraph",
]
