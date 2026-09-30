"""
Demo/mock authentication.

Real deployments would swap this for OAuth/JWT validation, but the
authorization *model* (Role + per-case access set) is real and enforced the
same way regardless of how the identity was established.

Headers:
  X-User-Id      -> arbitrary string identifying the caller (default 'demo-user')
  X-Role         -> one of Role enum values (default 'PARALEGAL')
  X-Case-Access  -> comma-separated case IDs this user may access.
                    '*' grants access to all cases (used by ADMIN in demo mode).
"""
from fastapi import Header, HTTPException
from app.core.enums import Role


class AuthContext:
    def __init__(self, user_id: str, role: Role, case_access: set):
        self.user_id = user_id
        self.role = role
        self.case_access = case_access

    def can_access_case(self, case_id: str) -> bool:
        return "*" in self.case_access or case_id in self.case_access


def get_auth_context(
    x_user_id: str = Header(default="demo-user"),
    x_role: str = Header(default="PARALEGAL"),
    x_case_access: str = Header(default="*"),
) -> AuthContext:
    try:
        role = Role(x_role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"unknown role: {x_role}")
    case_access = set(s.strip() for s in x_case_access.split(",") if s.strip())
    return AuthContext(user_id=x_user_id, role=role, case_access=case_access)
