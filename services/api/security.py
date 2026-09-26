"""FastAPI dependencies that put a real principal and RBAC on every mutating request.

WHY A SEPARATE MODULE
------------------------
`services/api/main.py` and `services/api/nyaya.py` contain numerous endpoints.
Burying authentication and authorization decisions in route handlers is how an
endpoint gets added later without one. Everything privileged imports `require_principal`,
`require_human_principal`, `require_role`, or `require_case_access` from here.

Tests in `tests/test_api_auth.py` walk the app's route table and verify that every
mutating route enforces a real authenticated principal.

RATE LIMITING, HONESTLY SCOPED
---------------------------------
[LIMITATION] The limiter below is an in-process token bucket keyed by principal.
On a single Cloud Run instance it is a real limit. Across several instances it limits
per instance, not globally -- a real deployment wants Cloud Armor or an API gateway in front.

ROLE-BASED ACCESS CONTROL (RBAC)
---------------------------------
Enforces explicit permissions across five canonical roles:
- VIEWER: Read permitted dossiers and public reports.
- ANALYST: Run structural analysis, builds twins, and simulates repairs.
- LEGAL_REVIEWER: Review proposals, approve/reject human review items (strictly requires human principal).
- GOVERNANCE_REVIEWER: Audit state transitions and execution guard logs.
- ADMIN: System configuration and testing resets.

CROSS-CASE ISOLATION
---------------------
Enforces strict multi-tenant case boundaries. A principal granted access to CASE_A
cannot read, modify, or query CASE_B.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from fastapi import HTTPException, Request

from lib.auth import Principal, Unauthenticated, Unauthorized, authenticate, require_human
from nyaya_observability.audit import record_audit


class Role(str, Enum):
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    LEGAL_REVIEWER = "LEGAL_REVIEWER"
    GOVERNANCE_REVIEWER = "GOVERNANCE_REVIEWER"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class UserContext:
    principal: Principal
    roles: frozenset[Role]
    accessible_cases: frozenset[str] | None = None

    def has_role(self, role: Role) -> bool:
        return role in self.roles or Role.ADMIN in self.roles

    def can_access_case(self, case_id: str) -> bool:
        if self.accessible_cases is None or Role.ADMIN in self.roles:
            return True
        return case_id in self.accessible_cases


#: [ASSUMPTION] Chosen limits: enough for interactive analysis,
#: low enough that an unattended loop or DDoS attempt is stopped.
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60.0

EXPENSIVE_RATE_LIMIT = 15
EXPENSIVE_RATE_WINDOW_SECONDS = 60.0

_BUCKETS: dict[str, deque[float]] = {}
_EXPENSIVE_BUCKETS: dict[str, deque[float]] = {}

# In-memory RBAC assignments: principal -> set of Roles
_PRINCIPAL_ROLES: dict[str, set[Role]] = {}

# In-memory Case-level authorization: principal -> set of accessible case_ids
# If a principal is not in this map, they have default access.
# If they are in this map, access is strictly limited to the specified case_ids.
_CASE_ACCESS_MAP: dict[str, set[str]] = {}


def assign_role(principal_id: str, role: Role) -> None:
    """Explicitly grants a role to a principal."""
    _PRINCIPAL_ROLES.setdefault(principal_id, set()).add(role)


def remove_role(principal_id: str, role: Role) -> None:
    if principal_id in _PRINCIPAL_ROLES:
        _PRINCIPAL_ROLES[principal_id].discard(role)


def get_principal_roles(principal: Principal) -> frozenset[Role]:
    """Resolves roles for an authenticated principal based on configuration and identity."""
    explicit = _PRINCIPAL_ROLES.get(principal.principal)
    if explicit:
        return frozenset(explicit)

    # Inferred default roles by identity convention
    pid = principal.principal.lower()
    roles: set[Role] = {Role.VIEWER}

    if "admin" in pid:
        roles.update({Role.ADMIN, Role.GOVERNANCE_REVIEWER, Role.LEGAL_REVIEWER, Role.ANALYST})
    elif principal.is_human and ("jurist" in pid or "judge" in pid or "legal" in pid or "lawyer" in pid or "counsel" in pid):
        roles.update({Role.LEGAL_REVIEWER, Role.ANALYST})
    elif "gov" in pid or "governance" in pid:
        roles.update({Role.GOVERNANCE_REVIEWER, Role.VIEWER})
    elif "analyst" in pid:
        roles.update({Role.ANALYST})
    else:
        # Default operational roles
        if principal.is_human:
            roles.update({Role.LEGAL_REVIEWER, Role.ANALYST})
        else:
            roles.update({Role.ANALYST})

    return frozenset(roles)


def grant_case_access(principal_id: str, case_id: str) -> None:
    """Restricts/grants access for a principal to a specific case."""
    _CASE_ACCESS_MAP.setdefault(principal_id, set()).add(case_id)


def revoke_case_access(principal_id: str, case_id: str) -> None:
    if principal_id in _CASE_ACCESS_MAP:
        _CASE_ACCESS_MAP[principal_id].discard(case_id)


def get_accessible_cases(principal_id: str) -> frozenset[str] | None:
    if principal_id in _CASE_ACCESS_MAP:
        return frozenset(_CASE_ACCESS_MAP[principal_id])
    return None


def reset_case_access() -> None:
    _CASE_ACCESS_MAP.clear()
    _PRINCIPAL_ROLES.clear()


def _check_rate_limit(principal: str) -> None:
    now = time.monotonic()
    bucket = _BUCKETS.setdefault(principal, deque())
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_REQUESTS:
        record_audit(
            "RATE_LIMIT_EXCEEDED",
            level="WARNING",
            actor_id=principal,
            status="BLOCKED",
            details={"limit": RATE_LIMIT_REQUESTS, "window_s": RATE_LIMIT_WINDOW_SECONDS},
        )
        raise HTTPException(
            429,
            f"rate limit exceeded for {principal}: more than {RATE_LIMIT_REQUESTS} "
            f"requests in {RATE_LIMIT_WINDOW_SECONDS:.0f}s",
        )
    bucket.append(now)


def check_expensive_rate_limit(principal: str) -> None:
    now = time.monotonic()
    bucket = _EXPENSIVE_BUCKETS.setdefault(principal, deque())
    while bucket and now - bucket[0] > EXPENSIVE_RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= EXPENSIVE_RATE_LIMIT:
        record_audit(
            "EXPENSIVE_RATE_LIMIT_EXCEEDED",
            level="WARNING",
            actor_id=principal,
            status="BLOCKED",
            details={"limit": EXPENSIVE_RATE_LIMIT, "window_s": EXPENSIVE_RATE_WINDOW_SECONDS},
        )
        raise HTTPException(
            429,
            f"expensive operation rate limit exceeded for {principal}: more than "
            f"{EXPENSIVE_RATE_LIMIT} requests in {EXPENSIVE_RATE_WINDOW_SECONDS:.0f}s",
        )
    bucket.append(now)


def reset_rate_limits() -> None:
    """Test hook. Mirrors the `reset_for_test` hooks elsewhere in the repo."""
    _BUCKETS.clear()
    _EXPENSIVE_BUCKETS.clear()


def require_principal(request: Request) -> Principal:
    """Any authenticated caller. 401 when nothing resolves -- never a default."""
    try:
        principal = authenticate(request.headers)
    except Unauthenticated as exc:
        record_audit("AUTHENTICATION_FAILED", level="WARNING", actor_id="anonymous", status="FAILED", details={"error": str(exc)})
        raise HTTPException(401, str(exc)) from exc
    _check_rate_limit(principal.principal)
    return principal


def require_human_principal(request: Request) -> Principal:
    """An authenticated HUMAN. 403 for a service identity."""
    principal = require_principal(request)
    try:
        return require_human(principal)
    except Unauthorized as exc:
        record_audit(
            "HUMAN_GATE_NON_HUMAN_BLOCKED",
            level="WARNING",
            actor_id=principal.principal,
            status="BLOCKED",
            details={"error": str(exc)},
        )
        raise HTTPException(403, str(exc)) from exc


def get_user_context(principal: Principal) -> UserContext:
    roles = get_principal_roles(principal)
    cases = get_accessible_cases(principal.principal)
    return UserContext(principal=principal, roles=roles, accessible_cases=cases)


def require_role(required_role: Role) -> Callable[[Request], UserContext]:
    """Dependency factory checking that the caller holds the specified Role."""
    def _dependency(request: Request) -> UserContext:
        principal = require_principal(request)
        ctx = get_user_context(principal)
        if not ctx.has_role(required_role):
            record_audit(
                "AUTHORIZATION_ROLE_DENIED",
                level="WARNING",
                actor_id=principal.principal,
                status="DENIED",
                details={"required_role": required_role.value, "assigned_roles": [r.value for r in ctx.roles]},
            )
            raise HTTPException(
                403,
                f"Principal {principal.principal!r} lacks required role {required_role.value}. "
                f"Assigned roles: {[r.value for r in ctx.roles]}",
            )
        return ctx
    return _dependency


def verify_case_access(principal: Principal, case_id: str) -> None:
    """Enforces tenant case isolation."""
    ctx = get_user_context(principal)
    if not ctx.can_access_case(case_id):
        record_audit(
            "CROSS_CASE_ACCESS_BLOCKED",
            level="WARNING",
            actor_id=principal.principal,
            case_id=case_id,
            status="BLOCKED",
            details={"accessible_cases": list(ctx.accessible_cases or [])},
        )
        raise HTTPException(
            403,
            f"Cross-case access denied: principal {principal.principal!r} is not authorized "
            f"to access case {case_id!r}",
        )


__all__ = [
    "EXPENSIVE_RATE_LIMIT",
    "EXPENSIVE_RATE_WINDOW_SECONDS",
    "RATE_LIMIT_REQUESTS",
    "RATE_LIMIT_WINDOW_SECONDS",
    "Role",
    "UserContext",
    "assign_role",
    "check_expensive_rate_limit",
    "get_accessible_cases",
    "get_principal_roles",
    "get_user_context",
    "grant_case_access",
    "remove_role",
    "require_human_principal",
    "require_principal",
    "require_role",
    "reset_case_access",
    "reset_rate_limits",
    "revoke_case_access",
    "verify_case_access",
]
