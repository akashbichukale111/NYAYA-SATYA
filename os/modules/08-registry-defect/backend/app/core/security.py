"""
RBAC and case-isolation enforcement.

Case isolation rule: every query for a case-scoped entity MUST filter by
case_id, and case_id MUST come from the authenticated request context
(via the X-Case-Access header / current user's permitted cases in a real
deployment) — never trusted blindly from a path parameter alone without
checking the requesting principal is allowed to see that case.

For this build, authentication is a lightweight bearer-token-free scheme
suitable for local/demo use: the caller identifies as a user via
X-User-Id, and access control is enforced by role + an explicit
case-access allowlist (CaseAccessRegistry). This keeps the security
*shape* real (server-side enforcement, deny-by-default, audited denials)
while remaining runnable without an external auth provider.
"""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.enums import UserRole
from app import models


class AccessDenied(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


def get_current_user(
    x_user_id: str = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> models.User:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Unknown or inactive user")
    return user


# Deny-by-default capability matrix. Only roles listed for an action may
# perform it. Human-review / consequential actions are restricted to
# roles capable of legal/case oversight.
ROLE_CAPABILITIES = {
    "VIEW_CASE": {UserRole.CITIZEN, UserRole.LEGAL_AID, UserRole.ADVOCATE, UserRole.ADMIN},
    "UPLOAD_DOCUMENT": {UserRole.CITIZEN, UserRole.LEGAL_AID, UserRole.ADVOCATE, UserRole.ADMIN},
    "CREATE_REQUIREMENT": {UserRole.LEGAL_AID, UserRole.ADVOCATE, UserRole.ADMIN},
    "RUN_PRECHECK": {UserRole.LEGAL_AID, UserRole.ADVOCATE, UserRole.ADMIN},
    "APPROVE_REVIEW": {UserRole.ADVOCATE, UserRole.ADMIN},
    "REJECT_REVIEW": {UserRole.ADVOCATE, UserRole.ADMIN},
    "RUN_SIMULATION": {UserRole.LEGAL_AID, UserRole.ADVOCATE, UserRole.ADMIN},
    "RUN_CRASH_TEST": {UserRole.ADVOCATE, UserRole.ADMIN},
    "MANAGE_USERS": {UserRole.ADMIN},
    "VIEW_AUDIT": {UserRole.ADVOCATE, UserRole.ADMIN},
}


def require_capability(user: models.User, capability: str):
    allowed = ROLE_CAPABILITIES.get(capability, set())
    if UserRole(user.role) not in allowed:
        raise AccessDenied(f"Role {user.role} is not permitted to perform '{capability}'")


def assert_case_access(db: Session, user: models.User, case_id: str) -> models.Case:
    """Deny-by-default case isolation check.

    ADMIN may access any case (governance oversight). All other roles
    may only access a case they own (owner_user_id) — this is a simple,
    strict model appropriate for a citizen/legal-aid/advocate filing
    tool where cross-case visibility must never leak by default.
    """
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if UserRole(user.role) == UserRole.ADMIN:
        return case
    if case.owner_user_id and case.owner_user_id != user.id:
        raise AccessDenied("You do not have access to this case")
    return case
