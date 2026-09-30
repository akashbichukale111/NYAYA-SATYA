"""
Evidence Extraction Agent.

Parses a document (via document_service) and creates EvidenceItem
candidates from the LLMProvider's extracted excerpts. Every excerpt is
a verbatim substring of the real parsed text -- never fabricated. Real
page numbers are preserved when the source format provides them (PDF);
otherwise source_location_known stays False and the item must render
as SOURCE_LOCATION_UNKNOWN downstream.

Creation of new, UNVERIFIED evidence candidates is additive and
non-destructive (it modifies no existing verified data), so this agent
writes directly rather than going through the Human Legal Gate. Every
write is still audited.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import Document, EvidenceItem
from app.models.enums import EvidenceState, VerificationStatus
from app.core.llm_provider import get_llm_provider
from app.services.document_service import parse_document
from app.services.time_machine_service import snapshot_evidence
from app.services.review_service import log_audit_event


def extract_evidence(db: Session, document_id: str, actor_id: str = "ExtractionAgent") -> Dict:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return {"ok": False, "reason": "Document not found.", "evidence_ids": []}

    full_text, page_chunks = parse_document(doc)
    provider = get_llm_provider()

    created_ids: List[str] = []
    for chunk in page_chunks:
        candidates = provider.extract_evidence_candidates(chunk["text"])
        for cand in candidates:
            source_text = cand["source_text"]
            # Anti-fabrication contract: the excerpt must actually appear in
            # the parsed chunk text.
            if source_text not in chunk["text"]:
                continue
            page_number = chunk.get("page_number")
            item = EvidenceItem(
                case_id=doc.case_id,
                document_id=doc.id,
                label=source_text[:80],
                source_text=source_text,
                page_number=page_number,
                section=None,
                source_location_known=page_number is not None,
                extraction_method=f"AGENT_EXTRACTED:{provider.name}",
                state=EvidenceState.UNKNOWN.value,
                verification_status=VerificationStatus.REQUIRES_HUMAN_REVIEW.value,
            )
            db.add(item)
            db.flush()
            snapshot_evidence(db, item, reason="AGENT_EXTRACTED")
            created_ids.append(item.id)

    log_audit_event(
        db, doc.case_id, actor="EvidenceExtractionAgent", actor_type="AGENT",
        action="EVIDENCE_EXTRACTED", target_type="DOCUMENT", target_id=doc.id,
        detail={"evidence_ids": created_ids, "count": len(created_ids)},
    )
    doc.status = "PROCESSED"
    db.commit()
    return {"ok": True, "document_id": doc.id, "evidence_ids": created_ids}
