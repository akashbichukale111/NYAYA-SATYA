"""
Role-based access control.

Permissions are additive per role. `require` raises PermissionError which the
API layer turns into HTTP 403. Case isolation is enforced separately in the
API layer by always filtering queries on case_id AND checking the caller's
case_access_ids — never by trusting a caller-supplied case_id alone.
"""
from app.core.enums import Role

PERMISSIONS = {
    Role.CITIZEN: {"workflow:view", "task:view"},
    Role.LEGAL_AID: {"workflow:view", "workflow:create", "task:view", "task:assign"},
    Role.PARALEGAL: {
        "workflow:view", "workflow:create", "task:view", "task:assign",
        "task:execute", "audit:view",
    },
    Role.ADVOCATE: {
        "workflow:view", "workflow:create", "workflow:cancel",
        "task:view", "task:assign", "task:execute", "task:verify",
        "approval:decide", "audit:view",
    },
    Role.ADMIN: {
        "workflow:view", "workflow:create", "workflow:cancel",
        "task:view", "task:assign", "task:execute", "task:verify",
        "approval:decide", "audit:view", "rbac:manage", "case:manage",
    },
}


class PermissionDenied(Exception):
    pass


def has_permission(role: Role, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def require(role: Role, permission: str) -> None:
    if not has_permission(role, permission):
        raise PermissionDenied(f"role {role.value} lacks permission {permission}")


def require_case_access(user_case_ids: set, case_id: str) -> None:
    """A user must not access another case merely by supplying a different ID."""
    if "*" in user_case_ids:
        return
    if case_id not in user_case_ids:
        raise PermissionDenied(f"no access to case {case_id}")
