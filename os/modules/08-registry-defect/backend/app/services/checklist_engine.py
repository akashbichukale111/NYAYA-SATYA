"""
Checklist Engine.

For each active Requirement in a filing package, determines whether the
package satisfies it, and — critically — records WHY. Matching is done
against actual document display names / kinds / attachment-reference
resolution; the engine never marks something FOUND without a concrete
document reference backing that determination.
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow
from app.core.enums import ChecklistItemStatus, RequirementType


def _find_matching_document(db: Session, filing_package_id: str, label: str | None, description: str):
    if not label:
        return None
    documents = db.query(models.Document).filter(
        models.Document.filing_package_id == filing_package_id,
        models.Document.status == "ACTIVE",
    ).all()
    label_norm = label.lower().replace(" ", "")
    for d in documents:
        if label_norm in (d.display_name or "").lower().replace(" ", ""):
            return d
        if label_norm in (d.document_kind or "").lower().replace(" ", ""):
            return d
    return None


def build_checklist(db: Session, *, case_id: str, filing_package_id: str) -> list[models.ChecklistItem]:
    # Every non-superseded/inactive requirement gets a checklist item —
    # including UNKNOWN-status ones, which must surface as
    # REQUIRES_HUMAN_REVIEW rather than silently vanish from the checklist.
    requirements = db.query(models.Requirement).filter(
        models.Requirement.filing_package_id == filing_package_id,
        models.Requirement.status.in_(["ACTIVE", "REQUIRES_VERIFICATION", "UNKNOWN"]),
    ).all()

    # Clear previous checklist items for this package to rebuild fresh
    # (idempotent recheck) — history remains in audit, not in the live
    # checklist table.
    db.query(models.ChecklistItem).filter(
        models.ChecklistItem.filing_package_id == filing_package_id
    ).delete()
    db.commit()

    items = []
    for req in requirements:
        status = ChecklistItemStatus.UNKNOWN.value
        explanation = "No matching evidence found; status could not be determined."
        document_refs = []
        evidence_refs = []
        verification = "UNVERIFIED"
        review_state = "NOT_REVIEWED"

        if req.status == "REQUIRES_VERIFICATION" or req.verification_status == "UNKNOWN":
            status = ChecklistItemStatus.REQUIRES_HUMAN_REVIEW.value
            explanation = "Requirement has no verified source; human verification is required before checklist status can be determined."
            review_state = "PENDING_REVIEW"

        elif req.requirement_type in (
            RequirementType.DOCUMENT_REQUIRED.value,
            RequirementType.ATTACHMENT_REQUIRED.value,
        ):
            match = _find_matching_document(db, filing_package_id, req.target_reference_label, req.description)
            if match:
                status = ChecklistItemStatus.FOUND.value
                explanation = f"Matched to document '{match.display_name}' present in the filing package."
                document_refs = [match.id]
                evidence_refs = [{"type": "document", "id": match.id, "name": match.display_name}]
                verification = "SYSTEM_DETECTED"
            else:
                # Also check resolved attachment references
                ref = db.query(models.AttachmentReference).filter(
                    models.AttachmentReference.filing_package_id == filing_package_id,
                    models.AttachmentReference.reference_label == req.target_reference_label,
                ).first()
                if ref and ref.resolved:
                    status = ChecklistItemStatus.FOUND.value
                    explanation = f"Reference '{ref.reference_label}' resolved to document {ref.resolved_document_id}."
                    document_refs = [ref.resolved_document_id]
                    verification = "SYSTEM_DETECTED"
                else:
                    status = ChecklistItemStatus.MISSING.value
                    explanation = (
                        f"No document in this filing package matches the required item "
                        f"'{req.target_reference_label or req.description}'."
                    )
                    verification = "SYSTEM_DETECTED"

        elif req.requirement_type == RequirementType.REFERENCE_REQUIRED.value:
            ref = db.query(models.AttachmentReference).filter(
                models.AttachmentReference.filing_package_id == filing_package_id,
                models.AttachmentReference.reference_label == req.target_reference_label,
            ).first()
            if ref and ref.resolved:
                status = ChecklistItemStatus.FOUND.value
                explanation = f"Reference '{ref.reference_label}' found and resolved."
                document_refs = [ref.resolved_document_id] if ref.resolved_document_id else []
            elif ref and not ref.resolved:
                status = ChecklistItemStatus.MISSING.value
                explanation = f"Reference '{ref.reference_label}' was found in a document but no matching attachment exists in the package."
            else:
                status = ChecklistItemStatus.UNVERIFIED.value
                explanation = "No reference to this item was detected in any document; cannot determine applicability."

        else:
            status = ChecklistItemStatus.REQUIRES_HUMAN_REVIEW.value
            explanation = f"Requirement type '{req.requirement_type}' requires manual determination in this build."
            review_state = "PENDING_REVIEW"

        item = models.ChecklistItem(
            id=new_id("chk"),
            case_id=case_id,
            filing_package_id=filing_package_id,
            requirement_id=req.id,
            status=status,
            source=req.source,
            document_refs=document_refs,
            evidence_refs=evidence_refs,
            verification=verification,
            review_state=review_state,
            explanation=explanation,
            updated_at=utcnow().isoformat(),
        )
        db.add(item)
        items.append(item)

    db.commit()
    for item in items:
        db.refresh(item)
    return items
