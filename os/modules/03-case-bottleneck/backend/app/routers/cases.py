from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Case, CaseEvent, CaseDocument, Bottleneck, BottleneckStatus, AuditEvent, BottleneckHistoryEntry
from ..agents.dependency import DependencyAgent

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def list_cases(session: Session = Depends(get_session)):
    cases = session.exec(select(Case)).all()
    out = []
    for c in cases:
        bottlenecks = session.exec(select(Bottleneck).where(Bottleneck.case_id == c.id)).all()
        open_count = len([b for b in bottlenecks if b.status != BottleneckStatus.RESOLVED])
        out.append({**c.model_dump(), "open_bottlenecks": open_count, "total_bottlenecks": len(bottlenecks)})
    return out


@router.get("/{case_id}")
def get_case(case_id: str, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("/{case_id}/flow")
def get_flow(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return DependencyAgent().graph_json(session, case_id)


@router.get("/{case_id}/dependencies")
def get_dependencies(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return DependencyAgent().graph_json(session, case_id)


@router.get("/{case_id}/events")
def get_events(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return session.exec(select(CaseEvent).where(CaseEvent.case_id == case_id)).all()


@router.get("/{case_id}/documents")
def get_documents(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return session.exec(select(CaseDocument).where(CaseDocument.case_id == case_id)).all()


@router.get("/{case_id}/history")
def get_history(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    entries = session.exec(
        select(BottleneckHistoryEntry).where(BottleneckHistoryEntry.case_id == case_id)
        .order_by(BottleneckHistoryEntry.timestamp)
    ).all()
    return entries


@router.get("/{case_id}/audit")
def get_audit(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    entries = session.exec(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.timestamp)
    ).all()
    return entries


@router.get("/{case_id}/flow-health")
def flow_health(case_id: str, session: Session = Depends(get_session)):
    """Section 31 — explicitly NOT reduced to a single unexplained score."""
    _require_case(session, case_id)
    bottlenecks = session.exec(select(Bottleneck).where(Bottleneck.case_id == case_id)).all()
    open_b = [b for b in bottlenecks if b.status != BottleneckStatus.RESOLVED]
    return {
        "open_bottlenecks": len(open_b),
        "resolved_bottlenecks": len(bottlenecks) - len(open_b),
        "unknown_confidence_count": len([b for b in open_b if b.confidence.value == "UNKNOWN"]),
        "contradiction_count": len([b for b in open_b if b.type.value == "CONTRADICTION_BLOCKER"]),
        "recurring_count": len([b for b in bottlenecks if b.recurrence_count > 0]),
        "total_blocked_transitions": len({t for b in open_b for t in b.affected_transitions}),
    }


def _require_case(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case
