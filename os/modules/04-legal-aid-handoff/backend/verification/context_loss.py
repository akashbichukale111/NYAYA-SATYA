"""
Context Loss Engine (sec 20) + Handoff Fidelity Engine (sec 21).

Produces an explicit PRESERVED / LOST / CHANGED / NEW / UNSUPPORTED
classification — never a vague single "fidelity score".
"""
from sqlalchemy.orm import Session
from models import Fact, Document, Deadline, HandoffVersion, Case


def _snapshot(db: Session, case_id: str):
    """The full source case context at the time of comparison."""
    facts = {f.id: f for f in db.query(Fact).filter(Fact.case_id == case_id).all()}
    docs = {d.id: d for d in db.query(Document).filter(Document.case_id == case_id).all()}
    deadlines = {d.id: d for d in db.query(Deadline).filter(Deadline.case_id == case_id).all()}
    return facts, docs, deadlines


def compare_source_to_handoff(db: Session, case: Case, version: HandoffVersion) -> dict:
    """Section 20: original case context vs. what this handoff version transmits."""
    facts, docs, deadlines = _snapshot(db, case.id)

    preserved, lost, changed, unsupported = [], [], [], []
    included_fact_ids = set(version.included_fact_ids or [])
    for fid, f in facts.items():
        if fid in included_fact_ids:
            if f.status.value in ("UNKNOWN", "NOT_PROVIDED"):
                unsupported.append({"id": fid, "label": f.label})
            else:
                preserved.append({"id": fid, "label": f.label})
        else:
            lost.append({"id": fid, "label": f.label,
                          "reason": "excluded by recipient sensitivity ceiling or not selected for this packet"})

    included_doc_ids = set(version.included_document_ids or [])
    docs_lost = [{"id": did, "label": d.filename} for did, d in docs.items() if did not in included_doc_ids]
    deadlines_lost = [{"id": did, "label": d.description} for did, d in deadlines.items()
                       if did not in set(version.included_deadline_ids or [])]

    result = {
        "case_id": case.id,
        "handoff_version": version.version_number,
        "facts": {
            "total_source": len(facts),
            "preserved": preserved,
            "lost": lost,
            "unsupported": unsupported,
        },
        "documents": {"total_source": len(docs), "lost": docs_lost},
        "deadlines": {"total_source": len(deadlines), "lost": deadlines_lost},
        "context_loss_detected": bool(lost or docs_lost or deadlines_lost),
    }
    return result


def compare_versions(db: Session, v_from: HandoffVersion, v_to: HandoffVersion) -> dict:
    """Section 24/25: diff between two handoff versions of the SAME handoff."""
    from_ids = set(v_from.included_fact_ids or [])
    to_ids = set(v_to.included_fact_ids or [])

    added = to_ids - from_ids
    removed = from_ids - to_ids
    kept = from_ids & to_ids

    def label_of(fid):
        f = db.query(Fact).get(fid)
        return f.label if f else fid

    from_docs = set(v_from.included_document_ids or [])
    to_docs = set(v_to.included_document_ids or [])
    from_dl = set(v_from.included_deadline_ids or [])
    to_dl = set(v_to.included_deadline_ids or [])
    from_conf = set(v_from.included_conflict_ids or [])
    to_conf = set(v_to.included_conflict_ids or [])

    return {
        "from_version": v_from.version_number,
        "to_version": v_to.version_number,
        "facts": {
            "added": [{"id": i, "label": label_of(i)} for i in added],
            "removed": [{"id": i, "label": label_of(i)} for i in removed],
            "preserved": [{"id": i, "label": label_of(i)} for i in kept],
        },
        "documents": {"added": list(to_docs - from_docs), "removed": list(from_docs - to_docs)},
        "deadlines": {"added": list(to_dl - from_dl), "removed": list(from_dl - to_dl)},
        "conflicts_resolved": list(from_conf - to_conf),
        "conflicts_new": list(to_conf - from_conf),
    }


def verify_handoff(db: Session, version: HandoffVersion) -> dict:
    """Section 30: post-acknowledgement verification record."""
    ack = version.acknowledgement
    open_clarifications = [c for c in version.clarifications if not c.resolved]
    ok = ack is not None and ack.action in ("ACKNOWLEDGE", "ACCEPT") and not open_clarifications
    return {
        "handoff_version_id": version.id,
        "version_number": version.version_number,
        "acknowledged": ack is not None,
        "acknowledgement_action": ack.action if ack else None,
        "open_clarifications": len(open_clarifications),
        "result": "VERIFIED" if ok else "VERIFICATION_FAILED",
    }
