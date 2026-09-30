from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_capability, assert_case_access
from app.core.audit import record as audit_record
from app.services import requirement_engine, checklist_engine
from app import models, schemas
from app.routers.cases import _get_package_or_404

router = APIRouter(tags=["requirements"])


@router.post("/api/filing-packages/{package_id}/requirements", response_model=schemas.RequirementOut)
def create_requirement(package_id: str, payload: schemas.RequirementCreate, db: Session = Depends(get_db),
                        user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)
    require_capability(user, "CREATE_REQUIREMENT")

    req = requirement_engine.create_requirement(
        db, case_id=case.id, filing_package_id=package_id,
        requirement_type=payload.requirement_type, description=payload.description,
        source=payload.source, source_reference=payload.source_reference,
        target_reference_label=payload.target_reference_label,
        jurisdiction=payload.jurisdiction, effective_from=payload.effective_from,
        effective_until=payload.effective_until,
    )
    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="CREATE_REQUIREMENT", entity_type="Requirement", entity_id=req.id,
                 after_state={"description": req.description, "source": req.source},
                 provenance=payload.source)
    return req


@router.get("/api/filing-packages/{package_id}/requirements", response_model=list[schemas.RequirementOut])
def list_requirements(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.Requirement).filter(models.Requirement.filing_package_id == package_id).all()


@router.get("/api/filing-packages/{package_id}/checklist", response_model=list[schemas.ChecklistItemOut])
def get_checklist(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.ChecklistItem).filter(models.ChecklistItem.filing_package_id == package_id).all()
