"""
Fact Status Engine + Conflict Engine + Missing Information Engine.

These are deterministic, rule-based engines over structured Fact/TimelineEvent
rows — they do NOT call an LLM. This keeps status/conflict classification
auditable and reproducible, per the "structured facts > free-form
hallucination" principle in the master prompt.
"""
from collections import defaultdict
from sqlalchemy.orm import Session

from models import Fact, FactStatus, Conflict, ConflictType, TimelineEvent, Deadline, Document, Question


def recompute_conflicts(db: Session, case_id: str) -> list[Conflict]:
    """Scan facts + timeline events for the same case for contradictions.

    Detects DATE_CONFLICT (same labeled event reported with two different
    dates across sources) as the primary demo-visible case; the other
    ConflictType values are scaffolded for future rule additions and are
    NOT yet auto-detected (tracked in docs/LIMITATIONS.md).
    """
    # clear previously auto-detected, unresolved conflicts before recomputing
    db.query(Conflict).filter(Conflict.case_id == case_id, Conflict.resolved == False).delete()  # noqa: E712
    db.commit()

    events = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).all()
    by_label = defaultdict(list)
    for e in events:
        key = e.description.split(":")[0].strip().lower() if ":" in e.description else e.description.lower()[:40]
        by_label[key].append(e)

    created = []
    for key, group in by_label.items():
        dates = {e.event_date for e in group if e.event_date}
        if len(dates) > 1:
            conf = Conflict(
                case_id=case_id,
                conflict_type=ConflictType.DATE_CONFLICT,
                description=(
                    f"Multiple dates reported for '{key}': "
                    + ", ".join(sorted(dates))
                    + ". Human review required — system does not decide which is correct."
                ),
                fact_ids=[e.id for e in group],
            )
            db.add(conf)
            created.append(conf)
    db.commit()
    for c in created:
        db.refresh(c)
    return created


def missing_information_report(db: Session, case_id: str) -> list[dict]:
    """Section 11/40: identify gaps and, for each, why/who/how/urgency."""
    report = []

    deadlines = db.query(Deadline).filter(Deadline.case_id == case_id).all()
    if not deadlines:
        report.append({
            "item": "Known deadline or hearing date",
            "why_needed": "Determines urgency of handoff and review priority",
            "who_may_know": "Citizen, or the notice/order document itself",
            "how_obtained": "Ask citizen directly, or check uploaded notice/order for a date",
            "urgency": "high",
            "source_requirement": "USER_REPORTED or DOCUMENT_SUPPORTED",
        })

    docs = db.query(Document).filter(Document.case_id == case_id).all()
    if not docs:
        report.append({
            "item": "Supporting document (notice, order, receipt, or photo)",
            "why_needed": "Facts currently rest only on the citizen's account with no document support",
            "who_may_know": "Citizen",
            "how_obtained": "Request citizen upload any paper related to the issue",
            "urgency": "medium",
            "source_requirement": "DOCUMENT_SUPPORTED",
        })

    unresolved_qs = db.query(Question).filter(Question.case_id == case_id, Question.resolved == False).all()  # noqa: E712
    for q in unresolved_qs:
        report.append({
            "item": q.text,
            "why_needed": q.reason or "Needed to complete case context",
            "who_may_know": "Citizen",
            "how_obtained": "Ask citizen in plain language",
            "urgency": q.priority,
            "source_requirement": "USER_REPORTED",
        })

    facts = db.query(Fact).filter(Fact.case_id == case_id).all()
    if not any(f.status in (FactStatus.VERIFIED, FactStatus.DOCUMENT_SUPPORTED) for f in facts):
        report.append({
            "item": "Any document- or officially-verified fact",
            "why_needed": "Every current fact is only USER_REPORTED — a reviewer cannot cross-check the account",
            "who_may_know": "Citizen or issuing authority",
            "how_obtained": "Obtain the underlying notice/order/receipt",
            "urgency": "medium",
            "source_requirement": "DOCUMENT_SUPPORTED",
        })

    return report


def intake_completeness(db: Session, case_id: str) -> dict:
    """Section 12: explainable completeness by category, no arbitrary %."""
    case_facts = db.query(Fact).filter(Fact.case_id == case_id).all()
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).all()
    deadlines = db.query(Deadline).filter(Deadline.case_id == case_id).all()
    questions = db.query(Question).filter(Question.case_id == case_id).all()

    def level(n, partial_ok=True):
        if n == 0:
            return "MISSING"
        if partial_ok and n < 2:
            return "PARTIAL"
        return "COMPLETE"

    return {
        "IDENTITY": "PARTIAL" if case_facts else "MISSING",
        "CASE_HISTORY": level(len(timeline)),
        "DOCUMENTS": level(len(docs)),
        "TIMELINE": level(len(timeline)),
        "DEADLINES": level(len(deadlines)),
        "REQUESTED_HELP": "COMPLETE",
        "UNRESOLVED_QUESTIONS": "PARTIAL" if any(not q.resolved for q in questions) else "COMPLETE",
    }
