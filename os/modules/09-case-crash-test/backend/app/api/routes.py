from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.domain import Case, CaseNode, CaseRelationship, CaseSnapshot, ReviewTask, AuditEvent
from app.models.simulation import Simulation, SimulationScenario
from app.schemas import schemas as s
from app.simulation_engine.snapshot_service import (
    create_snapshot, serialize_case_graph, compare_scenarios, restore_snapshot,
)
from app.simulation_engine.runner import run_simulation
from app.enums import SimulationStatus, ReviewStatus
from app.llm.providers import get_provider
from app.rbac import require_role, Role
from pydantic import BaseModel


class RestoreRequest(BaseModel):
    approved_by: str
    reason: str


router = APIRouter(prefix="/api")


def _audit(db: Session, case_id: str, event_type: str, payload: dict, actor: str = "system"):
    db.add(AuditEvent(case_id=case_id, event_type=event_type, actor=actor, payload=payload))
    db.commit()


# ---------------------------------------------------------------- Cases ----

@router.post("/cases", response_model=s.CaseOut)
def create_case(payload: s.CaseCreate, db: Session = Depends(get_db)):
    case = Case(title=payload.title, description=payload.description, is_demo=payload.is_demo)
    db.add(case)
    db.commit()
    db.refresh(case)
    _audit(db, case.id, "CASE_CREATED", {"title": case.title})
    return case


