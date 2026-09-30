"""
Attachment Reference Engine.

Extracts references to named attachments (Annexure X, Exhibit N,
Schedule Y, etc.) from a document's extracted text and checks whether
a document with a matching label exists elsewhere in the same filing
package. Never fabricates a page/location — location is only ever
carried over from the DocumentSection where the phrase was actually
found (which itself only claims a location when the parser determined
one).
"""
import re
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow

REFERENCE_PATTERNS = [
    (re.compile(r"\bAnnexure\s+([A-Z0-9]+)\b", re.IGNORECASE), "ANNEXURE"),
    (re.compile(r"\bExhibit\s+([A-Z0-9]+)\b", re.IGNORECASE), "EXHIBIT"),
    (re.compile(r"\bSchedule\s+([A-Z0-9]+)\b", re.IGNORECASE), "SCHEDULE"),
    (re.compile(r"\bAppendix\s+([A-Z0-9]+)\b", re.IGNORECASE), "APPENDIX"),
    (re.compile(r"\bAttachment\s+([A-Z0-9]+)\b", re.IGNORECASE), "ATTACHMENT"),
]


def extract_references(text: str) -> list[dict]:
    """Return a de-duplicated list of {label, reference_type, context} for
    every named-attachment reference found in `text`."""
    found = {}
    for pattern, ref_type in REFERENCE_PATTERNS:
        for match in pattern.finditer(text or ""):
            label = f"{ref_type.title()} {match.group(1).upper()}"
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            context = text[start:end].strip()
            key = (ref_type, match.group(1).upper())
            if key not in found:
                found[key] = {"label": label, "reference_type": ref_type, "context": context}
    return list(found.values())


def detect_and_store_references(
    db: Session,
    *,
    case_id: str,
    filing_package_id: str,
    document_version: models.DocumentVersion,
) -> list[models.AttachmentReference]:
    refs = extract_references(document_version.extracted_text or "")
    stored = []
    # find a section that actually contains the label text, to keep the
    # location claim honest; fall back to "location unknown".
    sections = db.query(models.DocumentSection).filter(
        models.DocumentSection.document_version_id == document_version.id
    ).all()

    for ref in refs:
        matching_section = next(
            (s for s in sections if ref["label"].split()[0].lower() in (s.text_excerpt or "").lower()
             and ref["label"].split()[1].lower() in (s.text_excerpt or "").lower()),
            None,
        )
        record = models.AttachmentReference(
            id=new_id("aref"),
            case_id=case_id,
            filing_package_id=filing_package_id,
            source_document_version_id=document_version.id,
            reference_label=ref["label"],
            reference_type=ref["reference_type"],
            raw_context=ref["context"],
            section_id=matching_section.id if matching_section else None,
            location_known=bool(matching_section and matching_section.location_known),
            resolved=False,
            created_at=utcnow().isoformat(),
        )
        db.add(record)
        stored.append(record)
    db.commit()
    for r in stored:
        db.refresh(r)
    return stored


def resolve_references(db: Session, *, filing_package_id: str) -> None:
    """Attempt to resolve each unresolved attachment reference against
    documents currently in the package, matching on display_name or
    document_kind containing the reference label. Never resolves against
    documents outside this package (case isolation + package scope)."""
    refs = db.query(models.AttachmentReference).filter(
        models.AttachmentReference.filing_package_id == filing_package_id,
        models.AttachmentReference.resolved == False,  # noqa: E712
    ).all()
    documents = db.query(models.Document).filter(
        models.Document.filing_package_id == filing_package_id,
        models.Document.status == "ACTIVE",
    ).all()

    for ref in refs:
        label_norm = ref.reference_label.lower().replace(" ", "")
        match = next(
            (d for d in documents if label_norm in (d.display_name or "").lower().replace(" ", "")
             or label_norm in (d.document_kind or "").lower().replace(" ", "")),
            None,
        )
        if match:
            ref.resolved = True
            ref.resolved_document_id = match.id
    db.commit()
