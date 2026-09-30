"""
Event Extraction Agent (section 25 #2).

Reads a Document's extracted text (already sanitized/truncated by the
security layer) and produces a structured EXTRACTION event. It never writes
to case-domain tables (Deadline, Obligation, ...) directly - it only records
what it observed, with confidence + provenance, as an AGENT_ACTION event.
The Change Detection Agent decides what, if anything, that observation
should change.
"""
from sqlalchemy.orm import Session

from app.models import Document, Event, EventType
from app.llm_provider import get_provider
from app.security import sanitize_for_prompt
from app.agents.base import run_agent


def extract_events_from_document(
    db: Session, *, case_id: str, document: Document, correlation_id: str,
) -> Event:
    with run_agent(db, case_id=case_id, agent_name="EventExtractionAgent", correlation_id=correlation_id,
                    input_summary=f"document_id={document.id}") as result:
        provider = get_provider()
        # Document content is treated as untrusted DATA at every step, per
        # security.sanitize_for_prompt - it is never allowed to alter agent behavior.
        sanitized = sanitize_for_prompt(document.extracted_text_preview or "")
        facts = provider.extract_candidate_facts(sanitized, doc_type_hint=document.doc_type)

        event = Event(
            case_id=case_id,
            event_type=EventType.AGENT_ACTION.value,
            source=document.id,
            actor="EventExtractionAgent",
            description=f"Extracted candidate facts from '{document.filename}'.",
            structured_payload={"extraction": facts, "document_id": document.id},
            confidence=float(facts.get("confidence", 0.5)),
            provenance={"document_id": document.id, "agent": "EventExtractionAgent"},
            correlation_id=correlation_id,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        result["output_summary"] = f"doc_type_guess={facts.get('doc_type_guess')} conf={facts.get('confidence')}"
        return event
