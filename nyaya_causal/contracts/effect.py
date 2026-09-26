"""Effect classification contracts for NYAYA-SATYA.

Classifies the structural impact of interventions on case graph nodes.
Never calls effects 'legal consequences' unless explicitly a structural case-state consequence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EffectType(str, Enum):
    DIRECT_EFFECT = "DIRECT_EFFECT"
    INDIRECT_EFFECT = "INDIRECT_EFFECT"
    NEW_CONTRADICTION = "NEW_CONTRADICTION"
    RESOLVED_CONTRADICTION = "RESOLVED_CONTRADICTION"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NEW_UNRESOLVED = "NEW_UNRESOLVED"
    UNCHANGED = "UNCHANGED"
    DEPENDENCY_BROKEN = "DEPENDENCY_BROKEN"
    DEPENDENCY_PRESERVED = "DEPENDENCY_PRESERVED"


@dataclass
class CausalEffect:
    """A classified effect resulting from an intervention."""

    node_id: str
    node_type: str
    effect_type: EffectType
    original_state: str = ""
    new_state: str = ""
    description: str = ""
    path_from_intervention: list[str] = field(default_factory=list)
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["effect_type"] = self.effect_type.value
        return data
