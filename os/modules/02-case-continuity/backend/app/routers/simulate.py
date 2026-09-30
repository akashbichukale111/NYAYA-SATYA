from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, StateVersion, Simulation
from app.state_twin import build_snapshot
from app.simulation import simulate_counterfactual_removal, simulate_field_change, project_future_states

router = APIRouter(prefix="/api/cases", tags=["simulate"])


class CounterfactualRemoval(BaseModel):
    collection: str
    entity_id: str
    base_version_number: int | None = None


class FieldChange(BaseModel):
    collection: str
    entity_id: str
    field: str
    new_value: str
    base_version_number: int | None = None


class FutureStateQuery(BaseModel):
    current_event_type: str


def _base_snapshot(db: Session, case_id: str, version_number: int | None) -> tuple[dict, int]:
    if version_number is not None:
        v = db.query(StateVersion).filter(
            StateVersion.case_id == case_id, StateVersion.version_number == version_number).first()
        if not v:
            raise HTTPException(404, "base version not found")
        return v.snapshot, version_number
    case = db.get(Case, case_id)
    return build_snapshot(db, case_id), case.current_version_number


@router.post("/{case_id}/simulate/remove")
def simulate_remove(case_id: str, payload: CounterfactualRemoval, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    snapshot, version_number = _base_snapshot(db, case_id, payload.base_version_number)
    result = simulate_counterfactual_removal(snapshot, collection=payload.collection, entity_id=payload.entity_id)
    sim = Simulation(case_id=case_id, base_version_number=version_number, hypothesis=result["hypothesis"],
                      result_snapshot=result)
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return {**result, "simulation_id": sim.id}


@router.post("/{case_id}/simulate/field-change")
def simulate_change(case_id: str, payload: FieldChange, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    snapshot, version_number = _base_snapshot(db, case_id, payload.base_version_number)
    result = simulate_field_change(
        snapshot, collection=payload.collection, entity_id=payload.entity_id,
        field=payload.field, new_value=payload.new_value,
    )
    sim = Simulation(case_id=case_id, base_version_number=version_number, hypothesis=result["hypothesis"],
                      result_snapshot=result)
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return {**result, "simulation_id": sim.id}


@router.post("/{case_id}/simulate/future-state")
def simulate_future(case_id: str, payload: FutureStateQuery, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    return project_future_states(payload.current_event_type)


@router.get("/{case_id}/simulate/history")
def simulation_history(case_id: str, db: Session = Depends(get_db)):
    sims = db.query(Simulation).filter(Simulation.case_id == case_id).order_by(Simulation.created_at.desc()).all()
    return [
        {"id": s.id, "base_version_number": s.base_version_number, "hypothesis": s.hypothesis,
         "created_at": s.created_at.isoformat(), "label": s.label}
        for s in sims
    ]
