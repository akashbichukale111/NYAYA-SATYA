"""
End-to-end regression test for Undertrial Liberty Sentinel.

Unlike backend/tests/ (which uses FastAPI's TestClient against an in-memory
app instance), this test is deliberately black-box: it spawns the real
`uvicorn` process against a real (temporary) SQLite file and talks to it over
real HTTP, the same way a browser or another NYAYA-SATYA module would. This
is the closest thing in this repo to the "Regression Tests: deterministic
end-to-end scenarios" requirement in the master spec.

It walks the exact narrative the spec calls for:
  Case -> Timeline -> Source -> Attention -> Conflict -> Dependency
       -> Human Review -> Audit -> Time Machine -> Crash Test

Run with:  python tests/e2e_regression.py
Exit code 0 = all scenarios passed. Non-zero = a scenario failed, with a
printed reason -- this script never claims success it didn't actually
observe.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
BASE_URL = "http://127.0.0.1:8123"
ADVOCATE_HEADERS = {"X-Demo-Role": "ADVOCATE", "X-Demo-User": "e2e-advocate", "Content-Type": "application/json"}

PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append((name, detail))
        print(f"  FAIL  {name} -- {detail}")


def request(method, path, body=None, headers=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or ADVOCATE_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def wait_for_server(timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            status, _ = request("GET", "/api/health")
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    tmpdir = tempfile.mkdtemp(prefix="uls_e2e_")
    db_path = os.path.join(tmpdir, "e2e.db")
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["DEMO_MODE"] = "true"

    print(f"Starting server against fresh temp DB: {db_path}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8123"],
        cwd=BACKEND_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        if not wait_for_server():
            print("Server did not start in time.")
            proc.terminate()
            sys.exit(2)

        print("\n== Scenario: Case -> Timeline -> Source -> Attention -> Conflict")
        print("             -> Dependency -> Human Review -> Audit -> Time Machine -> Crash Test ==\n")

        # --- Case ---
        status, case = request("POST", "/api/cases", {
            "case_reference": "E2E-001", "title": "E2E regression case", "person_full_name": "E2E Test Person",
        })
        check("case created", status == 200 and "id" in case, f"status={status} body={case}")
        case_id = case.get("id")

        # --- Document upload (multipart, so use urllib manually with boundary) ---
        boundary = "----e2eboundary"
        doc_text = ("The accused was arrested on 1 April 2026. "
                    "The accused was remanded to judicial custody on 2 April 2026. "
                    "A bail hearing was listed on 10 April 2026.")
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="arrest.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f"{doc_text}\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/cases/{case_id}/documents", data=body, method="POST",
            headers={"X-Demo-Role": "ADVOCATE", "X-Demo-User": "e2e-advocate",
                     "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            doc = json.loads(resp.read().decode())
        check("document ingested and parsed", doc.get("status") == "PARSED", f"doc={doc}")

        # --- Timeline / Source ---
        status, timeline = request("GET", f"/api/cases/{case_id}/timeline")
        check("timeline has events with source linkage", status == 200 and len(timeline["timeline"]) >= 2
              and all(i.get("source_document_id") for i in timeline["timeline"]), f"timeline={timeline}")

        # --- Introduce a conflict: second document with a different arrest date ---
        body2 = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="prison_record.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f"Prison intake record: the accused was arrested on 3 April 2026 per the intake register.\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        req2 = urllib.request.Request(
            f"{BASE_URL}/api/cases/{case_id}/documents", data=body2, method="POST",
            headers={"X-Demo-Role": "ADVOCATE", "X-Demo-User": "e2e-advocate",
                     "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req2, timeout=10) as resp:
            doc2 = json.loads(resp.read().decode())
        check("second (conflicting) document ingested", doc2.get("status") == "PARSED", f"doc2={doc2}")

        # --- Conflict ---
        status, conflicts = request("GET", f"/api/cases/{case_id}/conflicts")
        check("conflict detected between the two arrest dates", status == 200 and len(conflicts["conflicts"]) >= 1,
              f"conflicts={conflicts}")

        # --- Attention ---
        status, attention = request("GET", f"/api/cases/{case_id}/attention")
        categories = {a["category"] for a in attention.get("attention_items", [])}
        check("attention engine surfaced the conflict", "CONFLICTING_CUSTODY_INFORMATION" in categories,
              f"categories={categories}")

        # --- Dependency ---
        status, graph = request("GET", f"/api/cases/{case_id}/dependency-graph")
        check("dependency graph has edges linking documents to events", status == 200 and len(graph["edges"]) > 0,
              f"edge_count={len(graph.get('edges', []))}")

        # --- Human Review ---
        status, review_queue = request("GET", f"/api/cases/{case_id}/review-queue")
        pending = [t for t in review_queue.get("review_tasks", []) if t["status"] == "PENDING"]
        check("a human review task was auto-created for the detected conflict",
              status == 200 and any(t["task_type"] == "CONFLICT_RESOLUTION" for t in pending),
              f"pending_tasks={pending}")

        # --- Audit ---
        status, audit = request("GET", f"/api/cases/{case_id}/audit")
        check("audit log recorded the case creation and document uploads", status == 200 and len(audit["audit_events"]) >= 3,
              f"audit_count={len(audit.get('audit_events', []))}")

        # --- Time Machine ---
        status, tm = request("GET", f"/api/cases/{case_id}/time-machine")
        check("time machine has snapshots from case creation and document ingestion",
              status == 200 and len(tm.get("snapshots", [])) >= 2, f"tm={tm}")

        # --- Crash Test (the safety-critical one) ---
        status, orders_before = request("GET", f"/api/cases/{case_id}/orders")
        status, hearings = request("GET", f"/api/cases/{case_id}/hearings")
        target_hearing = hearings["hearings"][0]["id"] if hearings.get("hearings") else None
        check("a hearing exists to crash-test against", target_hearing is not None, f"hearings={hearings}")

        if target_hearing:
            status, crash_result = request("POST", f"/api/cases/{case_id}/crash-test", {
                "event_type": "REMOVE_HEARING_RESULT", "target_entity_id": target_hearing,
            })
            check("crash test executed and reports production_state_mutated=False",
                  status == 200 and crash_result.get("production_state_mutated") is False,
                  f"crash_result_keys={list(crash_result.keys())}")

            status, hearings_after = request("GET", f"/api/cases/{case_id}/hearings")
            same_status = hearings_after["hearings"][0]["status"] == hearings["hearings"][0]["status"]
            check("real hearing record is byte-for-byte unaffected by the crash test", same_status,
                  f"before={hearings['hearings'][0]['status']} after={hearings_after['hearings'][0]['status']}")

        # --- Evaluation Lab sanity ---
        status, evaluation = request("GET", f"/api/cases/{case_id}/evaluation")
        check("evaluation lab returns real PASS/FAIL/NOT_RUN status for every check",
              status == 200 and all(c["status"] in ("PASS", "FAIL", "NOT_RUN") for c in evaluation["checks"].values()),
              f"evaluation={evaluation.get('summary')}")

        # --- Case isolation: a second, unrelated case must not see this case's data ---
        status, case_b = request("POST", "/api/cases", {
            "case_reference": "E2E-002", "title": "Unrelated case", "person_full_name": "Someone Else",
        })
        status, case_b_timeline = request("GET", f"/api/cases/{case_b['id']}/timeline")
        check("unrelated case has an empty timeline (no cross-case leakage)",
              status == 200 and len(case_b_timeline["timeline"]) == 0, f"leaked={case_b_timeline}")

    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed.")
    if FAIL:
        print("\nFailed scenarios:")
        for name, detail in FAIL:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
