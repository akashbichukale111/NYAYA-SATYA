from app.services.evaluation_lab import run_evaluation_suite, SCENARIOS


def test_evaluation_suite_covers_every_spec_mandated_scenario():
    expected = {
        "missing_document_detection", "missing_attachment_detection", "metadata_conflict_detection",
        "duplicate_detection", "version_detection", "objection_lifecycle", "correction_verification",
        "provenance_gap", "unknown_requirement", "case_isolation", "prompt_injection_resistance",
        "crash_test_correctness", "historical_reconstruction",
    }
    assert set(SCENARIOS.keys()) == expected


def test_evaluation_suite_all_scenarios_actually_pass(db_session):
    result = run_evaluation_suite(db_session)
    failed = [r for r in result["results"] if r["result"] == "FAIL"]
    assert failed == [], f"Evaluation scenarios failed: {failed}"
    assert result["pass_count"] == result["total"]
    assert result["fail_count"] == 0


def test_evaluation_suite_never_computes_a_percentage_score():
    import inspect
    from app.services import evaluation_lab
    source = inspect.getsource(evaluation_lab)
    assert "* 100" not in source
    assert "/ len(results)" not in source
