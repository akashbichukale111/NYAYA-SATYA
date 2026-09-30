import pytest

from app.services import readiness_engine, action_planner, verification_engine
from app.tools.registry import build_default_registry, AuthorizationError
from app.models.evidence import Evidence
from app.models.requirement import Requirement
from app.models.blocker import Blocker


def _seed_blocked_case(db):
    from app.services import case_twin
    from app.models.hearing import Hearing

    case = case_twin.create_case(db, "Action Test Case", "civil", [])
    hearing = Hearing(case_id=case.id, is_next="true", purpose="ARGUMENTS", purpose_status="DETERMINED")
    db.add(hearing)
    db.flush()

    ev = Evidence(case_id=case.id, label="Missing Doc", evidence_type="document",
                  availability="MISSING", verification_state="UNVERIFIED", confidence="HIGH")
    db.add(ev)
    db.flush()

    req = Requirement(case_id=case.id, hearing_id=hearing.id, category="DOCUMENTS",
                       description="Doc filed", status="UNKNOWN", reason="", evidence_refs=[ev.id],
                       confidence="UNKNOWN")
    db.add(req)
    db.flush()
    readiness_engine.run_readiness_audit(db, case.id)
    blocker = db.query(Blocker).filter(Blocker.case_id == case.id).first()
    return case, blocker


def test_propose_action_is_pending_approval(db_session):
    case, blocker = _seed_blocked_case(db_session)
    action = action_planner.propose_action(db_session, blocker)
    assert action.status == "PENDING_APPROVAL"
    assert action.blocker_id == blocker.id


def test_verify_action_fails_before_execution(db_session):
    case, blocker = _seed_blocked_case(db_session)
    action = action_planner.propose_action(db_session, blocker)
    # Never executed -> no result artifact -> verification must fail.
    verification = verification_engine.verify_action(db_session, action)
    assert verification.result == "VERIFICATION_FAILED"


def test_execute_then_verify_action_passes(db_session):
    case, blocker = _seed_blocked_case(db_session)
    action = action_planner.propose_action(db_session, blocker)
    verification_engine.execute_action(db_session, action)
    verification = verification_engine.verify_action(db_session, action)
    assert verification.result == "PASSED"
    assert action.status == "VERIFIED"
    assert action.result["artifact_type"] in ("checklist", "reminder_draft", "evidence_index")


def test_tool_registry_blocks_consequential_tool_without_authorization(db_session):
    case, blocker = _seed_blocked_case(db_session)
    action = action_planner.propose_action(db_session, blocker)
    registry = build_default_registry()
    with pytest.raises(AuthorizationError):
        registry.call("state_update", authorized=False, db=db_session, action=action)


def test_tool_registry_allows_consequential_tool_with_authorization(db_session):
    case, blocker = _seed_blocked_case(db_session)
    action = action_planner.propose_action(db_session, blocker)
    registry = build_default_registry()
    # Should not raise.
    registry.call("state_update", authorized=True, db=db_session, action=action)
    assert action.status == "EXECUTED"
