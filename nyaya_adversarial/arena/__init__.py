"""Evidence Conflict Arena module for NYAYA-SATYA."""

from __future__ import annotations

from nyaya_adversarial.arena.conflict_arena import ConflictArena
from nyaya_adversarial.arena.contradiction_cluster import (
    ConflictCluster,
    ContradictionClusterer,
)
from nyaya_adversarial.arena.hypothesis_manager import HypothesisManager

__all__ = [
    "ConflictArena",
    "ConflictCluster",
    "ContradictionClusterer",
    "HypothesisManager",
]
