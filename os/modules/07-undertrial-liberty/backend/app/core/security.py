"""
Authentication, RBAC, and case isolation enforcement.

DEMO mode uses a simplified header-based identity (X-Demo-Role, X-Demo-User)
so the flagship demo runs without a real auth flow. Production deployments
should replace get_current_user with a real JWT/session-based implementation
(see docs/security.md).
"""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.db.session import get_db
from app.models import orm


class CurrentUser:
    def __init__(self, user_id: str, role: str, display_name: str):
        self.user_id = user_id
        self.role = role
        self.display_name = display_name


def get_current_user(
    x_demo_role: str = Header(default="ADVOCATE"),
    x_demo_user: str = Header(default="demo-advocate-1"),
) -> CurrentUser:
    if x_demo_role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail=f"Unknown role header: {x_demo_role}")
    return CurrentUser(user_id=x_demo_user, role=x_demo_role, display_name=x_demo_user)


# --- RBAC rules -------------------------------------------------------

# Actions requiring elevated roles. CITIZEN is read-limited by default.
ROLE_HIERARCHY = {
    UserRole.CITIZEN.value: 0,
    UserRole.LEGAL_AID.value: 1,
    UserRole.ADVOCATE.value: 2,
    UserRole.ADMIN.value: 3,
}

WRITE_MIN_ROLE = UserRole.LEGAL_AID.value
REVIEW_DECISION_MIN_ROLE = UserRole.ADVOCATE.value
EXPORT_MIN_ROLE = UserRole.ADVOCATE.value
ADMIN_ONLY_MIN_ROLE = UserRole.ADMIN.value


def require_min_role(user: CurrentUser, min_role: str):
    if ROLE_HIERARCHY.get(user.role, -1) < ROLE_HIERARCHY.get(min_role, 99):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user.role}' does not have sufficient privilege for this action (requires >= {min_role}).",
        )


def get_case_or_404(db: Session, case_id: str) -> orm.Case:
    """
    Central case-lookup used by every case-scoped endpoint. This is the
    single choke point that enforces strict case isolation: callers must
    always fetch related rows filtered by this case's id, never by a
    global entity id alone.
    """
    case = db.query(orm.Case).filter(orm.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def assert_entity_belongs_to_case(entity, case_id: str, entity_name: str = "entity"):
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{entity_name} not found")
    if getattr(entity, "case_id", None) != case_id:
        # Do not leak existence of the entity in another case.
        raise HTTPException(status_code=404, detail=f"{entity_name} not found")
    return entity
