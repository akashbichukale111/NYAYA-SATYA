"""Safe Evidence Reference Adapter for TARKA-VYUH Integration.

Ensures TARKA-VYUH reasoning engines consume ONLY sanitized, provenance-tracked evidence.
Quarantined or hostile evidence is structurally rejected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_evidence.contracts.evidence import EvidenceItem, EvidenceStatus
from nyaya_evidence.parsers.base import ExtractionMetadata, ParsedDocument
from nyaya_evidence.quarantine.manager import QuarantineViolationError
from nyaya_evidence.sanitization.sanitizer import RiskLevel, SanitizationResult
from tarka_vyuh.contracts.provenance import ProvenanceRef


@dataclass(frozen=True)
class SafeEvidenceRef:
    """A safe, quarantined-cleared evidence bundle prepared for TARKA-VYUH reasoning."""

    evidence_id: str
    case_id: str
    sanitized_text: str
    content_hash: str  # Original SHA-256
    sanitized_hash: str
    provenance_refs: tuple[ProvenanceRef, ...]
    sanitization_status: str
    risk_level: RiskLevel
    extraction_metadata: dict[str, Any]
    prepared_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk_level"] = self.risk_level.value
        data["prepared_at"] = self.prepared_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data


def create_safe_evidence_ref(
    *,
    item: EvidenceItem,
    sanitization: SanitizationResult | None,
    parsed: ParsedDocument | None,
    provenance_refs: list[ProvenanceRef],
) -> SafeEvidenceRef:
    """Validates that evidence has cleared quarantine and creates a SafeEvidenceRef."""
    if not item.is_safe_for_reasoning:
        raise QuarantineViolationError(
            f"Cannot create SafeEvidenceRef: evidence {item.evidence_id} is in status {item.status.value}. "
            "Evidence must be REGISTERED or PARSED to enter reasoning."
        )

    if sanitization is None:
        raise QuarantineViolationError(f"Evidence {item.evidence_id} has no sanitization record; access blocked.")

    if sanitization.risk_level is RiskLevel.BLOCKED:
        raise QuarantineViolationError(f"Evidence {item.evidence_id} is BLOCKED by adversarial security scanner.")

    # Use sanitized text rather than raw text
    text_content = sanitization.sanitized_content
    extraction_meta = parsed.metadata.to_dict() if parsed else {}

    return SafeEvidenceRef(
        evidence_id=item.evidence_id,
        case_id=item.case_id,
        sanitized_text=text_content,
        content_hash=item.content_hash,
        sanitized_hash=sanitization.sanitized_hash,
        provenance_refs=tuple(provenance_refs),
        sanitization_status=sanitization.status,
        risk_level=sanitization.risk_level,
        extraction_metadata=extraction_meta,
        prepared_at=datetime.now(UTC),
    )


__all__ = [
    "SafeEvidenceRef",
    "create_safe_evidence_ref",
]
