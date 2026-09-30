from app.diff import diff_snapshots


def test_diff_detects_added_removed_changed():
    before = {
        "procedural_stage": "Intake",
        "open_items_count": 1,
        "deadlines": {"d1": {"label": "Reply", "due_date": "12 Oct 2026", "status": "open"}},
        "obligations": {}, "orders": {}, "hearings": {}, "evidence": {}, "actions": {}, "documents": {},
    }
    after = {
        "procedural_stage": "Pending Reply",
        "open_items_count": 2,
        "deadlines": {"d1": {"label": "Reply", "due_date": "19 Oct 2026", "status": "open"},
                      "d2": {"label": "Rejoinder", "due_date": "01 Nov 2026", "status": "open"}},
        "obligations": {}, "orders": {}, "hearings": {}, "evidence": {}, "actions": {}, "documents": {},
    }
    diff = diff_snapshots(before, after)
    deadlines_diff = diff["entities"]["deadlines"]
    assert len(deadlines_diff["added"]) == 1
    assert deadlines_diff["added"][0]["id"] == "d2"
    assert len(deadlines_diff["changed"]) == 1
    assert deadlines_diff["changed"][0]["id"] == "d1"
    assert deadlines_diff["changed"][0]["fields"]["due_date"]["before"] == "12 Oct 2026"
    assert deadlines_diff["changed"][0]["fields"]["due_date"]["after"] == "19 Oct 2026"
    assert diff["summary"]["procedural_stage_before"] == "Intake"
    assert diff["summary"]["procedural_stage_after"] == "Pending Reply"
    assert diff["summary"]["open_items_delta"] == 1


def test_diff_detects_removed_items():
    before = {"deadlines": {"d1": {"label": "x", "due_date": "1 Jan", "status": "open"}},
              "obligations": {}, "orders": {}, "hearings": {}, "evidence": {}, "actions": {}, "documents": {}}
    after = {"deadlines": {}, "obligations": {}, "orders": {}, "hearings": {}, "evidence": {}, "actions": {},
             "documents": {}}
    diff = diff_snapshots(before, after)
    assert len(diff["entities"]["deadlines"]["removed"]) == 1
    assert diff["entities"]["deadlines"]["removed"][0]["id"] == "d1"


def test_diff_of_identical_snapshots_is_empty():
    snap = {"deadlines": {}, "obligations": {}, "orders": {}, "hearings": {}, "evidence": {}, "actions": {},
            "documents": {}}
    diff = diff_snapshots(snap, dict(snap))
    assert diff["summary"]["added"] == 0
    assert diff["summary"]["removed"] == 0
    assert diff["summary"]["changed"] == 0
