"""
Role-based access control.

Simple, explicit, and honest about its own limits: this reads a caller-supplied
`X-User-Role` header rather than verifying a signed session, because Section 1/2
has no auth/login system yet (that is out of scope until an auth provider is
wired in). What it DOES enforce, for real, right now: which roles are allowed
to call which consequential endpoints (approve/reject a review, restore a
snapshot). Every request missing the header is treated as the lowest-privilege
role, never as an admin — the fail-safe direction is always toward requiring
more privilege, not less.
"""

from enum import Enum

from fastapi import Header, HTTPException


class Role(str, Enum):
    ANALYST = "ANALYST"   # can create cases, run simulations, view everything
    REVIEWER = "REVIEWER"  # + approve/reject review tasks
    ADMIN = "ADMIN"        # + restore snapshots, manage users

_RANK = {Role.ANALYST: 0, Role.REVIEWER: 1, Role.ADMIN: 2}


def require_role(minimum: Role):
    def _dep(x_user_role: str | None = Header(default=None)) -> Role:
        try:
            role = Role(x_user_role) if x_user_role else Role.ANALYST
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown role: {x_user_role}")
        if _RANK[role] < _RANK[minimum]:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role {minimum.value} or higher (got {role.value}).",
            )
        return role

    return _dep
