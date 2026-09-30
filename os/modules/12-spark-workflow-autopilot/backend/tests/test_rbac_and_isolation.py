import pytest
from app.engine.rbac import require, require_case_access, PermissionDenied
from app.core.enums import Role


def test_citizen_cannot_create_workflow():
    with pytest.raises(PermissionDenied):
        require(Role.CITIZEN, "workflow:create")


def test_citizen_can_view_workflow():
    require(Role.CITIZEN, "workflow:view")  # should not raise


def test_paralegal_cannot_decide_approval():
    with pytest.raises(PermissionDenied):
        require(Role.PARALEGAL, "approval:decide")


def test_advocate_can_decide_approval():
    require(Role.ADVOCATE, "approval:decide")  # should not raise


def test_case_isolation_denies_unlisted_case():
    with pytest.raises(PermissionDenied):
        require_case_access({"case_a"}, "case_b")


def test_case_isolation_allows_listed_case():
    require_case_access({"case_a", "case_b"}, "case_b")  # should not raise


def test_wildcard_case_access_allows_any_case():
    """'*' is the ADMIN-style all-cases grant, not a bypass a normal user can forge:
    it is only ever set server-side via the demo auth header default, never derived
    from case IDs the caller supplies."""
    require_case_access({"*"}, "any_case_id_at_all")  # should not raise