@router.get("/cases/{case_id}", response_model=s.CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("/cases", response_model=list[s.CaseOut])
def list_cases(db: Session = Depends(get_db)):
    return db.query(Case).order_by(Case.created_at.desc()).all()


# ----------------------------------------------------------- Graph nodes ----

@router.post("/cases/{case_id}/nodes", response_model=s.NodeOut)
def create_node(case_id: str, payload: s.NodeCreate, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    node = CaseNode(case_id=case_id, **payload.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.post("/cases/{case_id}/relationships", response_model=s.RelationshipOut)
def create_relationship(case_id: str, payload: s.RelationshipCreate, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    rel = CaseRelationship(case_id=case_id, **payload.model_dump())
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


@router.get("/cases/{case_id}/graph", response_model=s.GraphOut)
def get_graph(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    nodes = db.query(CaseNode).filter(CaseNode.case_id == case_id).all()
    rels = db.query(CaseRelationship).filter(CaseRelationship.case_id == case_id).all()
    return {"nodes": nodes, "relationships": rels}


# ------------------------------------------------------------- Snapshots ----

@router.post("/cases/{case_id}/snapshots", response_model=s.SnapshotOut)
def create_snapshot_endpoint(case_id: str, payload: s.SnapshotCreate, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    snap = create_snapshot(db, case_id, label=payload.label, created_by=payload.created_by)
    _audit(db, case_id, "SNAPSHOT_CREATED", {"snapshot_id": snap.id, "version": snap.version})
    return snap


@router.get("/cases/{case_id}/snapshots", response_model=list[s.SnapshotOut])
def list_snapshots(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    return (
        db.query(CaseSnapshot)
        .filter(CaseSnapshot.case_id == case_id)
        .order_by(CaseSnapshot.version.desc())
        .all()
    )


@router.post("/cases/{case_id}/snapshots/{snapshot_id}/restore")
def restore_snapshot_endpoint(
    case_id: str, snapshot_id: str, payload: RestoreRequest, db: Session = Depends(get_db),
    role: Role = Depends(require_role(Role.ADMIN)),
):
    """
    Time Machine — RESTORE-SAFE-SNAPSHOT.

    The only endpoint in this API allowed to overwrite the real, live case
    graph. Requires ADMIN role AND an explicit reason. Simulations, mutations,
    and recovery-simulation NEVER reach this path — they only ever read or
    write isolated snapshot copies. See snapshot_service.restore_snapshot for
    the non-negotiable invariant this enforces.
    """
    _require_case(db, case_id)
    snapshot = db.get(CaseSnapshot, snapshot_id)
    if not snapshot or snapshot.case_id != case_id:
        raise HTTPException(404, "Snapshot not found for this case")
    if not payload.reason.strip():
        raise HTTPException(400, "A reason is required to restore a snapshot")

    result = restore_snapshot(db, case_id, snapshot, approved_by=payload.approved_by, reason=payload.reason)
    _audit(db, case_id, "SNAPSHOT_RESTORED", result, actor=payload.approved_by)
    return result


# -------------------------------------------------------------- Scenarios ----

@router.post("/cases/{case_id}/scenarios", response_model=s.ScenarioOut)
def create_scenario(case_id: str, payload: s.ScenarioCreate, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    scenario = SimulationScenario(
        case_id=case_id,
        name=payload.name,
        description=payload.description,
        preconditions=payload.preconditions,
        mutations=[m.model_dump() for m in payload.mutations],
        is_technical_resilience_test=payload.is_technical_resilience_test,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/cases/{case_id}/scenarios", response_model=list[s.ScenarioOut])
def list_scenarios(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    return db.query(SimulationScenario).filter(SimulationScenario.case_id == case_id).all()


# ------------------------------------------------------------ Simulations ----

@router.post("/cases/{case_id}/simulations", response_model=s.SimulationOut)
def create_simulation(case_id: str, payload: s.SimulationCreate, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    snapshot = db.get(CaseSnapshot, payload.base_snapshot_id)
    if not snapshot or snapshot.case_id != case_id:
        raise HTTPException(404, "Base snapshot not found for this case")

    mutations: list[dict] = []
    scenario = None
    if payload.scenario_id:
        scenario = db.get(SimulationScenario, payload.scenario_id)
        if not scenario or scenario.case_id != case_id:
            raise HTTPException(404, "Scenario not found for this case")
        mutations = scenario.mutations
    elif payload.inline_mutations:
        mutations = [m.model_dump() for m in payload.inline_mutations]
    else:
        raise HTTPException(400, "Provide either scenario_id or inline_mutations")

    sim = Simulation(
        case_id=case_id,
        base_snapshot_id=snapshot.id,
        scenario_id=scenario.id if scenario else None,
        inline_scenario={"mutations": mutations} if not scenario else None,
        status=SimulationStatus.RUNNING.value,
        created_by=payload.created_by,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    result = run_simulation(snapshot.data, mutations)

    if payload.explain and result.get("status") == "COMPLETED":
        provider = get_provider(payload.llm_provider)
        try:
            result["explanation"] = provider.explain(
                f"Blast radius summary: {result['blast_radius']}. "
                f"Affected nodes: {[a['label'] for a in result['affected_nodes']]}."
            )
        except Exception as e:
            result["explanation_error"] = str(e)

    sim.status = result.get("status", SimulationStatus.FAILED.value)
    sim.result = result
    sim.human_review_required = bool(result.get("human_review_required", False))
    db.commit()
    db.refresh(sim)

    _audit(db, case_id, "SIMULATION_RUN", {
        "simulation_id": sim.id, "mutations": mutations, "status": sim.status,
    }, actor=payload.created_by)

    if sim.human_review_required:
        for node_id in result.get("blast_radius", {}).get("human_review_items", []):
            db.add(ReviewTask(
                case_id=case_id, simulation_id=sim.id, node_id=node_id,
                reason=f"Simulation {sim.id} flagged node {node_id} for human review.",
                status=ReviewStatus.PENDING.value,
            ))
        db.commit()

    return sim


@router.get("/cases/{case_id}/simulations", response_model=list[s.SimulationOut])
def list_simulations(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    return db.query(Simulation).filter(Simulation.case_id == case_id).order_by(Simulation.created_at.desc()).all()


@router.get("/simulations/{simulation_id}", response_model=s.SimulationOut)
def get_simulation(simulation_id: str, db: Session = Depends(get_db)):
    sim = db.get(Simulation, simulation_id)
    if not sim:
        raise HTTPException(404, "Simulation not found")
    return sim


@router.get("/simulations/{simulation_id}/diff")
def get_simulation_diff(simulation_id: str, db: Session = Depends(get_db)):
    sim = _require_simulation(db, simulation_id)
    return sim.result.get("diff") if sim.result else None


@router.get("/simulations/{simulation_id}/blast-radius")
def get_blast_radius(simulation_id: str, db: Session = Depends(get_db)):
    sim = _require_simulation(db, simulation_id)
    return sim.result.get("blast_radius") if sim.result else None


@router.get("/simulations/{simulation_id}/failure-tree")
def get_failure_tree(simulation_id: str, db: Session = Depends(get_db)):
    sim = _require_simulation(db, simulation_id)
    return sim.result.get("failure_trees") if sim.result else None


@router.get("/simulations/{simulation_id}/recovery-options")
def get_recovery_options(simulation_id: str, db: Session = Depends(get_db)):
    sim = _require_simulation(db, simulation_id)
    return sim.result.get("recovery_options") if sim.result else None


@router.post("/simulations/{simulation_id}/rerun", response_model=s.SimulationOut)
def rerun_simulation(simulation_id: str, db: Session = Depends(get_db)):
    original = _require_simulation(db, simulation_id)
    snapshot = db.get(CaseSnapshot, original.base_snapshot_id)
    mutations = (
        db.get(SimulationScenario, original.scenario_id).mutations
        if original.scenario_id else original.inline_scenario["mutations"]
    )
    result = run_simulation(snapshot.data, mutations)
    sim = Simulation(
        case_id=original.case_id, base_snapshot_id=original.base_snapshot_id,
        scenario_id=original.scenario_id, inline_scenario=original.inline_scenario,
        status=result.get("status"), created_by="rerun",
        result=result, human_review_required=bool(result.get("human_review_required", False)),
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/simulations/{simulation_id}/compare")
def compare_simulations(simulation_id: str, payload: s.CompareRequest, db: Session = Depends(get_db)):
    sim_a = _require_simulation(db, payload.simulation_id_a)
    sim_b = _require_simulation(db, payload.simulation_id_b)
    return compare_scenarios(sim_a.result or {}, sim_b.result or {})


@router.post("/simulations/{simulation_id}/recovery-simulation")
def recovery_simulation(simulation_id: str, payload: s.RecoverySimulationRequest, db: Session = Depends(get_db)):
    """
    Runs a FURTHER simulation on top of the ORIGINAL base snapshot, with the
    original mutations plus proposed recovery mutations applied together.
    This never touches the real case graph — it is simulation all the way down.
    """
    sim = _require_simulation(db, simulation_id)
    snapshot = db.get(CaseSnapshot, sim.base_snapshot_id)
    original_mutations = (
        db.get(SimulationScenario, sim.scenario_id).mutations
        if sim.scenario_id else sim.inline_scenario["mutations"]
    )
    combined = original_mutations + [m.model_dump() for m in payload.additional_mutations]
    result = run_simulation(snapshot.data, combined)
    return {
        "base_simulation_id": sim.id,
        "recovery_mutations": [m.model_dump() for m in payload.additional_mutations],
        "result": result,
        "note": "This is a recovery SIMULATION only. Nothing has been applied to the real case.",
    }


# ------------------------------------------------------------- Review ----

@router.get("/cases/{case_id}/review-queue", response_model=list[s.ReviewTaskOut])
def get_review_queue(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    return (
        db.query(ReviewTask)
        .filter(ReviewTask.case_id == case_id, ReviewTask.status == ReviewStatus.PENDING.value)
        .order_by(ReviewTask.created_at.desc())
        .all()
    )


@router.post("/reviews/{review_id}/approve", response_model=s.ReviewTaskOut)
def approve_review(review_id: str, payload: s.ReviewDecision, db: Session = Depends(get_db),
                    role: Role = Depends(require_role(Role.REVIEWER))):
    review = db.get(ReviewTask, review_id)
    if not review:
        raise HTTPException(404, "Review task not found")
    review.status = ReviewStatus.APPROVED.value
    review.resolved_at = datetime.now(timezone.utc)
    review.resolved_by = payload.decided_by
    db.commit()
    db.refresh(review)
    _audit(db, review.case_id, "REVIEW_APPROVED", {"review_id": review.id, "note": payload.note}, actor=payload.decided_by)
    return review


@router.post("/reviews/{review_id}/reject", response_model=s.ReviewTaskOut)
def reject_review(review_id: str, payload: s.ReviewDecision, db: Session = Depends(get_db),
                   role: Role = Depends(require_role(Role.REVIEWER))):
    review = db.get(ReviewTask, review_id)
    if not review:
        raise HTTPException(404, "Review task not found")
    review.status = ReviewStatus.REJECTED.value
    review.resolved_at = datetime.now(timezone.utc)
    review.resolved_by = payload.decided_by
    db.commit()
    db.refresh(review)
    _audit(db, review.case_id, "REVIEW_REJECTED", {"review_id": review.id, "note": payload.note}, actor=payload.decided_by)
    return review


# -------------------------------------------------------------- Audit ----

@router.get("/cases/{case_id}/audit", response_model=list[s.AuditEventOut])
def get_audit(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    return db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at.desc()).all()


# ----------------------------------------------------------- Evaluation ----

@router.get("/cases/{case_id}/evaluation")
def get_evaluation(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    from app.demo.evaluation import run_evaluation_suite
    return run_evaluation_suite(db, case_id)


# ------------------------------------------------------------ Integration ----

@router.get("/cases/{case_id}/integration-summary", response_model=s.IntegrationSummary)
def get_integration_summary(case_id: str, db: Session = Depends(get_db)):
    _require_case(db, case_id)
    latest_snapshot = (
        db.query(CaseSnapshot).filter(CaseSnapshot.case_id == case_id)
        .order_by(CaseSnapshot.version.desc()).first()
    )
    active_sims = db.query(Simulation).filter(
        Simulation.case_id == case_id, Simulation.status == SimulationStatus.RUNNING.value
    ).count()
    recent_sims = (
        db.query(Simulation).filter(Simulation.case_id == case_id)
        .order_by(Simulation.created_at.desc()).limit(5).all()
    )

    graph_data = serialize_case_graph(db, case_id)
    from app.graph.graph_model import SimGraph
    from app.graph.traversal import compute_criticality
    from app.enums import CriticalityLabel

    sim_graph = SimGraph.from_snapshot_data(graph_data)
    criticality = compute_criticality(sim_graph)
    critical_dependencies = [
        nid for nid, label in criticality.items()
        if label in (CriticalityLabel.HIGH_DEPENDENCY.value, CriticalityLabel.SINGLE_POINT_DEPENDENCY.value)
    ]
    fragile_nodes = [nid for nid, label in criticality.items() if label == CriticalityLabel.SINGLE_POINT_DEPENDENCY.value]

    affected_claims, affected_issues, affected_obligations = [], [], []
    affected_deadlines, affected_hearings, affected_registry_defects = [], [], []
    blocked_workflows, verification_gaps, human_review_items, provenance_refs = [], [], [], []

    for sim in recent_sims:
        if not sim.result:
            continue
        br = sim.result.get("blast_radius", {})
        affected_claims += br.get("affected_claims", [])
        affected_issues += br.get("affected_issues", [])
        affected_obligations += br.get("affected_obligations", [])
        affected_deadlines += br.get("affected_deadlines", [])
        affected_hearings += br.get("affected_hearings", [])
        affected_registry_defects += br.get("affected_registry_defects", [])
        blocked_workflows += br.get("affected_workflows", [])
        verification_gaps += br.get("verification_gaps", [])
        human_review_items += br.get("human_review_items", [])

    for n in graph_data["nodes"]:
        if n.get("provenance_ref"):
            provenance_refs.append(n["provenance_ref"])

    recent_failures = [
        {"simulation_id": sim.id, "status": sim.status, "created_at": sim.created_at.isoformat()}
        for sim in recent_sims
    ]

    return {
        "case_id": case_id,
        "base_state_version": latest_snapshot.version if latest_snapshot else None,
        "active_simulations": active_sims,
        "critical_dependencies": list(set(critical_dependencies)),
        "fragile_nodes": list(set(fragile_nodes)),
        "recent_failures": recent_failures,
        "affected_claims": list(set(affected_claims)),
        "affected_issues": list(set(affected_issues)),
        "affected_obligations": list(set(affected_obligations)),
        "affected_deadlines": list(set(affected_deadlines)),
        "affected_hearings": list(set(affected_hearings)),
        "affected_registry_defects": list(set(affected_registry_defects)),
        "blocked_workflows": list(set(blocked_workflows)),
        "verification_gaps": list(set(verification_gaps)),
        "human_review_items": list(set(human_review_items)),
        "provenance_refs": list(set(provenance_refs)),
        "last_updated": datetime.now(timezone.utc),
    }


# ------------------------------------------------------------------- utils ----

def _require_case(db: Session, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


def _require_simulation(db: Session, simulation_id: str) -> Simulation:
    sim = db.get(Simulation, simulation_id)
    if not sim:
        raise HTTPException(404, "Simulation not found")
    return sim
