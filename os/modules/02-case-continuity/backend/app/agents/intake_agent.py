"""
Intake Agent (section 25 #1).

Responsibility: take a raw uploaded artifact, validate + hash + store it
safely, and record the DOCUMENT_UPLOADED event. This is the only agent
allowed to touch the filesystem.
"""
from sqlalchemy.orm import Session

from app.models import Document, Event, EventType
from app.security import validate_upload, safe_store_path, sha256_of_bytes, detect_prompt_injection
from app.agents.base import run_agent


def intake_document(
    db: Session, *, case_id: str, filename: str, content: bytes, doc_type_hint: str,
    correlation_id: str, actor: str = "user", is_demo_data: bool = False,
) -> tuple[Document, Event]:
    with run_agent(db, case_id=case_id, agent_name="IntakeAgent", correlation_id=correlation_id,
                    input_summary=f"filename={filename} size={len(content)}") as result:
        safe_name = validate_upload(filename, len(content))
        digest = sha256_of_bytes(content)
        try:
            text_preview = content.decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            text_preview = ""
        flagged = detect_prompt_injection(text_preview)

        path = safe_store_path(case_id, safe_name)
        with open(path, "wb") as f:
            f.write(content)

        doc = Document(
            case_id=case_id, filename=safe_name, doc_type=doc_type_hint or "unclassified",
            stored_path=path, sha256=digest, size_bytes=len(content),
            extracted_text_preview=text_preview[:1000],
            prompt_injection_flagged=flagged, is_demo_data=is_demo_data,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        event = Event(
            case_id=case_id, event_type=EventType.DOCUMENT_UPLOADED.value,
            source=doc.id, actor=actor,
            description=f"Document '{safe_name}' uploaded" + (" (DEMO DATA)" if is_demo_data else ""),
            structured_payload={"document_id": doc.id, "sha256": digest, "prompt_injection_flagged": flagged},
            confidence=1.0,
            provenance={"document_id": doc.id},
            correlation_id=correlation_id,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        result["output_summary"] = f"document_id={doc.id} flagged={flagged}"
        return doc, event
