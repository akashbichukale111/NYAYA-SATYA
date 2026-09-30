"""
DEMO data seeder.

Creates 3 synthetic, clearly-labeled demo cases entirely offline (no LLM
API key required -- uses the same rule-based extraction agents as
production document ingestion, run against synthetic .txt "documents").

DEMONSTRATION DATA -- NOT A REAL CASE.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime, timedelta
from app.db.session import SessionLocal, init_db
from app.models import orm
from app.agents.extraction import DocumentIntakeAgent
from app.agents.reconciliation import run_all_reconciliation
from app.agents.attention import run_attention_engine
from app.agents.dependency import rebuild_dependency_graph
from app.agents.time_machine import take_snapshot
from app.core.enums import DocumentStatus, ExtractionMethod

intake_agent = DocumentIntakeAgent()


def _make_doc(db, case_id, filename, text, doc_type="OTHER"):
    doc = orm.Document(
        case_id=case_id, filename=filename, safe_filename=f"demo_{filename}",
        document_type=doc_type, mime_type="text/plain", size_bytes=str(len(text)),
        sha256=f"demo-sha-{filename}", status=DocumentStatus.PARSED.value,
        extraction_method=ExtractionMethod.PLAIN_TEXT.value, extracted_text=text,
        uploaded_by_user_id="demo-seed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _ingest(db, case_id, doc):
    extracted = intake_agent.process(doc.id, doc.extracted_text)
    for c in extracted["custody_events"]:
        db.add(orm.CustodyEvent(
            case_id=case_id, event_type=c.fields["event_type"], event_date=c.date_iso,
            date_type=c.date_type, verification_status="SOURCE_FACT",
            source_document_id=doc.id, source_text_snippet=c.source_text_snippet,
            extraction_method=doc.extraction_method,
        ))
    for h in extracted["hearings"]:
        db.add(orm.Hearing(
            case_id=case_id, hearing_date=h.date_iso, date_type=h.date_type,
            purpose=h.fields.get("purpose"), status=h.fields.get("status"),
            verification_status="SOURCE_FACT", source_document_id=doc.id,
            source_text_snippet=h.source_text_snippet, extraction_method=doc.extraction_method,
        ))
    for o in extracted["orders"]:
        db.add(orm.Order(
            case_id=case_id, status=o.fields.get("status"), summary=o.fields.get("summary"),
            mentioned_date=o.date_iso, date_type=o.date_type, verification_status="SOURCE_FACT",
            source_document_id=doc.id, source_text_snippet=o.source_text_snippet,
            extraction_method=doc.extraction_method,
        ))
    for b in extracted["bail_events"]:
        db.add(orm.BailEvent(
            case_id=case_id, event_type=b.fields.get("event_type"), summary=b.fields.get("summary"),
            event_date=b.date_iso, date_type=b.date_type, verification_status="SOURCE_FACT",
            source_document_id=doc.id, source_text_snippet=b.source_text_snippet,
            extraction_method=doc.extraction_method,
        ))
    for r in extracted["release_events"]:
        db.add(orm.ReleaseRelatedEvent(
            case_id=case_id, event_type=r.fields.get("event_type"), summary=r.fields.get("summary"),
            event_date=r.date_iso, date_type=r.date_type,
            current_status_confidence="CURRENT_STATUS_UNVERIFIED",
            verification_status="SOURCE_FACT", source_document_id=doc.id,
            source_text_snippet=r.source_text_snippet, extraction_method=doc.extraction_method,
        ))
    db.commit()


def seed_demo_a_clean_timeline(db):
    """Demo A: a well-documented custody/hearing/order timeline with no gaps."""
    case = orm.Case(case_reference="DEMO-A-001", title="Demo A -- Clean Timeline",
                     jurisdiction_note="Synthetic demonstration jurisdiction", is_demo=True,
                     created_by_user_id="demo-seed")
    db.add(case)
    db.commit()
    db.refresh(case)
    db.add(orm.Person(case_id=case.id, full_name="Demo Person A", role_in_case="UNDERTRIAL"))
    db.commit()

    d1 = _make_doc(db, case.id, "arrest_memo.txt",
                    "Arrest memo. The accused was arrested on 3 January 2026 in connection with the case. "
                    "Police custody was recorded from the date of arrest.")
    _ingest(db, case.id, d1)

    d2 = _make_doc(db, case.id, "remand_order.txt",
                    "Remand order. The accused was remanded to judicial custody on 5 January 2026 by the "
                    "magistrate. Next hearing on 20 January 2026.")
    _ingest(db, case.id, d2)

    d3 = _make_doc(db, case.id, "bail_application.txt",
                    "Bail application filed on 10 January 2026 on behalf of the accused. "
                    "Bail hearing scheduled for 20 January 2026.")
    _ingest(db, case.id, d3)

    d4 = _make_doc(db, case.id, "bail_order.txt",
                    "Bail order. Following the hearing on 20 January 2026, an order was passed. "
                    "Order issued granting release on furnishing surety. Release order recorded.")
    _ingest(db, case.id, d4)

    d5 = _make_doc(db, case.id, "release_document.txt",
                    "Release document received confirming the release order was executed at the district "
                    "prison on 22 January 2026.")
    _ingest(db, case.id, d5)

    run_all_reconciliation(db, case.id)
    run_attention_engine(db, case.id)
    rebuild_dependency_graph(db, case.id)
    db.commit()
    take_snapshot(db, case.id, "demo_seed_initial")
    return case


def seed_demo_b_conflicting_records(db):
    """Demo B: two records contain conflicting custody information -> surfaced conflict + human review."""
    case = orm.Case(case_reference="DEMO-B-002", title="Demo B -- Conflicting Records",
                     jurisdiction_note="Synthetic demonstration jurisdiction", is_demo=True,
                     created_by_user_id="demo-seed")
    db.add(case)
    db.commit()
    db.refresh(case)
    db.add(orm.Person(case_id=case.id, full_name="Demo Person B", role_in_case="UNDERTRIAL"))
    db.commit()

    d1 = _make_doc(db, case.id, "police_station_record.txt",
                    "Station record. The accused was arrested on 12 February 2026 as per the station diary.")
    _ingest(db, case.id, d1)

    d2 = _make_doc(db, case.id, "prison_intake_record.txt",
                    "Prison intake record. The accused was arrested on 14 February 2026 according to the "
                    "intake register maintained at the district prison.")
    _ingest(db, case.id, d2)

    d3 = _make_doc(db, case.id, "hearing_notice.txt",
                    "Hearing notice. A hearing is listed on 28 February 2026 to consider custody status.")
    _ingest(db, case.id, d3)

    run_all_reconciliation(db, case.id)
    run_attention_engine(db, case.id)
    rebuild_dependency_graph(db, case.id)
    db.commit()

    # NOTE: reconciliation.py now auto-creates a CONFLICT_RESOLUTION ReviewTask
    # for every conflict it detects, so no manual review-task creation is
    # needed here anymore (it used to be, before that fix -- see
    # docs/PROJECT_STATUS.md for the reconciliation.py changelog).
    take_snapshot(db, case.id, "demo_seed_initial")
    return case


def seed_demo_c_missing_event_chain(db):
    """Demo C: a hearing exists but the result/order is missing -> procedural gap identified."""
    case = orm.Case(case_reference="DEMO-C-003", title="Demo C -- Missing Event Chain",
                     jurisdiction_note="Synthetic demonstration jurisdiction", is_demo=True,
                     created_by_user_id="demo-seed")
    db.add(case)
    db.commit()
    db.refresh(case)
    db.add(orm.Person(case_id=case.id, full_name="Demo Person C", role_in_case="UNDERTRIAL"))
    db.commit()

    d1 = _make_doc(db, case.id, "arrest_and_remand.txt",
                    "The accused was arrested on 1 March 2026. The accused was remanded to judicial custody "
                    "on 2 March 2026.")
    _ingest(db, case.id, d1)

    d2 = _make_doc(db, case.id, "hearing_notice_past.txt",
                    "Hearing notice. A bail hearing was listed on 15 March 2026 to consider the pending "
                    "bail application filed on 5 March 2026.")
    _ingest(db, case.id, d2)
    # Deliberately: no order document is ever ingested for this hearing, and the hearing date
    # (15 March 2026) is in the past relative to typical demo "current date" -- so the attention
    # engine should surface PAST_TRACKED_DATE / MISSING_HEARING_RESULT / MISSING_ORDER.

    run_all_reconciliation(db, case.id)
    run_attention_engine(db, case.id, today=datetime(2026, 4, 1).date())
    rebuild_dependency_graph(db, case.id)
    db.commit()
    take_snapshot(db, case.id, "demo_seed_initial")
    return case


def seed_all():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(orm.Case).filter(orm.Case.is_demo == True).count()  # noqa: E712
        if existing > 0:
            print(f"Demo cases already present ({existing}). Skipping seed.")
            return
        a = seed_demo_a_clean_timeline(db)
        b = seed_demo_b_conflicting_records(db)
        c = seed_demo_c_missing_event_chain(db)
        print("Seeded demo cases:")
        print(" A (clean timeline):        ", a.id)
        print(" B (conflicting records):   ", b.id)
        print(" C (missing event chain):   ", c.id)
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
