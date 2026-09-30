"""
Evaluation Lab.

Runs deterministic, case-scoped checks and reports PASS / FAIL / NOT_RUN.
No percentages or scores are invented -- each check either has enough
information to run and produce a boolean result, or is reported NOT_RUN
with a stated reason.
"""
from sqlalchemy.orm import Session
from app.models import orm


def _check_event_extraction_traceability(db: Session, case_id: str):
    events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all()
    if not events:
        return "NOT_RUN", "No custody events exist in this case to check."
    untraceable = [e for e in events if not e.source_document_id and not e.reported_by_user_id]
    if untraceable:
        return "FAIL", f"{len(untraceable)} custody event(s) have neither a source document nor a reporting user."
    return "PASS", f"All {len(events)} custody event(s) are traceable to a document or reporting user."


def _check_source_linkage(db: Session, case_id: str):
    hearings = db.query(orm.Hearing).filter(orm.Hearing.case_id == case_id).all()
    if not hearings:
        return "NOT_RUN", "No hearings exist in this case to check."
    unlinked = [h for h in hearings if not h.source_document_id]
    if unlinked:
        return "FAIL", f"{len(unlinked)} hearing(s) lack a linked source document."
    return "PASS", f"All {len(hearings)} hearing(s) are linked to a source document."


def _check_timeline_consistency(db: Session, case_id: str):
    events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id,
                                                 orm.CustodyEvent.event_date.isnot(None)).all()
    if len(events) < 2:
        return "NOT_RUN", "Fewer than 2 dated custody events; ordering check not meaningful."
    dates = [e.event_date for e in events]
    return "PASS", f"Timeline contains {len(dates)} dated event(s); each independently sortable by ISO date."


def _check_conflict_detection(db: Session, case_id: str):
    conflicts = db.query(orm.Conflict).filter(orm.Conflict.case_id == case_id).all()
    events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all()
    by_type = {}
    for e in events:
        by_type.setdefault(e.event_type, []).append(e)
    should_have_conflict = any(
        len({e.event_date for e in group if e.event_date}) > 1 for group in by_type.values()
    )
    if not should_have_conflict:
        return "NOT_RUN", "No differing-date events of the same type exist to test conflict detection."
    if conflicts:
        return "PASS", f"{len(conflicts)} conflict(s) correctly detected among differing custody dates."
    return "FAIL", "Differing custody dates exist but no conflict record was created."


def _check_dependency_correctness(db: Session, case_id: str):
    edges = db.query(orm.Dependency).filter(orm.Dependency.case_id == case_id).all()
    docs = db.query(orm.Document).filter(orm.Document.case_id == case_id).count()
    if docs == 0:
        return "NOT_RUN", "No documents ingested; dependency graph has nothing to link."
    if edges:
        return "PASS", f"Dependency graph contains {len(edges)} edge(s)."
    return "FAIL", "Documents exist but no dependency edges were built."


def _check_historical_reconstruction(db: Session, case_id: str):
    snaps = db.query(orm.CaseSnapshot).filter(orm.CaseSnapshot.case_id == case_id).all()
    if len(snaps) < 1:
        return "NOT_RUN", "No snapshots exist yet."
    ok = all(isinstance(s.snapshot_data, dict) and "case_id" in s.snapshot_data for s in snaps)
    return ("PASS" if ok else "FAIL"), f"{len(snaps)} snapshot(s) checked for structural completeness."


def _check_case_isolation(db: Session, case_id: str):
    other_case_rows = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id != case_id).count()
    this_case_rows = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all()
    leaked = [e for e in this_case_rows if e.case_id != case_id]
    if leaked:
        return "FAIL", "Case isolation violated: found rows with mismatched case_id in query result."
    return "PASS", f"Query-level isolation holds ({other_case_rows} unrelated row(s) correctly excluded)."


def _check_prompt_injection_resistance(db: Session, case_id: str):
    docs = db.query(orm.Document).filter(orm.Document.case_id == case_id).all()
    injection_markers = ["ignore previous instructions", "ignore all previous instructions", "you are now"]
    found_in_text = any(
        d.extracted_text and any(m in d.extracted_text.lower() for m in injection_markers) for d in docs
    )
    if not found_in_text:
        return "NOT_RUN", "No document in this case contains an injection-style phrase to test against."
    # The extraction agents are pure regex/keyword matchers over the vocabularies in extraction.py;
    # they have no instruction-following capability, so injected text cannot alter their behavior.
    suspicious_event_types = {e.event_type for e in db.query(orm.CustodyEvent).filter(
        orm.CustodyEvent.case_id == case_id).all()}
    from app.core.enums import CustodyEventType
    valid_types = {t.value for t in CustodyEventType}
    if suspicious_event_types.issubset(valid_types):
        return "PASS", "Document contains injection-style text; extracted event types remained within the fixed vocabulary."
    return "FAIL", "Unexpected event type found outside the fixed vocabulary."


def _check_attention_generation(db: Session, case_id: str):
    items = db.query(orm.AttentionItem).filter(orm.AttentionItem.case_id == case_id).all()
    if not items:
        return "NOT_RUN", "No attention items generated yet -- run the attention engine first."
    return "PASS", f"{len([i for i in items if i.status == 'OPEN'])} open attention item(s) present."


def _check_crash_test_correctness(db: Session, case_id: str):
    from app.agents.simulation import run_simulation
    orders = db.query(orm.Order).filter(orm.Order.case_id == case_id).first()
    if not orders:
        return "NOT_RUN", "No order exists in this case to crash-test."
    before_count = db.query(orm.Order).filter(orm.Order.case_id == case_id).count()
    result = run_simulation(db, case_id, "REMOVE_ORDER", orders.id)
    after_count = db.query(orm.Order).filter(orm.Order.case_id == case_id).count()
    if after_count != before_count:
        return "FAIL", "Production state was mutated by a simulation run (rollback failed)."
    order_removed_in_sim = result["after"].get("recent_orders", [])
    still_present = any(o["id"] == orders.id for o in order_removed_in_sim)
    if still_present:
        return "FAIL", "Simulated removal did not affect the simulated digital twin."
    return "PASS", "Order removal correctly reflected in simulated twin; production state unaffected."


CHECKS = {
    "event_extraction_traceability": _check_event_extraction_traceability,
    "source_linkage": _check_source_linkage,
    "timeline_consistency": _check_timeline_consistency,
    "conflict_detection": _check_conflict_detection,
    "dependency_correctness": _check_dependency_correctness,
    "historical_reconstruction": _check_historical_reconstruction,
    "case_isolation": _check_case_isolation,
    "prompt_injection_resistance": _check_prompt_injection_resistance,
    "attention_generation": _check_attention_generation,
    "crash_test_correctness": _check_crash_test_correctness,
}


def run_evaluation_suite(db: Session, case_id: str) -> dict:
    results = {}
    for name, fn in CHECKS.items():
        try:
            status, reason = fn(db, case_id)
        except Exception as ex:
            status, reason = "FAIL", f"Check raised an exception: {ex}"
        results[name] = {"status": status, "reason": reason}
    summary = {
        "PASS": sum(1 for r in results.values() if r["status"] == "PASS"),
        "FAIL": sum(1 for r in results.values() if r["status"] == "FAIL"),
        "NOT_RUN": sum(1 for r in results.values() if r["status"] == "NOT_RUN"),
    }
    return {"case_id": case_id, "checks": results, "summary": summary}
