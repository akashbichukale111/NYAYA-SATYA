"""
Defect Impact Analysis.

For a single defect, answers: what does this affect? Traces outward
from the defect through its own recorded references (requirement_refs,
document_refs, source_refs) plus anything in the same filing package
that references this defect back (checklist items tied to the same
requirement, other defects sharing a document, corrections targeting
it). This is a read-only traversal of existing rows — it never infers a
relationship that isn't already stored, and it never states a legal
consequence (no "will be rejected" / "is invalid" language anywhere in
this module, matching defect_engine.py's templates).
"""
from sqlalchemy.orm import Session
from app import models


def analyze_defect_impact(db: Session, *, defect_id: str) -> dict:
    defect = db.query(models.Defect).filter(models.Defect.id == defect_id).first()
    if not defect:
        return {"defect_id": defect_id, "found": False}

    affected_requirements = []
    for req_id in (defect.requirement_refs or []):
        req = db.query(models.Requirement).filter(models.Requirement.id == req_id).first()
        if req:
            affected_requirements.append({"id": req.id, "description": req.description, "status": req.status})

    affected_documents = []
    for doc_id in (defect.document_refs or []):
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if doc:
            affected_documents.append({"id": doc.id, "display_name": doc.display_name, "status": doc.status})

    affected_checklist_items = []
    if defect.requirement_refs:
        items = db.query(models.ChecklistItem).filter(
            models.ChecklistItem.requirement_id.in_(defect.requirement_refs)
        ).all()
        affected_checklist_items = [{"id": i.id, "status": i.status, "explanation": i.explanation} for i in items]

    # Other defects that share a document or requirement reference with
    # this one — a real, traceable relationship, not an inferred causal
    # link.
    related_defects = []
    sibling_defects = db.query(models.Defect).filter(
        models.Defect.filing_package_id == defect.filing_package_id,
        models.Defect.id != defect.id,
    ).all()
    doc_set = set(defect.document_refs or [])
    req_set = set(defect.requirement_refs or [])
    for other in sibling_defects:
        shares_doc = doc_set.intersection(other.document_refs or [])
        shares_req = req_set.intersection(other.requirement_refs or [])
        if shares_doc or shares_req:
            related_defects.append({
                "id": other.id, "defect_type": other.defect_type, "status": other.status,
                "shared_via": "document" if shares_doc else "requirement",
            })

    corrections = db.query(models.CorrectionRequest).filter(
        models.CorrectionRequest.defect_id == defect.id
    ).all()
    affected_corrections = [{"id": c.id, "status": c.status, "description": c.description} for c in corrections]

    objection = None
    linked_obj = db.query(models.RegistryObjection).filter(
        models.RegistryObjection.linked_defect_id == defect.id
    ).first()
    if linked_obj:
        objection = {"id": linked_obj.id, "status": linked_obj.status}

    # Affected workflow step: which lifecycle stage this defect currently
    # blocks/gates, expressed as the package's own recorded lifecycle
    # state — never a prediction of a future stage.
    package = db.query(models.FilingPackage).filter(models.FilingPackage.id == defect.filing_package_id).first()

    return {
        "defect_id": defect.id,
        "found": True,
        "defect_type": defect.defect_type,
        "severity": defect.severity,
        "status": defect.status,
        "affected_requirements": affected_requirements,
        "affected_documents": affected_documents,
        "affected_checklist_items": affected_checklist_items,
        "related_defects": related_defects,
        "affected_corrections": affected_corrections,
        "linked_objection": objection,
        "current_workflow_state": package.lifecycle_state if package else None,
        "human_review_required": defect.human_review_required,
        "note": (
            "This is a structural trace of recorded references, not a prediction of what a "
            "registry or court will do. It does not determine legal validity or filing acceptance."
        ),
    }
