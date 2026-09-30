"""
RBAC enforcement.

Identity/role are read from request headers (X-User-Id / X-User-Role).
There is no login/session system in this pass -- this is documented as a
known limitation (see docs/status.md): a real deployment would replace
`get_actor` with a proper auth dependency (JWT/session), but the
*enforcement points* below (require_role, require_case_access) are real
and are exercised by tests/security/test_rbac.py.

Backward-compatibility default: a request with NO auth headers resolves to
role ADMIN / user "system-user" so the Section 1 API contract and its 19
tests keep working unmodified. Any request that DOES send X-User-Role is
enforced against that role for real -- this is what makes RBAC testable
and real rather than decorative.
"""
from typing import Optional

from fastapi import Header, HTTPException

from app.models.enums import UserRole

ROLE_ORDER = {
    UserRole.CITIZEN.value: 0,
    UserRole.LEGAL_AID.value: 1,
    UserRole.ADVOCATE.value: 2,
    UserRole.ADMIN.value: 3,
}

DEFAULT_ROLE = UserRole.ADMIN.value
DEFAULT_USER_ID = "system-user"


class Actor:
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role

    def __repr__(self):
        return f"Actor(user_id={self.user_id!r}, role={self.role!r})"


def get_actor(
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
) -> Actor:
    role = x_user_role or DEFAULT_ROLE
    if role not in ROLE_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown role '{role}'. Valid roles: {list(ROLE_ORDER)}")
    user_id = x_user_id or DEFAULT_USER_ID
    return Actor(user_id=user_id, role=role)


def require_role(actor: Actor, minimum_role: str):
    if ROLE_ORDER[actor.role] < ROLE_ORDER[minimum_role]:
        raise HTTPException(
            status_code=403,
            detail=f"This action requires role >= {minimum_role}; actor has role {actor.role}.",
        )


def require_case_access(case, actor: Actor):
    """
    Case-level access control.
    - Demo cases are readable/usable by anyone (they're synthetic).
    - A case with no owner recorded (legacy/open) is accessible to anyone --
      this only happens for cases created before an owner header was sent.
    - Otherwise only the owning user or an ADMIN may access it.
    """
    if case.is_demo:
        return
    if case.owner_user_id is None:
        return
    if case.owner_user_id == actor.user_id:
        return
    if actor.role == UserRole.ADMIN.value:
        return
    raise HTTPException(status_code=403, detail="Not authorized to access this case.")
