"""Evidence Registry and Storage Repository for NYAYA-SATYA.

Maintains immutable records of Cases, EvidenceItems, Raw Artifacts,
Parsed Documents, and Sanitization Results.
Enforces content-addressed duplicate detection to prevent duplicate evidence
from fabricating independent provenance.
"""

from __future__ import annotations

import threading
from typing import Any

from nyaya_evidence.contracts.case import Case
from nyaya_evidence.contracts.evidence import (
    EvidenceArtifact,
    EvidenceItem,
    EvidenceStatus,
)
from nyaya_evidence.parsers.base import ParsedDocument
from nyaya_evidence.sanitization.sanitizer import SanitizationResult
from tarka_vyuh.contracts.provenance import ProvenanceRef


class EvidenceRegistryError(ValueError):
    """Raised on registry conflicts or validation failures."""


class EvidenceRegistry:
    """Thread-safe content-addressed registry for evidence and cases."""

    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}
        self._evidence: dict[str, EvidenceItem] = {}
        self._case_evidence: dict[str, list[str]] = {}
        self._artifacts: dict[str, EvidenceArtifact] = {}
        self._provenance: dict[str, list[ProvenanceRef]] = {}
        self._sanitizations: dict[str, SanitizationResult] = {}
        self._parsed_documents: dict[str, ParsedDocument] = {}
        self._hash_to_evidence_id: dict[str, str] = {}  # For duplicate detection
        self._lock = threading.Lock()

    # ---- Cases ----
    def register_case(self, case: Case) -> Case:
        with self._lock:
            if case.case_id in self._cases:
                raise EvidenceRegistryError(f"Case {case.case_id} already exists")
            self._cases[case.case_id] = case
            self._case_evidence.setdefault(case.case_id, [])
            return case

    def get_case(self, case_id: str) -> Case | None:
        with self._lock:
            return self._cases.get(case_id)

    def list_cases(self) -> list[Case]:
        with self._lock:
            return list(self._cases.values())

    # ---- Evidence Registration & Duplicate Detection ----
    def register_evidence(
        self,
        item: EvidenceItem,
        artifact: EvidenceArtifact,
        provenance: ProvenanceRef,
    ) -> EvidenceItem:
        """Registers evidence item and artifact with content-addressed duplicate detection."""
        with self._lock:
            if item.case_id not in self._cases:
                raise EvidenceRegistryError(f"Cannot register evidence for non-existent case {item.case_id}")

            if item.evidence_id in self._evidence:
                raise EvidenceRegistryError(f"Evidence {item.evidence_id} already exists")

            # Duplicate content detection
            existing_id = self._hash_to_evidence_id.get(item.content_hash)
            if existing_id is not None:
                # Mark as duplicate; does NOT create false independent provenance
                item.duplicate_of_id = existing_id
                item.metadata["duplicate_detection"] = {
                    "original_evidence_id": existing_id,
                    "content_hash": item.content_hash,
                    "note": "Identical bytes to previously registered evidence; shares provenance source",
                }
            else:
                self._hash_to_evidence_id[item.content_hash] = item.evidence_id

            self._evidence[item.evidence_id] = item
            self._case_evidence[item.case_id].append(item.evidence_id)
            self._artifacts[item.evidence_id] = artifact
            self._provenance.setdefault(item.evidence_id, []).append(provenance)

            return item

    def get_evidence(self, evidence_id: str) -> EvidenceItem | None:
        with self._lock:
            return self._evidence.get(evidence_id)

    def list_case_evidence(self, case_id: str) -> list[EvidenceItem]:
        with self._lock:
            eids = self._case_evidence.get(case_id, [])
            return [self._evidence[eid] for eid in eids if eid in self._evidence]

    def get_artifact(self, evidence_id: str) -> EvidenceArtifact | None:
        with self._lock:
            return self._artifacts.get(evidence_id)

    # ---- Provenance DNA ----
    def record_provenance(self, evidence_id: str, ref: ProvenanceRef) -> None:
        with self._lock:
            self._provenance.setdefault(evidence_id, []).append(ref)

    def get_provenance(self, evidence_id: str) -> list[ProvenanceRef]:
        with self._lock:
            return list(self._provenance.get(evidence_id, []))

    # ---- Sanitization & Parsing Results ----
    def record_sanitization(self, evidence_id: str, result: SanitizationResult) -> None:
        with self._lock:
            self._sanitizations[evidence_id] = result

    def get_sanitization(self, evidence_id: str) -> SanitizationResult | None:
        with self._lock:
            return self._sanitizations.get(evidence_id)

    def record_parsed_document(self, evidence_id: str, parsed: ParsedDocument) -> None:
        with self._lock:
            self._parsed_documents[evidence_id] = parsed

    def get_parsed_document(self, evidence_id: str) -> ParsedDocument | None:
        with self._lock:
            return self._parsed_documents.get(evidence_id)

    def reset_for_test(self) -> None:
        with self._lock:
            self._cases.clear()
            self._evidence.clear()
            self._case_evidence.clear()
            self._artifacts.clear()
            self._provenance.clear()
            self._sanitizations.clear()
            self._parsed_documents.clear()
            self._hash_to_evidence_id.clear()


# Default singleton instance
_GLOBAL_EVIDENCE_REGISTRY = EvidenceRegistry()


def get_evidence_registry() -> EvidenceRegistry:
    return _GLOBAL_EVIDENCE_REGISTRY


__all__ = [
    "EvidenceRegistry",
    "EvidenceRegistryError",
    "get_evidence_registry",
]
