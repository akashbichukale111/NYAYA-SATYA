"""Impact classification for blast-radius effects.

Classifies changed nodes into effect categories.
"""

from __future__ import annotations

from nyaya_causal.contracts.effect import CausalEffect, EffectType


class ImpactClassifier:
    """Classifies the structural impact type of a changed node."""

    def classify(
        self,
        node_id: str,
        node_type: str,
        original_state: str,
        new_state: str,
        is_direct: bool,
    ) -> CausalEffect:
        """Classify a single node's change."""
        if original_state == new_state:
            return CausalEffect(
                node_id=node_id,
                node_type=node_type,
                effect_type=EffectType.UNCHANGED,
                original_state=original_state,
                new_state=new_state,
            )

        # Determine effect type based on state transitions
        if new_state in ("UNSUPPORTED", "UNRESOLVED"):
            effect_type = EffectType.UNSUPPORTED if new_state == "UNSUPPORTED" else EffectType.NEW_UNRESOLVED
        elif new_state == "CONTRADICTED":
            effect_type = EffectType.NEW_CONTRADICTION
        elif new_state == "SUPPORTED" and original_state == "CONTRADICTED":
            effect_type = EffectType.RESOLVED_CONTRADICTION
        elif is_direct:
            effect_type = EffectType.DIRECT_EFFECT
        else:
            effect_type = EffectType.INDIRECT_EFFECT

        return CausalEffect(
            node_id=node_id,
            node_type=node_type,
            effect_type=effect_type,
            original_state=original_state,
            new_state=new_state,
            description=f"{node_type} {node_id} changed from {original_state} to {new_state}",
        )
