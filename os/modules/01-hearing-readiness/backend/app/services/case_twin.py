"""
Case Digital Twin (section 3). This is the ONLY place that creates
Document/Evidence rows from an upload, so every other module (agents,
API routes) reads/writes case state through here rather than keeping
its own copy, per the spec's explicit warning against duplicating state.
"""
from __future__ import annotations

import uuid

from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.hearing import Hearing
from app.models.requirement import Requirement
from app.models.blocker import Blocker
from app.services import ingestion, security, audit_service, hearing_context

DOC_CATEGORY_KEYWORDS = {
    "order": ["order dated", "it is hereby ordered", "the court orders"],
    "application": ["application under section", "i.a. no", "interlocutory application"],
    "affidavit": ["affidavit of", "i, the undersigned, solemnly affirm"],
    "notice": ["notice is hereby given", "cause list"],
}


def guess_doc_category(text: str) -> str | None:
    low = (text or "").lower()
    for category, phrases in DOC_CATEGORY_KEYWORDS.items():
        if any(p in low for p in phrases):
            return category
    return None


def create_case(db, title: str, case_type: str, parties: list[dict], is_synthetic: bool = True) -> Case:
    case = Case(title=title, case_type=case_type, parties=parties,
                is_synthetic="true" if is_synthetic else "false")
    db.add(case)
    db.flush()
    audit_service.log_event(
        db, case_id=case.id, actor="system", event_type="CASE_CREATED", action="create_case",
        input_ref={"title": title}, result={"case_id": case.id}, correlation_id=uuid.uuid4().hex[:12],
    )
    return case


def ingest_document(db, case_id: str, filename: str, raw: bytes) -> Document:
    ext = security.validate_upload(filename, len(raw))
    stored_name, full_path = security.safe_stored_path(ext)
    full_path.write_bytes(raw)

    extraction = ingestion.extract(ext, raw)
    injection_hits = security.scan_for_injection(extraction.text)
    category = guess_doc_category(extraction.text)

    doc = Document(
        case_id=case_id,
        original_filename=filename,
        stored_filename=stored_name,
        file_type=ext.lstrip("."),
        size_bytes=len(raw),
        content_hash=security.content_hash(raw),
        extraction_method=extraction.method,
        extraction_status=extraction.status,
        extracted_text=extraction.text,
        extracted_sections=extraction.sections,
        doc_category=category,
        injection_flag="true" if injection_hits else "false",
        injection_notes=injection_hits,
    )
    db.add(doc)
    db.flush()

    # Every ingested document also becomes a trackable evidence item so it
    # can be linked to readiness requirements -- but it starts UNVERIFIED;
    # only a human/verification step can promote it, we never assume.
    evidence = Evidence(
        case_id=case_id, document_id=doc.id, label=f"Document: {filename}",
        evidence_type="document",
        availability="AVAILABLE" if extraction.status in ("OK", "PARTIAL") else "UNKNOWN",
        verification_state="UNVERIFIED",
        confidence="MEDIUM" if extraction.status == "OK" else "LOW",
        notes=["Auto-created from document ingestion."],
    )
    db.add(evidence)
    db.flush()

    audit_service.log_event(
        db, case_id=case_id, actor="system", event_type="DOCUMENT_INGESTED", action="ingest_document",
        input_ref={"filename": filename, "content_hash": doc.content_hash},
        result={"document_id": doc.id, "extraction_status": extraction.status,
                "injection_flag": doc.injection_flag},
        correlation_id=uuid.uuid4().hex[:12],
    )
    return doc


def refresh_hearing_context(db, case_id: str) -> Hearing | None:
    hearing = db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    if hearing is None:
        return None
    if hearing.purpose:  # explicit fixture / already-determined purpose: don't override
        return hearing

    docs = db.query(Document).filter(Document.case_id == case_id).all()
    purpose, status, reasons = hearing_context.determine_purpose(
        [d.extracted_text for d in docs], fixture_purpose=None
    )
    hearing.purpose = purpose
    hearing.purpose_status = status
    hearing.uncertainty_reasons = reasons
    db.flush()
    return hearing


def get_case_full(db, case_id: str) -> dict | None:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return None
    return {
        "case": case.to_dict(),
        "documents": [d.to_dict() for d in db.query(Document).filter(Document.case_id == case_id).all()],
        "evidence": [e.to_dict() for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()],
        "hearings": [h.to_dict() for h in db.query(Hearing).filter(Hearing.case_id == case_id).all()],
        "requirements": [r.to_dict() for r in db.query(Requirement).filter(Requirement.case_id == case_id).all()],
        "blockers": [b.to_dict() for b in db.query(Blocker).filter(Blocker.case_id == case_id).all()],
    }
