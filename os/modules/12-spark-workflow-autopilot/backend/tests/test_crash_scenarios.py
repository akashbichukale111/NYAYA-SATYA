from app.engine import crash_test


def test_run_all_returns_twelve_scenarios():
    results = crash_test.run_all()
    assert len(results) == 12


def test_trigger_duplicated_shows_no_corruption():
    r = crash_test.scenario_trigger_duplicated()
    assert r["evaluated"] is True
    assert r["state_corruption_risk"] == "NONE_OBSERVED"


def test_dependency_disappears_is_honestly_flagged_as_a_gap():
    """This is a known, real gap: it must be reported CONFIRMED, not hidden."""
    r = crash_test.scenario_dependency_disappears()
    assert r["evaluated"] is True
    assert r["state_corruption_risk"] == "CONFIRMED"


def test_workflow_survives_simulated_restart():
    r = crash_test.scenario_workflow_interrupted()
    assert r["state_corruption_risk"] == "NONE_OBSERVED"


def test_stale_state_scenario_confirms_protection_works():
    r = crash_test.scenario_stale_source_state()
    assert r["state_corruption_risk"] == "NONE_OBSERVED"


def test_conflicting_input_scenario_confirms_preservation():
    r = crash_test.scenario_conflicting_input()
    assert r["state_corruption_risk"] == "NONE_OBSERVED"


def test_unimplemented_scenarios_are_marked_not_evaluated_not_fabricated_pass():
    results = crash_test.run_all()
    not_evaluated = {r["scenario"] for r in results if not r["evaluated"]}
    assert not_evaluated == {"TASK_DUPLICATED", "SERVICE_UNAVAILABLE", "TASK_TIMEOUT", "TWO_WORKFLOWS_SAME_OBJECT"}
    for r in results:
        if not r["evaluated"]:
            assert r["state_corruption_risk"] == "NOT_EVALUATED"
            assert r["notes"]  # must explain why, never silent
