from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_capability, assert_case_access
from app.core.ids import new_id, utcnow
from app.core.audit import record as audit_record
from app.services import precheck as precheck_service
from app import models, schemas
from app.routers.cases import _get_package_or_404

router = APIRouter(tags=["defects"])


@router.post("/api/filing-packages/{package_id}/precheck")
def run_precheck(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)
    require_capability(user, "RUN_PRECHECK")

    package.lifecycle_state = "PRECHECK"
    db.commit()

    result = precheck_service.run_precheck(db, case_id=case.id, filing_package_id=package_id)

    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="RUN_PRECHECK", entity_type="FilingPackage", entity_id=package_id,
                 after_state=result, provenance="SYSTEM_DERIVED")
    return result


@router.get("/api/filing-packages/{package_id}/defects", response_model=list[schemas.DefectOut])
def list_defects(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.Defect).filter(models.Defect.filing_package_id == package_id).all()


@router.get("/api/defects/{defect_id}", response_model=schemas.DefectOut)
def get_defect(defect_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    defect = db.query(models.Defect).filter(models.Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    assert_case_access(db, user, defect.case_id)
    return defect


@router.get("/api/defects/{defect_id}/suggested-correction")
def get_suggested_correction(defect_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Returns a non-binding, LLM-or-template-drafted suggestion for how a
    human might phrase a correction. This is advisory text only — it is
    never treated as a determination that the defect is resolved or that
    the filing is compliant. Works with zero LLM configuration (falls
    back to a deterministic template — see app/services/llm_provider.py)."""
    from app.services.llm_provider import get_provider

    defect = db.query(models.Defect).filter(models.Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    assert_case_access(db, user, defect.case_id)

    provider = get_provider()
    suggestion = provider.suggest_correction_wording(
        defect_description=defect.description,
        context=f"Category: {defect.category}; Severity: {defect.severity} (operational attention, not a legal judgment).",
    )
    return {
        "defect_id": defect_id,
        "suggestion": suggestion.text,
        "provider": suggestion.provider,
        "model": suggestion.model,
        "is_mock": suggestion.is_mock,
        "disclaimer": "This is a drafting aid, not a legal determination. A human must review and approve any correction.",
    }


@router.post("/api/filing-packages/{package_id}/objections", response_model=schemas.ObjectionOut)
def create_objection(package_id: str, payload: schemas.ObjectionCreate, db: Session = Depends(get_db),
                      user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)

    obj = models.RegistryObjection(
        id=new_id("obj"), case_id=case.id, filing_package_id=package_id,
        original_text=payload.original_text, source_reference=payload.source_reference,
        status="OPEN", created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="CREATE_OBJECTION", entity_type="RegistryObjection", entity_id=obj.id,
                 after_state={"original_text": obj.original_text}, provenance="USER_INPUT")
    return obj


@router.get("/api/filing-packages/{package_id}/objections", response_model=list[schemas.ObjectionOut])
def list_objections(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.RegistryObjection).filter(models.RegistryObjection.filing_package_id == package_id).all()


@router.post("/api/filing-packages/{package_id}/corrections", response_model=schemas.CorrectionOut)
def create_correction(package_id: str, payload: schemas.CorrectionCreate, db: Session = Depends(get_db),
                       user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)

    correction = models.CorrectionRequest(
        id=new_id("creq"), case_id=case.id, filing_package_id=package_id,
        defect_id=payload.defect_id, objection_id=payload.objection_id,
        description=payload.description, suggested_action=payload.suggested_action,
        status="PLANNED", created_at=utcnow().isoformat(),
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="CREATE_CORRECTION", entity_type="CorrectionRequest", entity_id=correction.id,
                 after_state={"description": correction.description}, provenance="USER_INPUT")
    return correction


@router.get("/api/filing-packages/{package_id}/corrections", response_model=list[schemas.CorrectionOut])
def list_corrections(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.CorrectionRequest).filter(models.CorrectionRequest.filing_package_id == package_id).all()
