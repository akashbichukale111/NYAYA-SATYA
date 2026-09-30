from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.orm import Case
from app.core.rbac import Actor, require_case_access


def require_case_with_access(db: Session, case_id: str, actor: Actor) -> Case:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    require_case_access(case, actor)
    return case
