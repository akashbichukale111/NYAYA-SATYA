import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_capability, assert_case_access
from app.core.ids import new_id, utcnow
from app.core.audit import record as audit_record
from app.services import parsing, attachment_engine
from app import models, schemas
from app.routers.cases import _get_package_or_404

router = APIRouter(tags=["documents"])


@router.post("/api/filing-packages/{package_id}/documents", response_model=schemas.DocumentOut)
async def upload_document(
    package_id: str,
    display_name: str = Form(...),
    document_kind: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)
    require_capability(user, "UPLOAD_DOCUMENT")

    content = await file.read()

    # Security: reject dangerous extensions outright regardless of declared
    # content type.
    from app.services.security_scan import check_dangerous_extension
    if check_dangerous_extension(file.filename or ""):
        audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                     action="UPLOAD_REJECTED_DANGEROUS_EXTENSION", entity_type="Document",
                     entity_id=None, reason=file.filename, provenance="SECURITY")
        raise HTTPException(status_code=400, detail="File type not permitted")

    parsed = parsing.parse_file(file.filename or "upload", content)

    document = models.Document(
        id=new_id("doc"), case_id=case.id, filing_package_id=package_id,
        display_name=display_name, document_kind=document_kind, status="ACTIVE",
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    version_id = new_id("docv")
    safe_name = parsing.safe_filename(file.filename or "upload", version_id)
    storage_dir = os.path.join(parsing.STORAGE_ROOT, case.id, package_id)
    os.makedirs(storage_dir, exist_ok=True)
    stored_path = os.path.join(storage_dir, safe_name)
    # Path traversal protection: stored_path is always constructed from
    # generated ids/validated dir components, never from client input.
    if not os.path.abspath(stored_path).startswith(os.path.abspath(parsing.STORAGE_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid storage path")
    with open(stored_path, "wb") as f:
        f.write(content)

    version = models.DocumentVersion(
        id=version_id, document_id=document.id, case_id=case.id, version_number=1,
        original_filename=file.filename or "upload", stored_path=stored_path,
        mime_type=parsed.mime_type, detected_format=parsed.detected_format,
        size_bytes=parsed.size_bytes, sha256=parsed.sha256,
        extracted_text=parsed.extracted_text, extraction_status=parsed.extraction_status,
        extraction_error=parsed.extraction_error, page_count=parsed.page_count,
        quarantined=parsed.quarantined, quarantine_reason=parsed.quarantine_reason,
        uploaded_at=utcnow().isoformat(), uploaded_by_user_id=user.id,
        source_location_known=parsed.source_location_known,
    )
    db.add(version)
    document.current_version_id = version.id
    db.commit()
    db.refresh(version)

    for section in parsed.sections:
        db.add(models.DocumentSection(
            id=new_id("sec"), document_version_id=version.id, case_id=case.id,
            section_type=section.section_type, section_index=section.section_index,
            text_excerpt=section.text_excerpt, location_known=section.location_known,
        ))
    db.commit()

    db.add(models.ProvenanceRecord(
        id=new_id("prov"), case_id=case.id, entity_type="Document", entity_id=document.id,
        origin="UPLOAD", origin_detail=f"sha256={parsed.sha256}",
    ))
    db.commit()

    if parsed.extraction_status == "OK":
        attachment_engine.detect_and_store_references(
            db, case_id=case.id, filing_package_id=package_id, document_version=version,
        )

    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="UPLOAD_DOCUMENT", entity_type="Document", entity_id=document.id,
                 after_state={"filename": file.filename, "sha256": parsed.sha256,
                              "extraction_status": parsed.extraction_status},
                 provenance="UPLOAD")

    if package.lifecycle_state == "DRAFT":
        package.lifecycle_state = "PACKAGE_ASSEMBLED"
        package.updated_at = utcnow().isoformat()
        db.commit()

    return document


@router.get("/api/filing-packages/{package_id}/documents", response_model=list[schemas.DocumentOut])
def list_documents(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.Document).filter(models.Document.filing_package_id == package_id).all()


@router.get("/api/documents/{document_id}/versions", response_model=list[schemas.DocumentVersionOut])
def list_document_versions(document_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_case_access(db, user, doc.case_id)
    return db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == document_id).all()
