from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_capability, assert_case_access
from app.core.ids import new_id, utcnow
from app.core.audit import record as audit_record
from app import models, schemas

router = APIRouter(tags=["cases"])


@router.post("/api/cases", response_model=schemas.CaseOut)
def create_case(payload: schemas.CaseCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = models.Case(
        id=new_id("case"), title=payload.title, case_reference=payload.case_reference,
        owner_user_id=user.id, status="ACTIVE", is_demo=False,
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="CREATE_CASE", entity_type="Case", entity_id=case.id,
                 after_state={"title": case.title}, provenance="USER_INPUT")
    return case


@router.get("/api/cases/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = assert_case_access(db, user, case_id)
    return case


@router.get("/api/cases", response_model=list[schemas.CaseOut])
def list_cases(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    from app.core.enums import UserRole
    if UserRole(user.role) == UserRole.ADMIN:
        return db.query(models.Case).all()
    return db.query(models.Case).filter(models.Case.owner_user_id == user.id).all()


@router.post("/api/cases/{case_id}/filing-packages", response_model=schemas.FilingPackageOut)
def create_filing_package(case_id: str, payload: schemas.FilingPackageCreate, db: Session = Depends(get_db),
                           user: models.User = Depends(get_current_user)):
    assert_case_access(db, user, case_id)
    pkg = models.FilingPackage(
        id=new_id("pkg"), case_id=case_id, name=payload.name, lifecycle_state="DRAFT",
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    audit_record(db, case_id=case_id, actor_user_id=user.id, actor_role=user.role,
                 action="CREATE_FILING_PACKAGE", entity_type="FilingPackage", entity_id=pkg.id,
                 after_state={"name": pkg.name}, provenance="USER_INPUT")
    return pkg


@router.get("/api/cases/{case_id}/filing-packages", response_model=list[schemas.FilingPackageOut])
def list_filing_packages(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    assert_case_access(db, user, case_id)
    return db.query(models.FilingPackage).filter(models.FilingPackage.case_id == case_id).all()


def _get_package_or_404(db: Session, package_id: str) -> models.FilingPackage:
    pkg = db.query(models.FilingPackage).filter(models.FilingPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Filing package not found")
    return pkg
