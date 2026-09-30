from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..database import get_session
from ..models import Case
from ..schemas import SimulateRequest, CrashTestRequest
from .. import simulation as sim

router = APIRouter(prefix="/api/cases", tags=["simulation"])


@router.post("/{case_id}/simulate")
def simulate(case_id: str, body: SimulateRequest, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return sim.simulate_removal(session, case_id, body.dependency_id)


@router.post("/{case_id}/collapse-test")
def collapse_test(case_id: str, body: SimulateRequest, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return sim.collapse_test(session, case_id, body.dependency_id)


@router.post("/{case_id}/crash-test")
def crash_test(case_id: str, body: CrashTestRequest, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return sim.run_crash_test(session, case_id, body.mutation, body.target_dependency_id)


@router.get("/{case_id}/crash-test/mutations")
def list_mutations():
    return sim.MUTATIONS


def _require_case(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case
