from tests.conftest import get_case_by_key


def test_case_d_has_a_superseded_deadline_and_never_deletes_it(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_D")
    r = seeded_client.get(f"/api/cases/{case['id']}/state")
    snapshot = r.json()["snapshot"]
    # Superseded deadlines are excluded from the "current" view...
    open_deadline_labels = [d["due_date"] for d in snapshot["deadlines"].values()]
    assert len(open_deadline_labels) >= 1

    # ...but never physically removed - the graph should still contain both.
    r = seeded_client.get(f"/api/cases/{case['id']}/graph")
    graph = r.json()
    deadline_nodes = [n for n in graph["nodes"] if n["type"] == "DEADLINE"]
    assert len(deadline_nodes) >= 2  # original + amended, both retained
