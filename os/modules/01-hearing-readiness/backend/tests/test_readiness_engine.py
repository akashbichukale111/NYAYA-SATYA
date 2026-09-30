from app.services.readiness_engine import (
    compute_requirement_status, compute_category_state, compute_overall_readiness,
    build_readiness_snapshot,
)


def test_requirement_status_no_evidence_is_unknown():
    status, reason, confidence = compute_requirement_status([])
    assert status == "UNKNOWN"
    assert confidence == "UNKNOWN"


def test_requirement_status_missing_evidence_is_unresolved():
    status, reason, confidence = compute_requirement_status(
        [{"label": "Affidavit", "availability": "MISSING", "verification_state": "UNVERIFIED"}]
    )
    assert status == "UNRESOLVED"
    assert "Affidavit" in reason


def test_requirement_status_all_available_verified_is_satisfied():
    status, reason, confidence = compute_requirement_status(
        [{"label": "Doc A", "availability": "AVAILABLE", "verification_state": "VERIFIED"}]
    )
    assert status == "SATISFIED"
    assert confidence == "HIGH"


def test_requirement_status_disputed_is_unresolved():
    status, reason, confidence = compute_requirement_status(
        [{"label": "Panchnama", "availability": "AVAILABLE", "verification_state": "DISPUTED"}]
    )
    assert status == "UNRESOLVED"
    assert "disputed" in reason.lower()


def test_category_state_aggregation():
    assert compute_category_state([]) == "UNKNOWN"
    assert compute_category_state(["SATISFIED", "SATISFIED"]) == "SATISFIED"
    assert compute_category_state(["SATISFIED", "UNRESOLVED"]) == "UNRESOLVED"
    assert compute_category_state(["SATISFIED", "UNKNOWN"]) == "UNKNOWN"


def test_overall_readiness_ready_when_all_satisfied():
    overall = compute_overall_readiness({"DOCUMENTS": "SATISFIED"}, False, [])
    assert overall == "READY"


def test_overall_readiness_unknown_when_hearing_uncertain():
    overall = compute_overall_readiness({"DOCUMENTS": "SATISFIED"}, True, [])
    assert overall == "UNKNOWN"


def test_overall_readiness_blocked_with_high_severity_open_blocker():
    overall = compute_overall_readiness({"DOCUMENTS": "UNRESOLVED"}, False, ["HIGH"])
    assert overall == "BLOCKED"


def test_overall_readiness_conditional_with_only_low_severity():
    overall = compute_overall_readiness({"DOCUMENTS": "UNRESOLVED"}, False, ["LOW"])
    assert overall == "CONDITIONAL"


def test_build_readiness_snapshot_counts():
    reqs = [
        {"category": "DOCUMENTS", "status": "SATISFIED"},
        {"category": "DOCUMENTS", "status": "UNRESOLVED"},
        {"category": "EVIDENCE", "status": "UNKNOWN"},
    ]
    blockers = [{"status": "OPEN", "severity": "HIGH"}]
    snap = build_readiness_snapshot(reqs, blockers, hearing_context_uncertain=False)
    assert snap["requirement_count"] == 3
    assert snap["satisfied_count"] == 1
    assert snap["unresolved_count"] == 1
    assert snap["unknown_count"] == 1
    assert snap["overall"] == "BLOCKED"


def test_readiness_never_uses_random_values_is_deterministic():
    reqs = [{"category": "DOCUMENTS", "status": "SATISFIED"}]
    blockers = []
    snap1 = build_readiness_snapshot(reqs, blockers, False)
    snap2 = build_readiness_snapshot(reqs, blockers, False)
    assert snap1 == snap2
