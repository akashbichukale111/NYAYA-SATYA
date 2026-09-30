"""
Flagship demo walkthrough.

Prints the spec's required narrative --
  Open Demo Case -> Inspect Custody Timeline -> Open Source -> Inspect Hearing
  -> Detect Missing/Conflicting Event -> Open Attention Center
  -> Inspect Dependency -> Run Crash Test -> Review Result
  -> Open Time Machine -> Inspect Audit
-- using REAL data pulled live from a running backend. This is a narration
tool for demonstrations, not a test (see tests/e2e_regression.py for the
automated version of this same flow with pass/fail assertions).

Usage:
    1. In one terminal: cd backend && python -m app.db.seed_demo && uvicorn app.main:app --port 8000
    2. In another terminal: python demo/walkthrough.py --case B
       (--case A | B | C, defaults to B, the conflicting-records case)
"""
import argparse
import json
import sys
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"X-Demo-Role": "ADVOCATE", "X-Demo-User": "demo-walkthrough", "Content-Type": "application/json"}

CASE_REFS = {"A": "DEMO-A-001", "B": "DEMO-B-002", "C": "DEMO-C-003"}


def get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method="POST", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def find_case(ref):
    cases = get("/api/cases")
    match = next((c for c in cases if c["case_reference"] == ref), None)
    if not match:
        print(f"Case {ref} not found. Have you run `python -m app.db.seed_demo`?")
        sys.exit(1)
    return match


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["A", "B", "C"], default="B")
    args = parser.parse_args()

    try:
        get("/api/health")
    except Exception:
        print(f"Could not reach backend at {BASE_URL}. Start it first: "
              f"cd backend && uvicorn app.main:app --port 8000")
        sys.exit(1)

    case = find_case(CASE_REFS[args.case])
    case_id = case["id"]

    section(f"OPEN DEMO CASE — {case['title']} ({case['case_reference']})")
    print(f"is_demo: {case['is_demo']}  (rendered in UI as: DEMONSTRATION DATA — NOT A REAL CASE)")

    section("INSPECT CUSTODY TIMELINE")
    timeline = get(f"/api/cases/{case_id}/timeline")
    for item in timeline["timeline"][:8]:
        print(f"  [{item['date'] or 'UNKNOWN_DATE':>10}] {item['kind']:15} {item.get('label', '')[:60]}")
    print(f"  ... {len(timeline['timeline'])} total item(s), {timeline['undated_count']} undated")

    section("OPEN SOURCE (first timeline item with a document)")
    sourced = next((i for i in timeline["timeline"] if i.get("source_document_id")), None)
    if sourced:
        print(f"  document_id: {sourced['source_document_id']}")
    else:
        print("  No source-linked item found.")

    section("INSPECT HEARINGS")
    hearings = get(f"/api/cases/{case_id}/hearings")
    for h in hearings["hearings"]:
        print(f"  {h['id']}: status={h['status']} date={h['hearing_date']} verification={h['verification_status']}")

    section("DETECT MISSING/CONFLICTING EVENTS")
    conflicts = get(f"/api/cases/{case_id}/conflicts")
    print(f"  Open conflicts: {len(conflicts['conflicts'])}")
    for c in conflicts["conflicts"]:
        print(f"    field={c['field_name']}  '{c['value_a']}'  vs  '{c['value_b']}'  status={c['status']}")

    section("OPEN ATTENTION CENTER")
    attention = get(f"/api/cases/{case_id}/attention")
    for a in attention["attention_items"]:
        print(f"  [{a['severity']:22}] {a['category']:32} {a['reason'][:70]}")

    section("INSPECT DEPENDENCY GRAPH")
    graph = get(f"/api/cases/{case_id}/dependency-graph")
    print(f"  {len(graph['edges'])} edge(s) total")
    blocked = [e for e in graph["edges"] if e["status"] == "BLOCKED"]
    print(f"  {len(blocked)} BLOCKED edge(s)")

    section("RUN CRASH TEST (guaranteed rollback — production data untouched)")
    if hearings["hearings"]:
        target = hearings["hearings"][0]["id"]
        result = post(f"/api/cases/{case_id}/crash-test",
                       {"event_type": "REMOVE_HEARING_RESULT", "target_entity_id": target})
        print(f"  event_type: REMOVE_HEARING_RESULT on hearing {target}")
        print(f"  production_state_mutated: {result['production_state_mutated']}")
        print(f"  new attention items in simulation: {len(result['affected_attention_items'])}")
        print(f"  human_review_required: {result['human_review_required']}")
    else:
        print("  No hearing available to crash-test in this case.")

    section("REVIEW RESULT (Review Queue)")
    reviews = get(f"/api/cases/{case_id}/review-queue")
    for t in reviews["review_tasks"]:
        print(f"  {t['task_type']:22} status={t['status']:10} {t['description'][:60]}")
    if not reviews["review_tasks"]:
        print("  No review tasks in this case.")

    section("OPEN TIME MACHINE")
    tm = get(f"/api/cases/{case_id}/time-machine")
    for s in tm["snapshots"]:
        print(f"  {s['created_at']}  reason={s['reason']}")

    section("INSPECT AUDIT")
    audit = get(f"/api/cases/{case_id}/audit")
    for e in audit["audit_events"][:10]:
        print(f"  {e['created_at']}  {e['action']:8} {e.get('entity_type') or ''} by {e.get('actor_user_id')}")

    section("DONE")
    print(f"Case {case['case_reference']} walkthrough complete. Nothing above was fabricated — "
          f"every line came from a live GET/POST against {BASE_URL}.")


if __name__ == "__main__":
    main()
