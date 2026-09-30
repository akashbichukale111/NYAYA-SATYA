from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Case, CaseMembership, User
from app.models.enums import RoleName


def get_authorized_case(db: Session, case_id: str, user: User) -> Case:
    """
    Returns the case only if it exists AND the user is authorized to see it
    (an explicit CaseMembership, or an Admin). Raises 404 rather than 403 when
    unauthorized so the existence of cases the user cannot see is not leaked.
    """
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if user.role == RoleName.ADMIN:
        return case

    membership = (
        db.query(CaseMembership)
        .filter(CaseMembership.case_id == case_id, CaseMembership.user_id == user.id)
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def authorized_case_ids(db: Session, user: User) -> list[str]:
    if user.role == RoleName.ADMIN:
        return [c.id for c in db.query(Case.id).all()]
    memberships = db.query(CaseMembership.case_id).filter(CaseMembership.user_id == user.id).all()
    return [m.case_id for m in memberships]
