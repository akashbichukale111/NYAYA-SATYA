from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, Case, CaseMembership, Workspace
from app.models.enums import MembershipRole
from app.schemas.schemas import CaseOut, CaseCreate
from app.core.security import get_current_user
from app.services.access import authorized_case_ids, get_authorized_case

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=list[CaseOut])
def list_my_cases(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids:
        return []
    return db.query(Case).filter(Case.id.in_(ids)).order_by(Case.updated_at.desc()).all()


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_authorized_case(db, case_id, user)


@router.post("", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.owner_user_id == user.id).first()
    if workspace is None:
        workspace = Workspace(owner_user_id=user.id, name=f"{user.full_name}'s Workspace")
        db.add(workspace)
        db.flush()

    case = Case(
        workspace_id=workspace.id,
        case_number=payload.case_number,
        title=payload.title,
        current_state_summary=payload.current_state_summary,
    )
    db.add(case)
    db.flush()
    db.add(CaseMembership(case_id=case.id, user_id=user.id, role=MembershipRole.OWNER))
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/pin", response_model=CaseOut)
def pin_case(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = get_authorized_case(db, case_id, user)
    membership = db.query(CaseMembership).filter(
        CaseMembership.case_id == case_id, CaseMembership.user_id == user.id
    ).first()
    if membership:
        membership.pinned = True
        db.commit()
    return case


@router.post("/{case_id}/unpin", response_model=CaseOut)
def unpin_case(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = get_authorized_case(db, case_id, user)
    membership = db.query(CaseMembership).filter(
        CaseMembership.case_id == case_id, CaseMembership.user_id == user.id
    ).first()
    if membership:
        membership.pinned = False
        db.commit()
    return case
