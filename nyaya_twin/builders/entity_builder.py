"""Entity Builder for NYAYA-SATYA Case Digital Twin.

Manages entity registration, deduplication, and resolution without assuming identity without proof.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from nyaya_twin.contracts.entities import (
    Entity,
    EntityResolutionType,
    EntityStatus,
    EntityType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef


class EntityBuilder:
    """Builder for resolving and instantiating case entities."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self._entities: dict[str, Entity] = {}

    def add_entity(
        self,
        *,
        canonical_label: str,
        entity_type: EntityType = EntityType.PERSON,
        entity_id: str | None = None,
        aliases: list[str] | None = None,
        source_evidence_ids: list[str] | None = None,
        provenance_refs: list[ProvenanceRef] | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        status: EntityStatus = EntityStatus.POSSIBLE_MATCH,
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """Registers a new entity or updates aliases if already registered."""
        if entity_id is None:
            clean_label = re.sub(r"[^a-zA-Z0-9]+", "_", canonical_label.strip()).strip("_").lower()
            entity_id = f"ent_{clean_label}_{uuid.uuid4().hex[:6]}"

        entity = Entity(
            entity_id=entity_id,
            case_id=self.case_id,
            entity_type=entity_type,
            canonical_label=canonical_label.strip(),
            aliases=list(aliases or []),
            source_evidence_ids=list(source_evidence_ids or []),
            provenance_refs=list(provenance_refs or []),
            confidence=confidence,
            status=status,
            metadata=dict(metadata or {}),
        )
        self._entities[entity.entity_id] = entity
        return entity

    def resolve_label(self, label: str) -> tuple[Entity | None, EntityResolutionType]:
        """Resolves a label against registered entities."""
        best_entity: Entity | None = None
        best_type = EntityResolutionType.UNRESOLVED

        for entity in self._entities.values():
            match_type = entity.matches_label(label)
            if match_type is EntityResolutionType.EXACT_MATCH:
                return entity, match_type
            elif match_type is EntityResolutionType.ALIAS_MATCH:
                best_entity = entity
                best_type = match_type
            elif match_type is EntityResolutionType.POSSIBLE_MATCH and best_type is EntityResolutionType.UNRESOLVED:
                best_entity = entity
                best_type = match_type

        return best_entity, best_type

    def get_entities(self) -> dict[str, Entity]:
        return dict(self._entities)
