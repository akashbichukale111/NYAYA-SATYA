"""
Router for the Section 2 analysis capabilities: verification re-checks,
the defect dependency graph, counterfactual simulation, and the registry
crash test. All of these are read-only or non-destructive — see each
service module's docstring for the specific guarantee.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_capability, assert_case_access
from app.core.audit import record as audit_record
from app import models, schemas
from app.routers.cases import _get_package_or_404
from app.services import verification_engine, dependency_graph, simulation_engine, time_machine, impact_analysis

router = APIRouter(tags=["analysis"])


@router.post("/api/defects/{defect_id}/verify")
def verify_defect(defect_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    defect = db.query(models.Defect).filter(models.Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    case = assert_case_access(db, user, defect.case_id)

    verification = verification_engine.verify_defect(db, defect_id=defect_id, user_id=user.id)

    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="VERIFY_DEFECT", entity_type="Defect", entity_id=defect_id,
                 after_state={"result": verification.result}, provenance="SYSTEM_DERIVED")
    return {
        "verification_id": verification.id,
        "result": verification.result,
        "notes": verification.notes,
    }


@router.get("/api/filing-packages/{package_id}/verification")
def list_verifications(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.Verification).filter(models.Verification.case_id == package.case_id).all()


@router.get("/api/defects/{defect_id}/impact")
def get_defect_impact(defect_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    defect = db.query(models.Defect).filter(models.Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    assert_case_access(db, user, defect.case_id)
    return impact_analysis.analyze_defect_impact(db, defect_id=defect_id)


@router.get("/api/filing-packages/{package_id}/dependency-graph")
def get_dependency_graph(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return dependency_graph.build_dependency_graph(db, filing_package_id=package_id)


@router.post("/api/filing-packages/{package_id}/simulation")
def run_simulation(package_id: str, payload: schemas.SimulationRequest, db: Session = Depends(get_db),
                    user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)
    require_capability(user, "RUN_SIMULATION")

    result = simulation_engine.run_counterfactual(
        db, case_id=case.id, filing_package_id=package_id,
        scenario=payload.scenario, params=payload.params, user_id=user.id,
    )
    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="RUN_SIMULATION", entity_type="FilingPackage", entity_id=package_id,
                 after_state={"scenario": payload.scenario}, provenance="SIMULATION")
    return result


@router.get("/api/filing-packages/{package_id}/evaluation")
def get_package_evaluation(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Spec-mandated path alias. The evaluation suite exercises the
    detection engines generally (not this specific package's data) — see
    docs/evaluation.md for why scenario-specific isolated cases are used
    instead of mutating the caller's real package. Requires only that the
    caller can see the package, so a citizen browsing their own package
    can confirm the engine's own health without needing ADMIN."""
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    from app.services.evaluation_lab import run_evaluation_suite
    return run_evaluation_suite(db)


@router.get("/api/filing-packages/{package_id}/time-machine")
def get_time_machine(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)
    return time_machine.build_time_machine_view(db, case_id=case.id, filing_package_id=package_id)


@router.post("/api/filing-packages/{package_id}/crash-test")
def run_crash_test(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    case = assert_case_access(db, user, package.case_id)
    require_capability(user, "RUN_CRASH_TEST")

    result = simulation_engine.run_crash_test_suite(db, case_id=case.id, filing_package_id=package_id, user_id=user.id)
    audit_record(db, case_id=case.id, actor_user_id=user.id, actor_role=user.role,
                 action="RUN_CRASH_TEST", entity_type="FilingPackage", entity_id=package_id,
                 after_state={"scenario_count": len(result["scenarios"])}, provenance="SIMULATION")
    return result
