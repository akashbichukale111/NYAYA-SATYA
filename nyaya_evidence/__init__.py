"""NYAYA-SATYA Evidence Foundation.

Handles Case Ingestion, Evidence Quarantine, SHA-256 Hashing, Provenance DNA,
Document Parsing (TXT, PDF, DOCX, JSON, CSV), Adversarial Sanitization,
Evidence Registry, Safe TARKA References, and First Contradiction Analysis Foundation.
"""

from nyaya_evidence.contracts.case import Case
from nyaya_evidence.contracts.evidence import (
    EvidenceArtifact,
    EvidenceItem,
    EvidenceSource,
    EvidenceStatus,
    MediaType,
)
from nyaya_evidence.contradiction.engine import (
    ContradictionAnalysisEngine,
    ContradictionCandidate,
    ContradictionType,
)
from nyaya_evidence.ingestion.ingest import (
    MAX_EVIDENCE_SIZE_BYTES,
    EvidenceIngestionError,
    detect_media_type,
    ingest_evidence,
    sanitize_filename,
)
from nyaya_evidence.parsers.base import (
    BaseDocumentParser,
    DocumentParserError,
    ExtractionMetadata,
    ParsedDocument,
    ParsedPage,
)
from nyaya_evidence.parsers.dispatcher import DocumentParserDispatcher
from nyaya_evidence.quarantine.manager import (
    QuarantineManager,
    QuarantineViolationError,
)
from nyaya_evidence.registry.store import (
    EvidenceRegistry,
    EvidenceRegistryError,
    get_evidence_registry,
)
from nyaya_evidence.sanitization.sanitizer import (
    AdversarialSanitizer,
    RiskLevel,
    SanitizationResult,
)
from nyaya_evidence.tarka_integration.safe_refs import (
    SafeEvidenceRef,
    create_safe_evidence_ref,
)

__all__ = [
    "AdversarialSanitizer",
    "BaseDocumentParser",
    "Case",
    "ContradictionAnalysisEngine",
    "ContradictionCandidate",
    "ContradictionType",
    "DocumentParserDispatcher",
    "DocumentParserError",
    "EvidenceArtifact",
    "EvidenceIngestionError",
    "EvidenceItem",
    "EvidenceRegistry",
    "EvidenceRegistryError",
    "EvidenceSource",
    "EvidenceStatus",
    "ExtractionMetadata",
    "MAX_EVIDENCE_SIZE_BYTES",
    "MediaType",
    "ParsedDocument",
    "ParsedPage",
    "QuarantineManager",
    "QuarantineViolationError",
    "RiskLevel",
    "SafeEvidenceRef",
    "SanitizationResult",
    "create_safe_evidence_ref",
    "detect_media_type",
    "get_evidence_registry",
    "ingest_evidence",
    "sanitize_filename",
]
