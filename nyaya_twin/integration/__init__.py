"""Integration layer for NYAYA-SATYA Case Digital Twin."""

from __future__ import annotations

from nyaya_twin.integration.evidence_adapter import CaseTwinEvidenceAdapter
from nyaya_twin.integration.tarka_adapter import CaseTwinTarkaAdapter

__all__ = [
    "CaseTwinEvidenceAdapter",
    "CaseTwinTarkaAdapter",
]
