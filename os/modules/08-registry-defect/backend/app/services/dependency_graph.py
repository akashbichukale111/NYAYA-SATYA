"""
Defect Dependency Graph.

Builds the graph described in the spec:

    Requirement -> Checklist Item -> Document -> Attachment -> Defect ->
    Correction -> Verification

plus the additional edge kinds: Document->Document (supersession),
Document->Requirement (satisfies), Objection->Defect, Defect->Defect
(not currently inferred — reserved), Correction->Defect,
Requirement->Requirement (not currently inferred — reserved).

Output shape is deliberately simple ({nodes, edges}) so the frontend can
feed it straight to React Flow (@xyflow/react) without transformation.
Every node/edge here is derived directly from rows that already exist —
nothing is synthesized or inferred beyond direct foreign-key/reference
relationships already stored in the database.
"""
from sqlalchemy.orm import Session
from app import models


def _node(node_id: str, kind: str, label: str, **extra) -> dict:
    return {"id": node_id, "kind": kind, "label": label, **extra}


def _edge(source: str, target: str, kind: str) -> dict:
    return {"source": source, "target": target, "kind": kind}


def build_dependency_graph(db: Session, *, filing_package_id: str) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()

    def add_node(node_id: str, kind: str, label: str, **extra):
        if node_id not in seen_nodes:
            nodes.append(_node(node_id, kind, label, **extra))
            seen_nodes.add(node_id)

    requirements = db.query(models.Requirement).filter(
        models.Requirement.filing_package_id == filing_package_id
    ).all()
    for r in requirements:
        add_node(r.id, "REQUIREMENT", r.description[:60], status=r.status)

    checklist_items = db.query(models.ChecklistItem).filter(
        models.ChecklistItem.filing_package_id == filing_package_id
    ).all()
    for item in checklist_items:
        add_node(item.id, "CHECKLIST_ITEM", item.status, status=item.status)
        if item.requirement_id in seen_nodes:
            edges.append(_edge(item.requirement_id, item.id, "REQUIREMENT_TO_CHECKLIST"))
        for doc_id in (item.document_refs or []):
            add_node(doc_id, "DOCUMENT", doc_id[:16])
            edges.append(_edge(item.id, doc_id, "CHECKLIST_TO_DOCUMENT"))

    documents = db.query(models.Document).filter(
        models.Document.filing_package_id == filing_package_id
    ).all()
    for d in documents:
        add_node(d.id, "DOCUMENT", d.display_name, status=d.status)

    attachment_refs = db.query(models.AttachmentReference).filter(
        models.AttachmentReference.filing_package_id == filing_package_id
    ).all()
    for ref in attachment_refs:
        add_node(ref.id, "ATTACHMENT", ref.reference_label, resolved=ref.resolved)
        # Document -> Attachment (the document that mentions it)
        source_doc = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.id == ref.source_document_version_id
        ).first()
        if source_doc:
            add_node(source_doc.document_id, "DOCUMENT", source_doc.document_id[:16])
            edges.append(_edge(source_doc.document_id, ref.id, "DOCUMENT_TO_ATTACHMENT"))
        if ref.resolved and ref.resolved_document_id:
            edges.append(_edge(ref.id, ref.resolved_document_id, "ATTACHMENT_RESOLVED_TO_DOCUMENT"))

    defects = db.query(models.Defect).filter(
        models.Defect.filing_package_id == filing_package_id
    ).all()
    for defect in defects:
        add_node(defect.id, "DEFECT", defect.defect_type, severity=defect.severity, status=defect.status)
        for req_id in (defect.requirement_refs or []):
            if req_id in seen_nodes:
                edges.append(_edge(req_id, defect.id, "REQUIREMENT_TO_DEFECT"))
        for doc_id in (defect.document_refs or []):
            add_node(doc_id, "DOCUMENT", doc_id[:16])
            edges.append(_edge(doc_id, defect.id, "DOCUMENT_TO_DEFECT"))

    objections = db.query(models.RegistryObjection).filter(
        models.RegistryObjection.filing_package_id == filing_package_id
    ).all()
    for obj in objections:
        add_node(obj.id, "OBJECTION", obj.original_text[:40], status=obj.status)
        if obj.linked_defect_id and obj.linked_defect_id in seen_nodes:
            edges.append(_edge(obj.id, obj.linked_defect_id, "OBJECTION_TO_DEFECT"))

    corrections = db.query(models.CorrectionRequest).filter(
        models.CorrectionRequest.filing_package_id == filing_package_id
    ).all()
    for corr in corrections:
        add_node(corr.id, "CORRECTION", corr.description[:40], status=corr.status)
        if corr.defect_id and corr.defect_id in seen_nodes:
            edges.append(_edge(corr.defect_id, corr.id, "DEFECT_TO_CORRECTION"))
        if corr.objection_id and corr.objection_id in seen_nodes:
            edges.append(_edge(corr.objection_id, corr.id, "OBJECTION_TO_CORRECTION"))

    package = db.query(models.FilingPackage).filter(models.FilingPackage.id == filing_package_id).first()
    verifications = db.query(models.Verification).filter(
        models.Verification.case_id == package.case_id
    ).all() if package else []
    for v in verifications:
        if v.target_type == "DEFECT" and v.target_id in seen_nodes:
            add_node(v.id, "VERIFICATION", v.result, result=v.result)
            edges.append(_edge(v.target_id, v.id, "DEFECT_TO_VERIFICATION"))

    # Document -> Document supersession edges.
    doc_ids = {d.id for d in documents}
    version_ids_by_doc = {
        d.id: [v.id for v in db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == d.id).all()]
        for d in documents
    }
    supersessions = db.query(models.Supersession).all()
    version_to_doc = {v_id: doc_id for doc_id, v_ids in version_ids_by_doc.items() for v_id in v_ids}
    for sup in supersessions:
        pred_doc = version_to_doc.get(sup.predecessor_document_version_id)
        succ_doc = version_to_doc.get(sup.successor_document_version_id)
        if pred_doc in doc_ids and succ_doc in doc_ids and pred_doc != succ_doc:
            edges.append(_edge(pred_doc, succ_doc, "DOCUMENT_SUPERSEDED_BY"))

    return {"filing_package_id": filing_package_id, "nodes": nodes, "edges": edges}
