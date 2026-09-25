"""Registry package for NYAYA-SATYA Evidence Foundation."""

from nyaya_evidence.registry.store import (
    EvidenceRegistry,
    EvidenceRegistryError,
    get_evidence_registry,
)

__all__ = [
    "EvidenceRegistry",
    "EvidenceRegistryError",
    "get_evidence_registry",
]
