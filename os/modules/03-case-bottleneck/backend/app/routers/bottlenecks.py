from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Bottleneck, RootCauseCandidate, Case
from ..orchestrator import run_full_investigation, compute_primary_bottleneck
from ..agents.impact import ImpactAgent

router = APIRouter(prefix="/api/cases", tags=["bottlenecks"])


@router.post("/{case_id}/investigate")
def investigate(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    result = run_full_investigation(session, case_id)
    primary = compute_primary_bottleneck(result["bottlenecks"])
    return {
        "correlation_id": result["correlation_id"],
        "bottleneck_count": len(result["bottlenecks"]),
        "primary_bottleneck_id": primary.id if primary else None,
        "bottlenecks": result["bottlenecks"],
    }


@router.get("/{case_id}/bottlenecks")
def list_bottlenecks(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    bottlenecks = session.exec(select(Bottleneck).where(Bottleneck.case_id == case_id)).all()
    primary = compute_primary_bottleneck(bottlenecks)
    return {
        "primary_bottleneck_id": primary.id if primary else None,
        "bottlenecks": bottlenecks,
    }


@router.get("/{case_id}/bottlenecks/{bottleneck_id}")
def get_bottleneck(case_id: str, bottleneck_id: str, session: Session = Depends(get_session)):
    bn = _require_bottleneck(session, case_id, bottleneck_id)
    root_causes = session.exec(
        select(RootCauseCandidate).where(RootCauseCandidate.bottleneck_id == bottleneck_id)
        .order_by(RootCauseCandidate.created_at.desc())
    ).all()
    impact = ImpactAgent().run(session, bn)
    return {"bottleneck": bn, "root_cause_candidates": root_causes, "impact": impact}


@router.get("/{case_id}/root-cause")
def get_root_cause(case_id: str, bottleneck_id: str = Query(...), session: Session = Depends(get_session)):
    _require_case(session, case_id)
    latest = session.exec(
        select(RootCauseCandidate).where(RootCauseCandidate.bottleneck_id == bottleneck_id)
        .order_by(RootCauseCandidate.created_at.desc())
    ).first()
    if not latest:
        raise HTTPException(404, "No root-cause analysis yet for this bottleneck — call /investigate first.")
    return latest


@router.get("/{case_id}/impact")
def get_impact(case_id: str, bottleneck_id: str = Query(...), session: Session = Depends(get_session)):
    bn = _require_bottleneck(session, case_id, bottleneck_id)
    return ImpactAgent().run(session, bn)


def _require_case(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


def _require_bottleneck(session: Session, case_id: str, bottleneck_id: str) -> Bottleneck:
    bn = session.get(Bottleneck, bottleneck_id)
    if not bn or bn.case_id != case_id:
        raise HTTPException(404, "Bottleneck not found for this case")
    return bn
