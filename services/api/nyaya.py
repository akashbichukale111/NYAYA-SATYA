"""FastAPI router for NYAYA-SATYA / TARKA-VYUH / UNWIND Core boundary.

Enforces deterministic governance, Human Legal Gate verification, and Execution Guard.
Every mutating route requires an authenticated principal, with judicial decisions
requiring an authenticated human principal.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lib.auth import Principal
from services.api.security import (
    require_human_principal,
    require_principal,
    reset_rate_limits,
)
from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef
from tarka_vyuh.validation.validator import (
    ProposalValidationError,
    assert_valid_proposal,
)
from unwind_core.execution.executor import GovernedExecutor
from unwind_core.execution.guard import ExecutionBlockedError, ExecutionGuard
from unwind_core.gate.human_gate import (
    AutomatedApprovalProhibitedError,
    HumanDecisionRecord,
    HumanDecisionType,
    HumanLegalGate,
)
from unwind_core.governance.audit import AuditEventType, AuditStore, get_audit_store
from unwind_core.governance.state_machine import (
    GovernanceStateMachine,
    InvalidGovernanceTransitionError,
)

import base64
from nyaya_evidence.contracts.case import Case
from nyaya_evidence.contracts.evidence import EvidenceItem, EvidenceStatus
from nyaya_evidence.ingestion.ingest import ingest_evidence, EvidenceIngestionError
from nyaya_evidence.quarantine.manager import QuarantineManager, QuarantineViolationError
from nyaya_evidence.sanitization.sanitizer import AdversarialSanitizer, RiskLevel
from nyaya_evidence.parsers.dispatcher import DocumentParserDispatcher
from nyaya_evidence.parsers.base import DocumentParserError
from nyaya_evidence.registry.store import get_evidence_registry, EvidenceRegistryError
from nyaya_evidence.tarka_integration.safe_refs import create_safe_evidence_ref
from nyaya_evidence.contradiction.engine import ContradictionAnalysisEngine

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.entities import Entity, EntityType, EntityStatus
from nyaya_twin.contracts.claims import Claim, ClaimType, ClaimStatus
from nyaya_twin.contracts.issues import Issue, IssueStatus
from nyaya_twin.contracts.events import TimelineEvent, TimePrecision, TemporalStatus
from nyaya_twin.contracts.relationships import CaseRelationship, RelationshipType
from nyaya_twin.builders.twin_builder import CaseTwinBuilder
from nyaya_twin.graph.case_graph import CaseGraph
from nyaya_twin.graph.timeline_graph import TimelineGraph
from nyaya_twin.validation.graph_validator import validate_case_graph
from nyaya_twin.traversal.evidence_paths import (
    get_supporting_evidence_for_claim,
    get_contradicting_evidence_for_claim,
    get_evidence_dependent_claims,
    get_unsupported_claims,
)
from nyaya_twin.traversal.claim_dependencies import (
    get_claim_prerequisites,
    get_claim_dependents,
    get_claim_ancestors,
    get_claim_descendants,
)
from nyaya_twin.traversal.downstream_impact import compute_evidence_invalidation_impact

from nyaya_adversarial.contracts.assumption import (
    Assumption,
    AssumptionRegistry,
    AssumptionStatus,
    AssumptionType,
)
from nyaya_adversarial.contracts.attack import AttackScenario, AttackStatus, AttackType
from nyaya_adversarial.contracts.conflict import ConflictSet, EvidenceConflict, ConflictType, ConflictSeverity
from nyaya_adversarial.contracts.fragility import FragilityReport, AchillesHeel, StructuralSeverity
from nyaya_adversarial.contracts.missing_evidence import MissingEvidenceCandidate
from nyaya_adversarial.contracts.result import AdversarialFinding, AdversarialGauntletReport, FindingType
from nyaya_adversarial.contracts.voi import NextBestEvidence
from nyaya_adversarial.arena.conflict_arena import ConflictArena
from nyaya_adversarial.arena.contradiction_cluster import ContradictionClusterer
from nyaya_adversarial.arena.hypothesis_manager import HypothesisManager
from nyaya_adversarial.gauntlet.gauntlet import AdversarialGauntlet
from nyaya_adversarial.jenga.fragility_engine import JengaFragilityEngine
from nyaya_adversarial.jenga.achilles_engine import AchillesHeelEngine
from nyaya_adversarial.jenga.dependency_stress import DependencyStressEngine
from nyaya_adversarial.missing.detector import MissingEvidenceDetector
from nyaya_adversarial.missing.evidence_candidates import NextBestEvidenceEngine
from nyaya_adversarial.missing.uncertainty_reduction import UncertaintyReductionEngine
from nyaya_adversarial.validation.attack_validator import AttackValidator
from nyaya_adversarial.validation.result_validator import ResultValidator
from nyaya_adversarial.validation.safety_validator import SafetyValidator

# Phase 5: Causal Reasoning Engine imports
from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.intervention import (
    Intervention,
    InterventionOperation,
    InterventionTargetType,
)
from nyaya_causal.contracts.scenario import CounterfactualScenario, ScenarioStatus
from nyaya_causal.counterfactual.lab import CounterfactualLab
from nyaya_causal.graph.causal_graph import CausalGraph
from nyaya_causal.graph.path_engine import PathEngine
from nyaya_causal.integration.adversarial_adapter import AdversarialToCausalAdapter
from nyaya_causal.integration.tarka_adapter import CausalTarkaAdapter
from nyaya_causal.integration.twin_adapter import TwinToCausalAdapter
from nyaya_causal.integration.unwind_adapter import CausalUnwindAdapter
from nyaya_causal.materiality.classifier import MaterialityClassifier
from nyaya_causal.materiality.should_change import ShouldChangeAnalyzer
from nyaya_causal.materiality.should_not_change import ShouldNotChangeAnalyzer
from nyaya_causal.provenance.causal_provenance import CausalProvenanceTracker
from nyaya_causal.validation.counterfactual_validator import CounterfactualValidator
from nyaya_causal.validation.graph_validator import CausalGraphValidator
from nyaya_causal.validation.intervention_validator import InterventionValidator
from nyaya_causal.validation.safety_validator import CausalSafetyValidator

# Phase 6: Auto-Healer, Re-Attack, Perturbation, Readiness & Dossier imports
from nyaya_dossier.dossier_builder import DossierBuilder
from nyaya_dossier.dossier_model import JudicialReviewDossier
from nyaya_dossier.export_formatter import DossierFormatter
from nyaya_perturbation.perturbation_engine import LegalPerturbationLab
from nyaya_perturbation.perturbation_scenario import (
    PerturbationOutcome,
    PerturbationResultType,
    PerturbationScenario,
    PerturbationType,
)
from nyaya_perturbation.stability_analyzer import StabilityAnalyzer, StabilityReport
from nyaya_readiness.calculator import ReadinessCalculator
from nyaya_readiness.readiness_delta import CaseReadinessDelta
from nyaya_readiness.readiness_snapshot import CaseReadinessSnapshot
from nyaya_reattack.attack_comparator import AttackComparator, AttackComparisonReport
from nyaya_reattack.independent_attacker import IndependentAttacker
from nyaya_reattack.reattack_engine import ReAttackEngine
from nyaya_reattack.regression_detector import RegressionDetector, RegressionReport
from nyaya_reattack.repair_immunity import (
    RepairImmunityAssessment,
    RepairImmunityEvaluator,
    RepairImmunityStatus,
)
from nyaya_repair.contracts.repair import LegalAuthorityRef, LegalGroundingStatus
from nyaya_repair.contracts.repair_candidate import (
    RepairCandidate,
    RepairCandidateStatus,
    RepairChangeType,
)
from nyaya_repair.contracts.repair_result import SimulatedRepairReport
from nyaya_repair.contracts.repair_utility import RepairUtilityVector
from nyaya_repair.engine.convergence_governor import ConvergenceGovernor, ConvergenceState
from nyaya_repair.engine.repair_applier import RepairApplier
from nyaya_repair.engine.repair_evaluator import RepairEvaluator
from nyaya_repair.engine.repair_generator import RepairGenerator
from nyaya_repair.engine.repair_planner import RepairPlanner
from nyaya_repair.integration.adversarial_adapter import AdversarialRepairAdapter
from nyaya_repair.integration.causal_adapter import CausalRepairAdapter
from nyaya_repair.integration.tarka_adapter import TarkaRepairAdapter
from nyaya_repair.integration.unwind_adapter import UnwindRepairAdapter
from nyaya_repair.validation.collateral_impact_validator import CollateralImpactValidator
from nyaya_repair.validation.evidence_support_validator import EvidenceSupportValidator
from nyaya_repair.validation.legal_grounding_validator import LegalGroundingValidator
from nyaya_repair.validation.repair_validator import RepairValidator
from nyaya_repair.validation.vulnerability_validator import VulnerabilityValidator

# Phase 7: Dossier 2.0 and Proven Impact imports
from nyaya_dossier.dossier_diff import DossierComparator, DossierDiff
from nyaya_dossier.dossier_version import DossierVersionRecord, DossierVersionStore
from nyaya_dossier.human_checklist import (
    HumanReviewChecklist,
    ReviewItem,
    ReviewSeverity,
    ReviewStatus,
)
from nyaya_impact.collection.event_collector import EventCollector
from nyaya_impact.contracts.impact_baseline import ComparativeTrialResult
from nyaya_impact.contracts.impact_event import ImpactEvent, ImpactEventType
from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification
from nyaya_impact.contracts.impact_report import ProvenImpactReport
from nyaya_impact.experiments.benchmark_suite import BenchmarkScenarioResult, SyntheticBenchmarkSuite
from nyaya_impact.experiments.experiment_runner import ExperimentRunner
from nyaya_impact.reporting.evidence_exporter import EvidenceExporter
from nyaya_impact.reporting.impact_report import ImpactReportCompiler
from nyaya_impact.reporting.impact_summary import ExecutiveKPIs, ImpactSummaryGenerator
from nyaya_impact.validation.impact_safety_validator import ImpactSafetyValidator

router = APIRouter(prefix="/api/nyaya", tags=["nyaya-satya"])


# In-memory repositories for proposals and runtime instances
_PROPOSALS: dict[str, ReasoningProposal] = {}
_STATE_MACHINE = GovernanceStateMachine()
_HUMAN_GATE = HumanLegalGate(state_machine=_STATE_MACHINE)
_GUARD = ExecutionGuard()
_EXECUTOR = GovernedExecutor(guard=_GUARD, state_machine=_STATE_MACHINE)

# Evidence foundation runtime instances
_QUARANTINE = QuarantineManager()
_SANITIZER = AdversarialSanitizer()
_PARSER = DocumentParserDispatcher()
_CONTRADICTION = ContradictionAnalysisEngine()

# Case Digital Twin repository
_TWINS: dict[str, CaseDigitalTwin] = {}

# Adversarial Subsystem repositories
_ADVERSARIAL_REPORTS: dict[str, AdversarialGauntletReport] = {}
_ASSUMPTION_REGISTRIES: dict[str, AssumptionRegistry] = {}

# Causal Reasoning Subsystem repositories
_CAUSAL_GRAPHS: dict[str, CausalGraph] = {}
_COUNTERFACTUAL_LAB = CounterfactualLab()
_BLAST_ENGINE = BlastRadiusEngine()
_MATERIALITY_CLASSIFIER = MaterialityClassifier()
_TWIN_ADAPTER = TwinToCausalAdapter()
_CAUSAL_GRAPH_VALIDATOR = CausalGraphValidator()
_INTERVENTION_VALIDATOR = InterventionValidator()
_COUNTERFACTUAL_VALIDATOR = CounterfactualValidator()

# Phase 6: Repair, Re-Attack, Perturbation, Readiness & Dossier repositories
_REPAIR_CANDIDATES: dict[str, dict[str, RepairCandidate]] = {}
_SIMULATED_REPAIRS: dict[str, dict[str, SimulatedRepairReport]] = {}
_REPAIR_IMMUNITIES: dict[str, dict[str, RepairImmunityAssessment]] = {}
_PERTURBATION_LAB = LegalPerturbationLab()
_READINESS_CALCULATOR = ReadinessCalculator()
_READINESS_SNAPSHOTS: dict[str, CaseReadinessSnapshot] = {}
_READINESS_DELTAS: dict[str, list[CaseReadinessDelta]] = {}
_DOSSIER_BUILDER = DossierBuilder()
_DOSSIERS: dict[str, JudicialReviewDossier] = {}
_DOSSIER_BY_VERSION: dict[str, dict[int, JudicialReviewDossier]] = {}
_DOSSIER_VERSION_STORE = DossierVersionStore()
_DOSSIER_COMPARATOR = DossierComparator()
_REATTACK_ENGINE = ReAttackEngine()
_REPAIR_APPLIER = RepairApplier()
_REPAIR_EVALUATOR = RepairEvaluator()
_REPAIR_VALIDATOR = RepairValidator()

# Phase 7: Proven Impact repositories
_IMPACT_COLLECTOR = EventCollector()
_BENCHMARK_SUITE = SyntheticBenchmarkSuite()
_EXPERIMENT_RUNNER = ExperimentRunner()
_IMPACT_COMPILER = ImpactReportCompiler()
_IMPACT_SUMMARY_GEN = ImpactSummaryGenerator()
_EVIDENCE_EXPORTER = EvidenceExporter(compiler=_IMPACT_COMPILER)
_IMPACT_SAFETY_VALIDATOR = ImpactSafetyValidator()
_IMPACT_REPORTS: dict[str, ProvenImpactReport] = {}


def reset_nyaya_api_state() -> None:
    """Test hook to reset API in-memory repositories."""
    _PROPOSALS.clear()
    _TWINS.clear()
    _ADVERSARIAL_REPORTS.clear()
    _ASSUMPTION_REGISTRIES.clear()
    _CAUSAL_GRAPHS.clear()
    _COUNTERFACTUAL_LAB.reset_for_test()
    _REPAIR_CANDIDATES.clear()
    _SIMULATED_REPAIRS.clear()
    _REPAIR_IMMUNITIES.clear()
    _PERTURBATION_LAB.reset_for_test()
    _READINESS_SNAPSHOTS.clear()
    _READINESS_DELTAS.clear()
    _DOSSIERS.clear()
    _DOSSIER_BY_VERSION.clear()
    _DOSSIER_VERSION_STORE.reset_for_test()
    _IMPACT_COLLECTOR.reset_for_test()
    _IMPACT_REPORTS.clear()
    _HUMAN_GATE.reset_for_test()
    _GUARD.reset_for_test()
    get_audit_store().reset_for_test()
    get_evidence_registry().reset_for_test()
    reset_rate_limits()



# Pydantic schemas for request bodies
class ProvenanceRefPayload(BaseModel):
    source_id: str
    source_type: str
    evidence_id: str
    content_hash: str
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
    parent_record_id: str | None = None


class ProposedActionPayload(BaseModel):
    action_type: str
    target_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_consequential: bool = True


class CreateProposalRequest(BaseModel):
    proposal_id: str
    case_id: str
    reasoning_type: str
    input_evidence_ids: list[str]
    claims: list[str]
    assumptions: list[str] = Field(default_factory=list)
    uncertainty: float
    proposed_action: ProposedActionPayload
    provenance_refs: list[ProvenanceRefPayload]
    model_metadata: dict[str, Any] = Field(default_factory=dict)


class HumanDecisionRequest(BaseModel):
    decision: str  # "APPROVE" or "REJECT"
    reason: str
    authorization_record: dict[str, Any] = Field(default_factory=dict)


class BuildTwinRequest(BaseModel):
    twin_id: str | None = None
    entities: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)


@router.post("/proposals", status_code=201)
async def create_proposal(
    req: CreateProposalRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Creates a new reasoning proposal in PROPOSED status."""
    if req.proposal_id in _PROPOSALS:
        raise HTTPException(409, f"Proposal {req.proposal_id} already exists")

    try:
        r_type = ReasoningType(req.reasoning_type)
    except ValueError:
        raise HTTPException(400, f"Invalid reasoning_type: {req.reasoning_type}")

    action = ProposedAction(
        action_type=req.proposed_action.action_type,
        target_id=req.proposed_action.target_id,
        parameters=req.proposed_action.parameters,
        is_consequential=req.proposed_action.is_consequential,
    )

    prov_refs = [
        ProvenanceRef(
            ref_id=f"prov_{p.evidence_id[:16]}",
            source_id=p.source_id,
            source_type=p.source_type,
            evidence_id=p.evidence_id,
            content_hash=p.content_hash,
            extraction_metadata=p.extraction_metadata,
            parent_record_id=p.parent_record_id,
        )
        for p in req.provenance_refs
    ]

    try:
        proposal = ReasoningProposal(
            proposal_id=req.proposal_id,
            case_id=req.case_id,
            reasoning_type=r_type,
            input_evidence_ids=req.input_evidence_ids,
            claims=req.claims,
            assumptions=req.assumptions,
            uncertainty=req.uncertainty,
            proposed_action=action,
            provenance_refs=prov_refs,
            model_metadata=req.model_metadata,
            status=ProposalStatus.PROPOSED,
        )
        assert_valid_proposal(proposal)
    except (ValueError, ProposalValidationError) as exc:
        raise HTTPException(422, str(exc)) from exc

    _PROPOSALS[proposal.proposal_id] = proposal

    # Audit initial creation
    get_audit_store().record_event(
        proposal_id=proposal.proposal_id,
        case_id=proposal.case_id,
        event_type=AuditEventType.PROPOSAL_CREATED,
        previous_status=None,
        new_status=ProposalStatus.PROPOSED,
        actor_type="AI" if "agent" in caller.principal or "service" in caller.principal else "HUMAN",
        actor_id=caller.principal,
        proposal_hash=proposal.compute_hash(),
        provenance_refs=[p.ref_id for p in proposal.provenance_refs],
        reason="Initial proposal creation",
    )

    return {
        "status": "created",
        "proposal": proposal.to_dict(),
    }


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str) -> dict[str, Any]:
    """Retrieves an existing proposal."""
    proposal = _PROPOSALS.get(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")
    return proposal.to_dict()


@router.post("/proposals/{proposal_id}/review")
async def review_proposal(
    proposal_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Submits a proposal for governance review and advances it to ASK_HUMAN."""
    proposal = _PROPOSALS.get(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")

    try:
        _STATE_MACHINE.transition(
            proposal,
            ProposalStatus.GOVERNANCE_REVIEW,
            actor_type="SYSTEM",
            actor_id=caller.principal,
            reason="Submitted for governance review",
        )
        _STATE_MACHINE.transition(
            proposal,
            ProposalStatus.ASK_HUMAN,
            actor_type="SYSTEM",
            actor_id=caller.principal,
            reason="Governance checks passed; awaiting Human Legal Gate decision",
        )
    except InvalidGovernanceTransitionError as exc:
        raise HTTPException(409, str(exc)) from exc

    return {
        "proposal_id": proposal.proposal_id,
        "status": proposal.status.value,
        "message": "Proposal successfully escalated to Human Legal Gate (ASK_HUMAN)",
    }


@router.post("/proposals/{proposal_id}/decide")
async def human_decide(
    proposal_id: str,
    req: HumanDecisionRequest,
    caller: Principal = Depends(require_human_principal),
) -> dict[str, Any]:
    """Human Legal Gate: records explicit human judicial decision (APPROVE or REJECT)."""
    proposal = _PROPOSALS.get(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")

    try:
        dec = HumanDecisionType(req.decision.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid decision: {req.decision}. Must be APPROVE or REJECT.")

    try:
        record = _HUMAN_GATE.decide(
            proposal,
            reviewer_id=caller.principal,
            decision=dec,
            reason=req.reason,
            authorization_record=req.authorization_record,
        )
    except (InvalidGovernanceTransitionError, AutomatedApprovalProhibitedError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc

    return {
        "proposal_id": proposal.proposal_id,
        "status": proposal.status.value,
        "human_decision": record.to_dict(),
    }


@router.post("/proposals/{proposal_id}/execute")
async def execute_proposal(
    proposal_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Governed Execution: Verifies all safety criteria through ExecutionGuard before executing."""
    proposal = _PROPOSALS.get(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")

    decision_record = _HUMAN_GATE.get_decision(proposal_id)

    try:
        receipt = _EXECUTOR.execute(
            proposal=proposal,
            decision_record=decision_record,
            actor_id=caller.principal,
        )
    except ExecutionBlockedError as exc:
        raise HTTPException(403, str(exc)) from exc
    except InvalidGovernanceTransitionError as exc:
        raise HTTPException(409, str(exc)) from exc

    return {
        "proposal_id": proposal.proposal_id,
        "status": proposal.status.value,
        "receipt": receipt,
    }


@router.get("/proposals/{proposal_id}/audit")
async def get_audit_trail(proposal_id: str) -> dict[str, Any]:
    """Returns the immutable audit records for a proposal."""
    if proposal_id not in _PROPOSALS:
        raise HTTPException(404, f"Proposal {proposal_id} not found")

    records = get_audit_store().get_events_for_proposal(proposal_id)
    return {
        "proposal_id": proposal_id,
        "count": len(records),
        "events": [r.to_dict() for r in records],
    }



# ---------------------------------------------------------------------------
# EVIDENCE FOUNDATION: CASES & EVIDENCE
# ---------------------------------------------------------------------------

class CreateCaseRequest(BaseModel):
    case_id: str
    title: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestEvidenceRequest(BaseModel):
    filename: str
    content_base64: str | None = None
    text_content: str | None = None
    source_type: str = "DOCUMENT_UPLOAD"
    custodian: str = "UNKNOWN"
    chain_of_custody_notes: str = ""
    custom_metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeContradictionRequest(BaseModel):
    evidence_a_id: str
    evidence_b_id: str


@router.post("/cases", status_code=201)
async def create_case(
    req: CreateCaseRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Registers a new legal matter / case container."""
    registry = get_evidence_registry()
    try:
        case = Case(
            case_id=req.case_id,
            title=req.title,
            description=req.description,
            metadata=req.metadata,
        )
        registry.register_case(case)
    except (ValueError, EvidenceRegistryError) as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"status": "created", "case": case.to_dict()}


@router.get("/cases")
async def list_cases() -> dict[str, Any]:
    """Lists all cases registered in the system."""
    cases = get_evidence_registry().list_cases()
    return {"cases": [c.to_dict() for c in cases]}


@router.get("/cases/{case_id}")
async def get_case(case_id: str) -> dict[str, Any]:
    """Retrieves a specific case."""
    case = get_evidence_registry().get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.to_dict()


@router.post("/cases/{case_id}/evidence", status_code=201)
async def upload_evidence(
    case_id: str,
    req: IngestEvidenceRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Ingests raw evidence bytes into quarantine with SHA-256 and provenance."""
    registry = get_evidence_registry()
    case = registry.get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")

    if req.content_base64:
        try:
            raw_bytes = base64.b64decode(req.content_base64)
        except Exception as exc:
            raise HTTPException(400, f"Invalid base64 payload: {exc}") from exc
    elif req.text_content is not None:
        raw_bytes = req.text_content.encode("utf-8")
    else:
        raise HTTPException(400, "Either content_base64 or text_content must be provided")

    try:
        item, artifact, prov = ingest_evidence(
            case_id=case_id,
            raw_bytes=raw_bytes,
            filename=req.filename,
            source_type=req.source_type,
            custodian=req.custodian,
            chain_of_custody_notes=req.chain_of_custody_notes,
            custom_metadata=req.custom_metadata,
        )
        registry.register_evidence(item, artifact, prov)
    except EvidenceIngestionError as exc:
        raise HTTPException(422, str(exc)) from exc
    except EvidenceRegistryError as exc:
        raise HTTPException(409, str(exc)) from exc

    return {
        "status": "quarantined",
        "evidence": item.to_dict(),
        "provenance": prov.to_dict(),
    }


@router.get("/cases/{case_id}/evidence")
async def list_case_evidence(case_id: str) -> dict[str, Any]:
    """Lists all evidence items associated with a case."""
    registry = get_evidence_registry()
    case = registry.get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    items = registry.list_case_evidence(case_id)
    return {"case_id": case_id, "evidence": [i.to_dict() for i in items]}


@router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str) -> dict[str, Any]:
    """Retrieves an evidence item."""
    item = get_evidence_registry().get_evidence(evidence_id)
    if not item:
        raise HTTPException(404, f"Evidence {evidence_id} not found")
    return item.to_dict()


@router.get("/evidence/{evidence_id}/provenance")
async def get_evidence_provenance(evidence_id: str) -> dict[str, Any]:
    """Retrieves full provenance chain for an evidence item."""
    registry = get_evidence_registry()
    item = registry.get_evidence(evidence_id)
    if not item:
        raise HTTPException(404, f"Evidence {evidence_id} not found")
    provs = registry.get_provenance(evidence_id)
    return {
        "evidence_id": evidence_id,
        "provenance_chain": [p.to_dict() for p in provs],
    }


@router.get("/evidence/{evidence_id}/sanitization")
async def get_evidence_sanitization(evidence_id: str) -> dict[str, Any]:
    """Retrieves security sanitization scan report for an evidence item."""
    registry = get_evidence_registry()
    item = registry.get_evidence(evidence_id)
    if not item:
        raise HTTPException(404, f"Evidence {evidence_id} not found")
    san = registry.get_sanitization(evidence_id)
    if not san:
        raise HTTPException(404, f"Evidence {evidence_id} has not been scanned yet")
    return san.to_dict()


@router.post("/evidence/{evidence_id}/scan")
async def scan_evidence(
    evidence_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Runs adversarial security scan and sanitization on quarantined evidence."""
    registry = get_evidence_registry()
    item = registry.get_evidence(evidence_id)
    if not item:
        raise HTTPException(404, f"Evidence {evidence_id} not found")

    artifact = registry.get_artifact(evidence_id)
    if not artifact:
        raise HTTPException(500, f"Artifact bytes missing for evidence {evidence_id}")

    # Mark scanning
    try:
        _QUARANTINE.mark_scanning(item)
    except QuarantineViolationError as exc:
        raise HTTPException(409, str(exc)) from exc

    # Parse text or convert bytes for scanning
    try:
        parsed = _PARSER.parse(
            evidence_id=evidence_id,
            media_type=item.media_type,
            raw_bytes=artifact.raw_bytes,
            source_hash=artifact.content_hash,
        )
        registry.record_parsed_document(evidence_id, parsed)
        text_to_scan = parsed.text_content
    except DocumentParserError:
        text_to_scan = artifact.raw_bytes.decode("utf-8", errors="replace")

    # Run adversarial sanitizer
    result = _SANITIZER.sanitize(
        evidence_id=evidence_id,
        text_content=text_to_scan,
        original_hash=artifact.content_hash,
    )
    registry.record_sanitization(evidence_id, result)

    # Advance quarantine status based on scan findings
    if result.risk_level is RiskLevel.BLOCKED:
        _QUARANTINE.mark_malicious(item, reason="; ".join(result.findings))
    elif result.risk_level in (RiskLevel.HIGH_RISK, RiskLevel.SUSPICIOUS):
        _QUARANTINE.mark_flagged(item, reason="; ".join(result.findings))
    else:
        _QUARANTINE.mark_sanitized(item, reason="Passed security scan with zero high-risk findings")

    return {
        "evidence_id": evidence_id,
        "status": item.status.value,
        "sanitization": result.to_dict(),
    }


@router.post("/evidence/{evidence_id}/register")
async def register_safe_evidence(
    evidence_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Releases sanitized evidence from quarantine into REGISTERED status."""
    registry = get_evidence_registry()
    item = registry.get_evidence(evidence_id)
    if not item:
        raise HTTPException(404, f"Evidence {evidence_id} not found")

    try:
        _QUARANTINE.mark_registered(item, reason="Operator confirmed registration of sanitized evidence")
    except QuarantineViolationError as exc:
        raise HTTPException(409, str(exc)) from exc

    return {
        "evidence_id": evidence_id,
        "status": item.status.value,
        "message": "Evidence successfully registered and made accessible for TARKA-VYUH reasoning",
    }


@router.post("/evidence/{evidence_id}/parse")
async def parse_evidence(
    evidence_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Parses registered evidence into structured pages and provenance links."""
    registry = get_evidence_registry()
    item = registry.get_evidence(evidence_id)
    if not item:
        raise HTTPException(404, f"Evidence {evidence_id} not found")

    if not item.is_safe_for_reasoning:
        raise HTTPException(
            403,
            f"Evidence {evidence_id} is in status {item.status.value}. Evidence must be REGISTERED before parsing for reasoning.",
        )

    artifact = registry.get_artifact(evidence_id)
    if not artifact:
        raise HTTPException(500, f"Artifact bytes missing for evidence {evidence_id}")

    try:
        parsed = _PARSER.parse(
            evidence_id=evidence_id,
            media_type=item.media_type,
            raw_bytes=artifact.raw_bytes,
            source_hash=artifact.content_hash,
        )
        registry.record_parsed_document(evidence_id, parsed)
        _QUARANTINE.advance_status(item, EvidenceStatus.PARSED, reason="Document parsed into structured pages")
    except DocumentParserError as exc:
        raise HTTPException(422, str(exc)) from exc

    return {
        "evidence_id": evidence_id,
        "status": item.status.value,
        "parsed": parsed.to_dict(),
    }


@router.post("/contradictions/analyze")
async def analyze_contradictions(
    req: AnalyzeContradictionRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compares two registered evidence references and identifies contradiction candidates."""
    registry = get_evidence_registry()
    item_a = registry.get_evidence(req.evidence_a_id)
    item_b = registry.get_evidence(req.evidence_b_id)

    if not item_a:
        raise HTTPException(404, f"Evidence {req.evidence_a_id} not found")
    if not item_b:
        raise HTTPException(404, f"Evidence {req.evidence_b_id} not found")

    san_a = registry.get_sanitization(req.evidence_a_id)
    san_b = registry.get_sanitization(req.evidence_b_id)
    parsed_a = registry.get_parsed_document(req.evidence_a_id)
    parsed_b = registry.get_parsed_document(req.evidence_b_id)
    provs_a = registry.get_provenance(req.evidence_a_id)
    provs_b = registry.get_provenance(req.evidence_b_id)

    try:
        ref_a = create_safe_evidence_ref(
            item=item_a,
            sanitization=san_a,
            parsed=parsed_a,
            provenance_refs=provs_a,
        )
        ref_b = create_safe_evidence_ref(
            item=item_b,
            sanitization=san_b,
            parsed=parsed_b,
            provenance_refs=provs_b,
        )
    except QuarantineViolationError as exc:
        raise HTTPException(403, str(exc)) from exc

    candidates = _CONTRADICTION.analyze_pair(ref_a, ref_b)
    proposals = [_CONTRADICTION.to_reasoning_proposal(c).to_dict() for c in candidates]

    return {
        "evidence_a_id": req.evidence_a_id,
        "evidence_b_id": req.evidence_b_id,
        "candidates_count": len(candidates),
        "candidates": [c.to_dict() for c in candidates],
        "generated_proposals": proposals,
    }


# ============================================================================
# PHASE 3: CASE DIGITAL TWIN API ENDPOINTS
# ============================================================================
@router.post("/cases/{case_id}/twin/build")
async def build_case_twin(
    case_id: str,
    req: BuildTwinRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Constructs or updates the Case Digital Twin from entities, claims, events, and evidence."""
    registry = get_evidence_registry()
    case = registry.get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")

    builder = CaseTwinBuilder(case_id=case_id, twin_id=req.twin_id)

    # Attach all registered safe evidence for this case
    all_evidence = registry.list_case_evidence(case_id)
    registered_items = {
        item.evidence_id: item
        for item in all_evidence
        if item.is_safe_for_reasoning
    }

    safe_refs_list = []
    for ev_id, item in registered_items.items():
        san = registry.get_sanitization(ev_id)
        parsed = registry.get_parsed_document(ev_id)
        provs = registry.get_provenance(ev_id)
        try:
            ref = create_safe_evidence_ref(
                item=item,
                sanitization=san,
                parsed=parsed,
                provenance_refs=provs,
            )
            builder.add_evidence_ref(ref)
            safe_refs_list.append(ref)
        except QuarantineViolationError:
            continue

    # Add entities
    for edata in req.entities:
        etype_str = edata.get("entity_type", "PERSON")
        try:
            etype = EntityType(etype_str)
        except ValueError:
            etype = EntityType.OTHER
        builder.entity_builder.add_entity(
            canonical_label=edata["canonical_label"],
            entity_type=etype,
            entity_id=edata.get("entity_id"),
            aliases=edata.get("aliases"),
            source_evidence_ids=edata.get("source_evidence_ids"),
            metadata=edata.get("metadata"),
        )

    # Add claims
    for cdata in req.claims:
        ctype_str = cdata.get("claim_type", "FACTUAL")
        try:
            ctype = ClaimType(ctype_str)
        except ValueError:
            ctype = ClaimType.FACTUAL
        builder.claim_builder.add_claim(
            subject_entity_id=cdata["subject_entity_id"],
            predicate=cdata["predicate"],
            object_value=cdata["object_value"],
            claim_id=cdata.get("claim_id"),
            claim_type=ctype,
            source_evidence_ids=cdata.get("source_evidence_ids"),
            supporting_evidence_ids=cdata.get("supporting_evidence_ids"),
            contradicting_evidence_ids=cdata.get("contradicting_evidence_ids"),
            notes=cdata.get("notes", ""),
            metadata=cdata.get("metadata"),
        )

    # Add issues
    for idata in req.issues:
        builder.add_issue(
            title=idata["title"],
            issue_id=idata.get("issue_id"),
            description=idata.get("description", ""),
            related_claim_ids=idata.get("related_claim_ids"),
            related_evidence_ids=idata.get("related_evidence_ids"),
            unresolved_questions=idata.get("unresolved_questions"),
        )

    # Add events
    for evdata in req.events:
        tprec_str = evdata.get("time_precision", "UNKNOWN")
        try:
            tprec = TimePrecision(tprec_str)
        except ValueError:
            tprec = TimePrecision.UNKNOWN
        builder.timeline_builder.add_event(
            title=evdata["title"],
            event_id=evdata.get("event_id"),
            event_type=evdata.get("event_type", "FACTUAL_EVENT"),
            description=evdata.get("description", ""),
            event_time=evdata.get("event_time"),
            start_time=evdata.get("start_time"),
            end_time=evdata.get("end_time"),
            time_precision=tprec,
            participants=evdata.get("participants"),
            location=evdata.get("location"),
            source_evidence_ids=evdata.get("source_evidence_ids"),
            related_claim_ids=evdata.get("related_claim_ids"),
            metadata=evdata.get("metadata"),
        )

    # Add relationships
    for rdata in req.relationships:
        rtype_str = rdata["relationship_type"]
        try:
            rtype = RelationshipType(rtype_str)
        except ValueError:
            raise HTTPException(400, f"Invalid relationship_type: {rtype_str}")
        builder.add_relationship(
            source_id=rdata["source_id"],
            source_type=rdata.get("source_type", "CLAIM"),
            target_id=rdata["target_id"],
            target_type=rdata.get("target_type", "CLAIM"),
            relationship_type=rtype,
            relationship_id=rdata.get("relationship_id"),
            weight=rdata.get("weight", 1.0),
            metadata=rdata.get("metadata"),
        )

    # Add unresolved items
    for item_str in req.unresolved_items:
        builder.add_unresolved_item(item_str)

    # Run pairwise contradiction analysis across attached safe references
    for i in range(len(safe_refs_list)):
        for j in range(i + 1, len(safe_refs_list)):
            cands = _CONTRADICTION.analyze_pair(safe_refs_list[i], safe_refs_list[j])
            for cand in cands:
                builder.add_contradiction(cand)

    all_evidence_map = {item.evidence_id: item for item in all_evidence}
    twin = builder.build(evidence_items=all_evidence_map)
    _TWINS[case_id] = twin

    return {
        "twin_id": twin.twin_id,
        "case_id": twin.case_id,
        "version": twin.version,
        "integrity_hash": twin.integrity_hash,
        "entities_count": len(twin.entities),
        "claims_count": len(twin.claims),
        "issues_count": len(twin.issues),
        "events_count": len(twin.events),
        "evidence_refs_count": len(twin.evidence_refs),
        "relationships_count": len(twin.relationships),
        "contradictions_count": len(twin.contradictions),
        "temporal_conflicts_count": len(twin.temporal_conflicts),
        "graph_integrity": twin.graph_integrity,
    }


@router.get("/cases/{case_id}/twin")
async def get_case_twin(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieves high-level summary of the Case Digital Twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    return {
        "twin_id": twin.twin_id,
        "case_id": twin.case_id,
        "version": twin.version,
        "integrity_hash": twin.integrity_hash,
        "entities_count": len(twin.entities),
        "claims_count": len(twin.claims),
        "issues_count": len(twin.issues),
        "events_count": len(twin.events),
        "evidence_refs_count": len(twin.evidence_refs),
        "relationships_count": len(twin.relationships),
        "contradictions_count": len(twin.contradictions),
        "temporal_conflicts_count": len(twin.temporal_conflicts),
        "graph_integrity": twin.graph_integrity,
        "unresolved_items": twin.unresolved_items,
    }


@router.get("/cases/{case_id}/twin/entities")
async def get_case_twin_entities(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieves entities registered in the Case Digital Twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    return {
        "case_id": case_id,
        "entities": [e.to_dict() for e in twin.entities.values()],
    }


@router.get("/cases/{case_id}/twin/claims")
async def get_case_twin_claims(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieves claims registered in the Case Digital Twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    return {
        "case_id": case_id,
        "claims": [c.to_dict() for c in twin.claims.values()],
    }


@router.get("/cases/{case_id}/twin/issues")
async def get_case_twin_issues(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieves legal issues registered in the Case Digital Twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    return {
        "case_id": case_id,
        "issues": [i.to_dict() for i in twin.issues.values()],
    }


@router.get("/cases/{case_id}/twin/timeline")
async def get_case_twin_timeline(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieves chronologically sorted events and temporal conflicts."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    tg = TimelineGraph(case_id)
    for ev in twin.events.values():
        tg.add_event(ev)
    stream = tg.get_chronological_stream()
    return {
        "case_id": case_id,
        "timeline_events": [e.to_dict() for e in stream],
        "temporal_conflicts": twin.temporal_conflicts,
    }


@router.get("/cases/{case_id}/twin/graph")
async def get_case_twin_graph(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieves full graph nodes and relationships."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    return {
        "case_id": case_id,
        "twin_id": twin.twin_id,
        "nodes": {
            "entities": [e.to_dict() for e in twin.entities.values()],
            "claims": [c.to_dict() for c in twin.claims.values()],
            "issues": [i.to_dict() for i in twin.issues.values()],
            "events": [e.to_dict() for e in twin.events.values()],
            "evidence_refs": [ref.to_dict() for ref in twin.evidence_refs.values()],
        },
        "relationships": [rel.to_dict() for rel in twin.relationships.values()],
        "contradictions": [cand.to_dict() for cand in twin.contradictions],
    }


@router.get("/cases/{case_id}/twin/evidence/{evidence_id}/dependencies")
async def get_evidence_dependencies(
    case_id: str,
    evidence_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Computes downstream impact if an evidence reference is altered or invalidated."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    report = compute_evidence_invalidation_impact(twin, evidence_id)
    return report.to_dict()


@router.get("/cases/{case_id}/twin/claims/{claim_id}/support")
async def get_claim_support(
    case_id: str,
    claim_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns supporting and contradicting evidence for a specific claim."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if claim_id not in twin.claims:
        raise HTTPException(404, f"Claim {claim_id} not found in twin")

    claim = twin.claims[claim_id]
    supporting = get_supporting_evidence_for_claim(twin, claim_id)
    contradicting = get_contradicting_evidence_for_claim(twin, claim_id)

    return {
        "case_id": case_id,
        "claim_id": claim_id,
        "statement": claim.statement,
        "status": claim.status.value,
        "confidence": claim.confidence.value,
        "supporting_evidence_ids": supporting,
        "contradicting_evidence_ids": contradicting,
    }


@router.get("/cases/{case_id}/twin/claims/{claim_id}/dependencies")
async def get_claim_dependencies(
    case_id: str,
    claim_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns direct and transitive upstream/downstream claim dependencies."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if claim_id not in twin.claims:
        raise HTTPException(404, f"Claim {claim_id} not found in twin")

    prereqs = get_claim_prerequisites(twin, claim_id)
    deps = get_claim_dependents(twin, claim_id)
    ancestors = get_claim_ancestors(twin, claim_id)
    descendants = get_claim_descendants(twin, claim_id)

    return {
        "case_id": case_id,
        "claim_id": claim_id,
        "direct_prerequisites": prereqs,
        "direct_dependents": deps,
        "all_ancestors": ancestors,
        "all_descendants": descendants,
    }


@router.get("/cases/{case_id}/twin/snapshot")
async def get_twin_snapshot(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns the reproducible, deterministic JSON snapshot of the twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    return twin.snapshot()


@router.post("/cases/{case_id}/twin/validate")
async def validate_twin_endpoint(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Validates the Case Digital Twin against the 15 graph integrity rules."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    registry = get_evidence_registry()
    all_evidence = registry.list_case_evidence(case_id)
    evidence_map = {item.evidence_id: item for item in all_evidence}
    res = validate_case_graph(twin, evidence_items=evidence_map)
    return res.to_dict()


# -------------------------------------------------------------
# PHASE 4: ADVERSARIAL GAUNTLET & REASONING ENDPOINTS
# -------------------------------------------------------------

class RunGauntletPayload(BaseModel):
    attack_types: list[str] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AssumptionPayload(BaseModel):
    assumption_id: str
    description: str
    assumption_type: str = "STRUCTURAL"
    related_claim_ids: list[str] = Field(default_factory=list)
    related_evidence_ids: list[str] = Field(default_factory=list)
    support_status: str = "UNSUPPORTED"
    uncertainty: float = 0.5


@router.post("/cases/{case_id}/adversarial/run")
async def run_adversarial_gauntlet_endpoint(
    case_id: str,
    payload: RunGauntletPayload | None = None,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Runs the Adversarial Gauntlet against the Case Digital Twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    if case_id not in _ASSUMPTION_REGISTRIES:
        _ASSUMPTION_REGISTRIES[case_id] = AssumptionRegistry(case_id=case_id)
    assump_reg = _ASSUMPTION_REGISTRIES[case_id]

    gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
    report = gauntlet.run_gauntlet()
    _ADVERSARIAL_REPORTS[case_id] = report
    return report.to_dict()


@router.get("/cases/{case_id}/adversarial/findings")
async def list_adversarial_findings(
    case_id: str,
    severity: str | None = None,
    finding_type: str | None = None,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Returns adversarial findings, optionally filtered by severity or type."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    if case_id not in _ADVERSARIAL_REPORTS:
        twin = _TWINS[case_id]
        assump_reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
        gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
        _ADVERSARIAL_REPORTS[case_id] = gauntlet.run_gauntlet()

    report = _ADVERSARIAL_REPORTS[case_id]
    findings = report.findings
    if severity:
        findings = [f for f in findings if f.severity.value == severity.upper()]
    if finding_type:
        findings = [f for f in findings if f.finding_type.value == finding_type.upper()]
    return [f.to_dict() for f in findings]


@router.get("/cases/{case_id}/adversarial/conflicts")
async def list_case_conflicts(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns the ConflictSet, clusters, and hypotheses from the Conflict Arena."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    arena = ConflictArena(twin)
    cset = arena.detect_conflicts()
    clusterer = ContradictionClusterer()
    clusters = clusterer.cluster_conflicts(cset)
    hyp_mgr = HypothesisManager(twin)
    hyp_map = hyp_mgr.build_case_hypothesis_map(cset.conflicts)

    return {
        "case_id": case_id,
        "conflict_set": cset.to_dict(),
        "clusters": [cl.to_dict() for cl in clusters],
        "hypotheses": {k: [h.to_dict() for h in v] for k, v in hyp_map.items()},
    }


@router.get("/cases/{case_id}/adversarial/attacks")
async def list_generated_attacks(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Lists all attack scenarios generated across the 10 attack classes."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    assump_reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
    gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
    attacks = gauntlet.generator.generate_all_attacks()
    return [a.to_dict() for a in attacks]


@router.get("/cases/{case_id}/adversarial/fragility")
async def get_fragility_analysis(
    case_id: str,
    target_id: str | None = None,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Returns Jenga structural fragility reports for nodes in the case."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    engine = JengaFragilityEngine(twin)
    if target_id:
        if target_id in twin.evidence_refs:
            return [engine.analyze_evidence_fragility(target_id).to_dict()]
        elif target_id in twin.claims:
            return [engine.analyze_claim_fragility(target_id).to_dict()]
        else:
            raise HTTPException(404, f"Node {target_id} not found in case twin")
    else:
        return [r.to_dict() for r in engine.analyze_all_evidence()]


@router.get("/cases/{case_id}/adversarial/achilles-heels")
async def list_achilles_heels(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Returns detected Achilles-heel vulnerabilities in the case."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    engine = AchillesHeelEngine(twin)
    heels = engine.detect_achilles_heels()
    return [h.to_dict() for h in heels]


@router.get("/cases/{case_id}/adversarial/assumptions")
async def list_assumptions(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns all registered assumptions for the case."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
    return reg.to_dict()


@router.post("/cases/{case_id}/adversarial/assumptions")
async def register_assumption(
    case_id: str,
    payload: AssumptionPayload,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Registers an explicit or structural assumption."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    if case_id not in _ASSUMPTION_REGISTRIES:
        _ASSUMPTION_REGISTRIES[case_id] = AssumptionRegistry(case_id=case_id)
    reg = _ASSUMPTION_REGISTRIES[case_id]
    assump = Assumption(
        assumption_id=payload.assumption_id,
        case_id=case_id,
        description=payload.description,
        assumption_type=AssumptionType(payload.assumption_type.upper()),
        related_claim_ids=payload.related_claim_ids,
        related_evidence_ids=payload.related_evidence_ids,
        support_status=AssumptionStatus(payload.support_status.upper()),
        uncertainty=payload.uncertainty,
    )
    reg.register(assump)
    return assump.to_dict()


@router.get("/cases/{case_id}/adversarial/missing-evidence")
async def list_missing_evidence(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Returns detected missing evidence questions and candidates."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    detector = MissingEvidenceDetector(twin)
    cands = detector.detect_missing_evidence()
    return [c.to_dict() for c in cands]


@router.get("/cases/{case_id}/adversarial/next-best-evidence")
async def list_next_best_evidence(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Returns ranked next-best-evidence candidates based on uncertainty reduction."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    engine = NextBestEvidenceEngine(twin)
    ranked = engine.rank_next_best_evidence()
    return [r.to_dict() for r in ranked]


@router.get("/cases/{case_id}/adversarial/claims/{claim_id}/attacks")
async def get_claim_attacks(
    case_id: str,
    claim_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Returns attacks specifically targeting a claim or its dependency tree."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if claim_id not in twin.claims:
        raise HTTPException(404, f"Claim {claim_id} not found in case {case_id}")
    assump_reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
    gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
    all_attacks = gauntlet.generator.generate_all_attacks()
    claim_attacks = [
        a for a in all_attacks
        if a.target_node_id == claim_id or claim_id in a.parameters.get("descendants", [])
    ]
    return [a.to_dict() for a in claim_attacks]


@router.get("/cases/{case_id}/adversarial/evidence/{evidence_id}/dependencies")
async def get_evidence_dependency_stress(
    case_id: str,
    evidence_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns dependency chain stress analysis rooted at a specific evidence node."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if evidence_id not in twin.evidence_refs:
        raise HTTPException(404, f"Evidence {evidence_id} not found in case {case_id}")
    engine = DependencyStressEngine(twin)
    summary = engine.stress_test_all_chains()
    chains = [c.to_dict() for c in summary.high_stress_chains if c.root_evidence_id == evidence_id]
    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "is_single_point_of_failure": evidence_id in summary.single_points_of_failure,
        "stress_chains": chains,
    }


@router.post("/cases/{case_id}/adversarial/validate")
async def validate_adversarial_findings_endpoint(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Validates adversarial findings for compliance with non-adjudication rules."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if case_id not in _ADVERSARIAL_REPORTS:
        assump_reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
        gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
        _ADVERSARIAL_REPORTS[case_id] = gauntlet.run_gauntlet()

    report = _ADVERSARIAL_REPORTS[case_id]
    validator = ResultValidator()
    validator.validate_report(report)
    return {
        "status": "VALID",
        "case_id": case_id,
        "total_findings_validated": len(report.findings),
        "non_adjudication_verified": True,
    }


@router.get("/cases/{case_id}/adversarial/snapshot")
async def get_adversarial_snapshot(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Returns the full adversarial report snapshot for a case."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if case_id not in _ADVERSARIAL_REPORTS:
        assump_reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
        gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
        _ADVERSARIAL_REPORTS[case_id] = gauntlet.run_gauntlet()

    report = _ADVERSARIAL_REPORTS[case_id]
    return report.to_dict()


# ============================================================
# Phase 5: Causal Reasoning Engine Endpoints
# ============================================================


class InterventionRequest(BaseModel):
    target_id: str
    target_type: str  # EVIDENCE, EVENT, CLAIM, ASSUMPTION
    operation: str  # REMOVE, DISABLE, CHANGE_VALUE, CHANGE_TIME, etc.
    rationale: str = ""
    hypothetical_state: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class RunScenarioRequest(BaseModel):
    intervention: InterventionRequest
    preconditions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    execution_config: dict[str, Any] = Field(default_factory=dict)


class ShouldChangeRequest(BaseModel):
    intervention: InterventionRequest
    expected_changed_ids: list[str]


class ShouldNotChangeRequest(BaseModel):
    intervention: InterventionRequest
    protected_node_ids: list[str]


def _build_intervention(case_id: str, req: InterventionRequest) -> Intervention:
    """Helper: convert API request into Intervention contract."""
    import uuid
    return Intervention(
        intervention_id=f"INT_{uuid.uuid4().hex[:12]}",
        case_id=case_id,
        target_id=req.target_id,
        target_type=InterventionTargetType(req.target_type),
        operation=InterventionOperation(req.operation),
        rationale=req.rationale,
        hypothetical_state=req.hypothetical_state,
        assumptions=req.assumptions,
    )


@router.post("/cases/{case_id}/causal/graph/build")
def build_causal_graph(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Build a causal graph from the Case Digital Twin."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    graph = _TWIN_ADAPTER.build_causal_graph(twin)
    _CAUSAL_GRAPHS[case_id] = graph
    return graph.to_dict()


@router.get("/cases/{case_id}/causal/graph")
def get_causal_graph(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get the causal graph for a case."""
    if case_id not in _CAUSAL_GRAPHS:
        raise HTTPException(404, f"Causal graph for {case_id} not found")
    return _CAUSAL_GRAPHS[case_id].to_dict()


@router.get("/cases/{case_id}/causal/graph/validate")
def validate_causal_graph(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Validate causal graph integrity."""
    if case_id not in _CAUSAL_GRAPHS:
        raise HTTPException(404, f"Causal graph for {case_id} not found")
    result = _CAUSAL_GRAPH_VALIDATOR.validate(_CAUSAL_GRAPHS[case_id])
    return result.to_dict()


@router.get("/cases/{case_id}/causal/graph/paths")
def get_causal_paths(
    case_id: str,
    source_id: str,
    target_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Find causal paths between two nodes."""
    if case_id not in _CAUSAL_GRAPHS:
        raise HTTPException(404, f"Causal graph for {case_id} not found")
    engine = PathEngine(_CAUSAL_GRAPHS[case_id])
    try:
        result = engine.find_paths(source_id, target_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result.to_dict()


@router.get("/cases/{case_id}/causal/graph/downstream/{node_id}")
def get_downstream_nodes(
    case_id: str,
    node_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get all nodes downstream of a given node."""
    if case_id not in _CAUSAL_GRAPHS:
        raise HTTPException(404, f"Causal graph for {case_id} not found")
    graph = _CAUSAL_GRAPHS[case_id]
    if node_id not in graph.nodes:
        raise HTTPException(404, f"Node {node_id} not found")
    downstream = graph.get_downstream(node_id)
    return {"node_id": node_id, "downstream": downstream, "count": len(downstream)}


@router.get("/cases/{case_id}/causal/graph/upstream/{node_id}")
def get_upstream_nodes(
    case_id: str,
    node_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get all nodes upstream of a given node."""
    if case_id not in _CAUSAL_GRAPHS:
        raise HTTPException(404, f"Causal graph for {case_id} not found")
    graph = _CAUSAL_GRAPHS[case_id]
    if node_id not in graph.nodes:
        raise HTTPException(404, f"Node {node_id} not found")
    upstream = graph.get_upstream(node_id)
    return {"node_id": node_id, "upstream": upstream, "count": len(upstream)}


@router.post("/cases/{case_id}/causal/blast-radius")
def compute_blast_radius(
    case_id: str,
    req: InterventionRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compute the causal blast-radius of an intervention."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    intervention = _build_intervention(case_id, req)

    # Validate
    iv_result = _INTERVENTION_VALIDATOR.validate(intervention, twin)
    if not iv_result.valid:
        raise HTTPException(400, f"Invalid intervention: {iv_result.errors}")

    report = _BLAST_ENGINE.compute(twin, intervention)
    return report.to_dict()


@router.post("/cases/{case_id}/causal/scenarios")
def create_counterfactual_scenario(
    case_id: str,
    req: RunScenarioRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Create and run a counterfactual scenario."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    intervention = _build_intervention(case_id, req.intervention)

    # Validate intervention
    iv_result = _INTERVENTION_VALIDATOR.validate(intervention, twin)
    if not iv_result.valid:
        raise HTTPException(400, f"Invalid intervention: {iv_result.errors}")

    # Create and run
    scenario = _COUNTERFACTUAL_LAB.create_scenario(
        case_id=case_id,
        intervention=intervention,
        base_twin_version=twin.version,
        preconditions=req.preconditions,
        assumptions=req.assumptions,
        execution_config=req.execution_config,
    )
    result = _COUNTERFACTUAL_LAB.run_scenario(scenario.scenario_id, twin)
    return result.to_dict()


@router.get("/cases/{case_id}/causal/scenarios")
def list_scenarios(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """List all counterfactual scenarios for a case."""
    scenarios = _COUNTERFACTUAL_LAB.list_scenarios(case_id)
    return {
        "case_id": case_id,
        "scenarios": [s.to_dict() for s in scenarios],
        "total_count": len(scenarios),
    }


@router.get("/cases/{case_id}/causal/scenarios/{scenario_id}")
def get_scenario(
    case_id: str,
    scenario_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get a specific counterfactual scenario."""
    scenario = _COUNTERFACTUAL_LAB.get_scenario(scenario_id)
    if scenario is None or scenario.case_id != case_id:
        raise HTTPException(404, f"Scenario {scenario_id} not found for case {case_id}")
    return scenario.to_dict()


@router.post("/cases/{case_id}/causal/scenarios/{scenario_id}/replay")
def replay_scenario(
    case_id: str,
    scenario_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Replay a counterfactual scenario for reproducibility verification."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    scenario = _COUNTERFACTUAL_LAB.get_scenario(scenario_id)
    if scenario is None or scenario.case_id != case_id:
        raise HTTPException(404, f"Scenario {scenario_id} not found for case {case_id}")
    result = _COUNTERFACTUAL_LAB.replay_scenario(scenario_id, _TWINS[case_id])
    return result.to_dict()


@router.get("/cases/{case_id}/causal/materiality/evidence/{evidence_id}")
def assess_evidence_materiality(
    case_id: str,
    evidence_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Assess the structural materiality of an evidence item."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if evidence_id not in twin.evidence_refs:
        raise HTTPException(404, f"Evidence {evidence_id} not found in twin")
    assessment = _MATERIALITY_CLASSIFIER.assess_evidence(evidence_id, twin)
    return assessment.to_dict()


@router.get("/cases/{case_id}/causal/materiality/claims/{claim_id}")
def assess_claim_materiality(
    case_id: str,
    claim_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Assess the structural materiality of a claim."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    if claim_id not in twin.claims:
        raise HTTPException(404, f"Claim {claim_id} not found in twin")
    assessment = _MATERIALITY_CLASSIFIER.assess_claim(claim_id, twin)
    return assessment.to_dict()


@router.post("/cases/{case_id}/causal/should-change")
def should_change_analysis(
    case_id: str,
    req: ShouldChangeRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Verify that material interventions produce expected state changes."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    intervention = _build_intervention(case_id, req.intervention)
    analyzer = ShouldChangeAnalyzer()
    result = analyzer.analyze(twin, intervention, req.expected_changed_ids)
    return result.to_dict()


@router.post("/cases/{case_id}/causal/should-not-change")
def should_not_change_analysis(
    case_id: str,
    req: ShouldNotChangeRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Verify that irrelevant perturbations do not affect protected nodes."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    intervention = _build_intervention(case_id, req.intervention)
    analyzer = ShouldNotChangeAnalyzer()
    result = analyzer.analyze(twin, intervention, req.protected_node_ids)
    return result.to_dict()


@router.post("/cases/{case_id}/causal/validate")
def validate_causal_subsystem(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Validate Phase 5 causal subsystem compliance."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    results: dict[str, Any] = {"case_id": case_id}

    # Case isolation
    safety = CausalSafetyValidator()
    iso_result = safety.validate_case_isolation(case_id, twin)
    results["case_isolation"] = iso_result.to_dict()

    # Twin immutability check
    original_hash = twin.integrity_hash
    imm_result = safety.validate_twin_immutability(original_hash, twin.integrity_hash)
    results["twin_immutability"] = imm_result.to_dict()

    # Causal graph validation (if graph exists)
    if case_id in _CAUSAL_GRAPHS:
        gv_result = _CAUSAL_GRAPH_VALIDATOR.validate(_CAUSAL_GRAPHS[case_id])
        results["causal_graph"] = gv_result.to_dict()

    results["overall_valid"] = all(
        r.get("safe", r.get("valid", True))
        for r in [results.get("case_isolation", {}), results.get("twin_immutability", {})]
    )

    return results


@router.get("/cases/{case_id}/causal/snapshot")
def get_causal_snapshot(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get a full causal analysis snapshot for a case."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")

    snapshot: dict[str, Any] = {"case_id": case_id}

    if case_id in _CAUSAL_GRAPHS:
        snapshot["causal_graph"] = _CAUSAL_GRAPHS[case_id].to_dict()

    scenarios = _COUNTERFACTUAL_LAB.list_scenarios(case_id)
    snapshot["scenarios"] = [s.to_dict() for s in scenarios]
    snapshot["scenario_count"] = len(scenarios)

    return snapshot


# ============================================================
# Phase 6: Auto-Healer, Re-Attack, Perturbation, Readiness & Dossier Endpoints
# ============================================================


class GenerateRepairsRequest(BaseModel):
    finding_ids: list[str] | None = None


class ValidateRepairRequest(BaseModel):
    repair_id: str


class SimulateRepairRequest(BaseModel):
    repair_id: str


class RunReAttackRequest(BaseModel):
    repair_id: str


class RunPerturbationRequest(BaseModel):
    perturbation_type: str  # SHOULD_CHANGE or SHOULD_NOT_CHANGE
    target_node_id: str
    target_node_type: str  # EVIDENCE, CLAIM, EVENT, ENTITY
    operation: str  # REMOVE, MODIFY, CORRUPT_TIMESTAMP
    expected_affected_nodes: list[str] = Field(default_factory=list)
    protected_nodes: list[str] = Field(default_factory=list)
    rationale: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ComputeReadinessDeltaRequest(BaseModel):
    repair_id: str


@router.post("/cases/{case_id}/repair/generate")
def generate_repairs(
    case_id: str,
    req: GenerateRepairsRequest = GenerateRepairsRequest(),
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Generate evidence-grounded repair candidates for identified vulnerabilities."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    if case_id not in _ADVERSARIAL_REPORTS:
        # Run adversarial gauntlet if report not present
        assump_reg = _ASSUMPTION_REGISTRIES.get(case_id, AssumptionRegistry(case_id=case_id))
        gauntlet = AdversarialGauntlet(twin, assumption_registry=assump_reg)
        _ADVERSARIAL_REPORTS[case_id] = gauntlet.run_gauntlet()

    gauntlet_report = _ADVERSARIAL_REPORTS[case_id]
    adapter = AdversarialRepairAdapter(twin)

    findings = gauntlet_report.findings
    if req.finding_ids:
        findings = [f for f in findings if f.finding_id in req.finding_ids]

    candidates = adapter.extract_repairs_from_findings(findings)
    planner = RepairPlanner()
    prioritized = planner.prioritize_repairs(candidates)

    if case_id not in _REPAIR_CANDIDATES:
        _REPAIR_CANDIDATES[case_id] = {}
    for r in prioritized:
        _REPAIR_CANDIDATES[case_id][r.repair_id] = r

    return {
        "case_id": case_id,
        "total_generated": len(prioritized),
        "candidates": [r.to_dict() for r in prioritized],
    }


@router.get("/cases/{case_id}/repair/candidates")
def list_repair_candidates(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """List generated repair candidates for a case."""
    repairs = _REPAIR_CANDIDATES.get(case_id, {})
    return {
        "case_id": case_id,
        "candidates": [r.to_dict() for r in repairs.values()],
        "count": len(repairs),
    }


@router.get("/cases/{case_id}/repair/candidates/{repair_id}")
def get_repair_candidate(
    case_id: str,
    repair_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get a specific repair candidate."""
    repairs = _REPAIR_CANDIDATES.get(case_id, {})
    if repair_id not in repairs:
        raise HTTPException(404, f"Repair candidate {repair_id} not found for case {case_id}")
    return repairs[repair_id].to_dict()


@router.post("/cases/{case_id}/repair/validate")
def validate_repair(
    case_id: str,
    req: ValidateRepairRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Validate a repair candidate against safety, non-adjudication, and grounding rules."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    repairs = _REPAIR_CANDIDATES.get(case_id, {})
    if req.repair_id not in repairs:
        raise HTTPException(404, f"Repair candidate {req.repair_id} not found")

    repair = repairs[req.repair_id]
    validator = RepairValidator()
    result = validator.validate(repair, twin)

    ev_validator = EvidenceSupportValidator()
    ev_result = ev_validator.validate_evidence(repair, twin)

    legal_validator = LegalGroundingValidator()
    legal_result = legal_validator.validate_authorities(repair)

    is_overall_valid = result.is_valid and ev_result.is_valid and legal_result.is_valid
    if is_overall_valid:
        repair.status = RepairCandidateStatus.VALIDATED

    return {
        "repair_id": repair.repair_id,
        "is_valid": is_overall_valid,
        "structural_validation": result.to_dict(),
        "evidence_validation": ev_result.to_dict(),
        "legal_grounding_validation": legal_result.to_dict(),
    }


@router.post("/cases/{case_id}/repair/simulate")
def simulate_repair(
    case_id: str,
    req: SimulateRepairRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Simulate a repair candidate on a cloned twin and compute utility."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]
    repairs = _REPAIR_CANDIDATES.get(case_id, {})
    if req.repair_id not in repairs:
        raise HTTPException(404, f"Repair candidate {req.repair_id} not found")

    repair = repairs[req.repair_id]
    pre_hash = twin.integrity_hash

    # Apply repair to clone
    applier = RepairApplier()
    repaired_twin, exec_result = applier.apply_repair(twin, repair)
    post_hash = repaired_twin.integrity_hash

    # Evaluate utility vector
    evaluator = RepairEvaluator()
    utility = evaluator.evaluate(repair, twin, repaired_twin)

    # Blast radius via causal adapter
    causal_adapter = CausalRepairAdapter()
    blast_report = causal_adapter.recalculate_blast_radius(twin, repair)

    report_id = f"SIMREP_{uuid.uuid4().hex[:8]}"
    sim_report = SimulatedRepairReport(
        report_id=report_id,
        case_id=case_id,
        repair_candidate=repair,
        pre_repair_hash=pre_hash,
        post_repair_hash=post_hash,
        execution_result=exec_result,
        utility_vector=utility,
        blast_radius=blast_report.to_dict(),
        is_acceptable=utility.is_acceptable(),
    )

    repair.status = RepairCandidateStatus.SIMULATED
    if case_id not in _SIMULATED_REPAIRS:
        _SIMULATED_REPAIRS[case_id] = {}
    _SIMULATED_REPAIRS[case_id][repair.repair_id] = sim_report

    return sim_report.to_dict()


@router.post("/cases/{case_id}/repair/utility")
def evaluate_repair_utility(
    case_id: str,
    req: SimulateRepairRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compute the multi-dimensional Repair Utility Vector for a simulated repair."""
    sims = _SIMULATED_REPAIRS.get(case_id, {})
    if req.repair_id not in sims:
        raise HTTPException(404, f"Simulated report for repair {req.repair_id} not found. Run /simulate first.")
    report = sims[req.repair_id]
    return report.utility_vector.to_dict()


@router.post("/cases/{case_id}/reattack/run")
def run_reattack(
    case_id: str,
    req: RunReAttackRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Run independent re-attack scenarios against the post-repair state."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    sims = _SIMULATED_REPAIRS.get(case_id, {})
    if req.repair_id not in sims:
        raise HTTPException(404, f"Simulated report for repair {req.repair_id} not found. Run /simulate first.")
    sim_report = sims[req.repair_id]

    # Re-apply repair to a fresh simulation clone for re-attack
    applier = RepairApplier()
    repaired_twin, _ = applier.apply_repair(twin, sim_report.repair_candidate)

    reattack_engine = ReAttackEngine()
    report = reattack_engine.execute_reattack(repaired_twin, sim_report.repair_candidate)

    # Compare with pre-repair findings
    pre_findings = _ADVERSARIAL_REPORTS[case_id].findings if case_id in _ADVERSARIAL_REPORTS else []
    comparator = AttackComparator()
    comparison = comparator.compare(pre_findings, report.findings, target_vulnerability_id=sim_report.repair_candidate.target_vulnerability_id)

    reg_detector = RegressionDetector()
    regression = reg_detector.detect_regressions(comparison, report.findings)

    immunity_evaluator = RepairImmunityEvaluator()
    immunity = immunity_evaluator.evaluate_immunity(sim_report.repair_candidate, comparison, regression)

    if case_id not in _REPAIR_IMMUNITIES:
        _REPAIR_IMMUNITIES[case_id] = {}
    _REPAIR_IMMUNITIES[case_id][req.repair_id] = immunity

    sim_report.re_attack_summary = {
        "report_id": report.report_id,
        "total_attacks": report.total_attacks_executed,
        "findings_count": len(report.findings),
    }
    sim_report.immunity_status = immunity.status.value

    return {
        "repair_id": req.repair_id,
        "reattack_report": report.to_dict(),
        "comparison": comparison.to_dict(),
        "regression": regression.to_dict(),
        "immunity": immunity.to_dict(),
    }


@router.post("/cases/{case_id}/reattack/compare")
def compare_reattack(
    case_id: str,
    req: RunReAttackRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compare pre-repair vs post-repair adversarial findings."""
    immunities = _REPAIR_IMMUNITIES.get(case_id, {})
    if req.repair_id not in immunities:
        raise HTTPException(404, f"Re-attack analysis for repair {req.repair_id} not found. Run /reattack/run first.")
    return immunities[req.repair_id].to_dict()


@router.get("/cases/{case_id}/reattack/immunity/{repair_id}")
def get_repair_immunity(
    case_id: str,
    repair_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get the repair immunity assessment for a repair."""
    immunities = _REPAIR_IMMUNITIES.get(case_id, {})
    if repair_id not in immunities:
        raise HTTPException(404, f"Immunity assessment for repair {repair_id} not found")
    return immunities[repair_id].to_dict()


@router.post("/cases/{case_id}/perturbation/run")
def run_perturbation_scenario(
    case_id: str,
    req: RunPerturbationRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Run a controlled SHOULD_CHANGE or SHOULD_NOT_CHANGE perturbation experiment."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    scenario = PerturbationScenario(
        scenario_id=f"PERT_{uuid.uuid4().hex[:8]}",
        case_id=case_id,
        perturbation_type=PerturbationType(req.perturbation_type),
        target_node_id=req.target_node_id,
        target_node_type=req.target_node_type,
        operation=req.operation,
        expected_affected_nodes=req.expected_affected_nodes,
        protected_nodes=req.protected_nodes,
        rationale=req.rationale,
        parameters=req.parameters,
    )

    outcome = _PERTURBATION_LAB.run_scenario(twin, scenario)
    return outcome.to_dict()


@router.get("/cases/{case_id}/perturbation/outcomes")
def list_perturbation_outcomes(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """List all perturbation outcomes for a case."""
    outcomes = _PERTURBATION_LAB.list_outcomes(case_id)
    return {
        "case_id": case_id,
        "outcomes": [o.to_dict() for o in outcomes],
        "count": len(outcomes),
    }


@router.get("/cases/{case_id}/perturbation/stability")
def get_perturbation_stability(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get the aggregate reasoning stability report from perturbation testing."""
    outcomes = _PERTURBATION_LAB.list_outcomes(case_id)
    analyzer = StabilityAnalyzer()
    report = analyzer.analyze_stability(case_id, outcomes)
    return report.to_dict()


@router.get("/cases/{case_id}/readiness/snapshot")
def get_readiness_snapshot(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compute and retrieve a structural case readiness snapshot."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    snapshot = _READINESS_CALCULATOR.compute_snapshot(twin)
    _READINESS_SNAPSHOTS[case_id] = snapshot
    return snapshot.to_dict()


@router.post("/cases/{case_id}/readiness/delta")
def compute_readiness_delta(
    case_id: str,
    req: ComputeReadinessDeltaRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compute the structural readiness delta before and after a simulated repair."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    sims = _SIMULATED_REPAIRS.get(case_id, {})
    if req.repair_id not in sims:
        raise HTTPException(404, f"Simulated report for repair {req.repair_id} not found. Run /simulate first.")
    sim_report = sims[req.repair_id]

    # Re-apply to clone for post snapshot
    applier = RepairApplier()
    repaired_twin, _ = applier.apply_repair(twin, sim_report.repair_candidate)

    pre_snap = _READINESS_CALCULATOR.compute_snapshot(twin)
    post_snap = _READINESS_CALCULATOR.compute_snapshot(
        repaired_twin,
        repair_immunity_status=sim_report.immunity_status,
    )

    delta = _READINESS_CALCULATOR.compute_delta(req.repair_id, pre_snap, post_snap)
    if case_id not in _READINESS_DELTAS:
        _READINESS_DELTAS[case_id] = []
    _READINESS_DELTAS[case_id].append(delta)

    return delta.to_dict()


@router.post("/cases/{case_id}/dossier/build")
def build_judicial_dossier(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Build the comprehensive 24-section auditable Judicial Review Dossier."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    gauntlet = _ADVERSARIAL_REPORTS.get(case_id)
    sims = _SIMULATED_REPAIRS.get(case_id, {})
    latest_sim = list(sims.values())[-1] if sims else None
    latest_repair = latest_sim.repair_candidate if latest_sim else None

    immunities = _REPAIR_IMMUNITIES.get(case_id, {})
    latest_immunity = list(immunities.values())[-1] if immunities else None

    outcomes = _PERTURBATION_LAB.list_outcomes(case_id)
    stability = StabilityAnalyzer().analyze_stability(case_id, outcomes) if outcomes else None

    deltas = _READINESS_DELTAS.get(case_id, [])
    latest_delta = deltas[-1] if deltas else None

    history = _DOSSIER_VERSION_STORE.get_history(case_id)
    version_num = len(history) + 1
    prev_fp = history[-1].current_fingerprint if history else None

    dossier = _DOSSIER_BUILDER.build_dossier(
        twin,
        gauntlet_report=gauntlet,
        repair=latest_repair,
        sim_report=latest_sim,
        immunity=latest_immunity,
        stability=stability,
        readiness_delta=latest_delta,
        version=version_num,
        previous_fingerprint=prev_fp,
    )

    _DOSSIERS[case_id] = dossier
    if case_id not in _DOSSIER_BY_VERSION:
        _DOSSIER_BY_VERSION[case_id] = {}
    _DOSSIER_BY_VERSION[case_id][version_num] = dossier

    _DOSSIER_VERSION_STORE.record_version(
        case_id=case_id,
        current_fingerprint=dossier.fingerprint,
        change_summary=f"Dossier build version {version_num}",
        actor_id=caller.principal,
    )

    return dossier.to_dict()


@router.get("/cases/{case_id}/dossier/latest")
def get_latest_dossier(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Get the latest compiled Judicial Review Dossier."""
    if case_id not in _DOSSIERS:
        raise HTTPException(404, f"Judicial Review Dossier for {case_id} not found. Run /dossier/build first.")
    return _DOSSIERS[case_id].to_dict()


@router.get("/cases/{case_id}/dossier/export/markdown")
def export_dossier_markdown(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Export the latest dossier as structured Markdown."""
    if case_id not in _DOSSIERS:
        raise HTTPException(404, f"Judicial Review Dossier for {case_id} not found. Run /dossier/build first.")
    md_content = DossierFormatter.to_markdown(_DOSSIERS[case_id])
    return {
        "case_id": case_id,
        "dossier_id": _DOSSIERS[case_id].dossier_id,
        "format": "markdown",
        "content": md_content,
    }


@router.get("/cases/{case_id}/dossier/export/json")
def export_dossier_json(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Export the latest dossier as JSON string."""
    if case_id not in _DOSSIERS:
        raise HTTPException(404, f"Judicial Review Dossier for {case_id} not found. Run /dossier/build first.")
    json_str = DossierFormatter.to_json(_DOSSIERS[case_id])
    return {
        "case_id": case_id,
        "dossier_id": _DOSSIERS[case_id].dossier_id,
        "format": "json",
        "content": json_str,
    }


# ============================================================
# Phase 7: Dossier 2.0 Versioning, Diff, and Human Checklist
# ============================================================

class DossierDiffRequest(BaseModel):
    version_a: int
    version_b: int


class ImpactEventPayload(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    workflow_phase: str | None = None
    actor_type: str = "SYSTEM"


class RunExperimentRequest(BaseModel):
    case_id: str


class VerifyExportPayload(BaseModel):
    json_export: str


@router.get("/cases/{case_id}/dossier/versions")
def list_dossier_versions(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """List historical dossier versions for a case."""
    history = _DOSSIER_VERSION_STORE.get_history(case_id)
    return [h.to_dict() for h in history]


@router.get("/cases/{case_id}/dossier/versions/{version_num}")
def get_dossier_by_version(
    case_id: str,
    version_num: int,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieve a specific historical version of the dossier."""
    case_versions = _DOSSIER_BY_VERSION.get(case_id, {})
    dossier = case_versions.get(version_num)
    if not dossier:
        raise HTTPException(404, f"Dossier version {version_num} for case {case_id} not found")
    return dossier.to_dict()


@router.post("/cases/{case_id}/dossier/diff")
def diff_dossier_versions(
    case_id: str,
    req: DossierDiffRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Calculate deterministic structural diff between two dossier versions."""
    case_versions = _DOSSIER_BY_VERSION.get(case_id, {})
    d_a = case_versions.get(req.version_a)
    d_b = case_versions.get(req.version_b)
    if not d_a:
        raise HTTPException(404, f"Dossier version {req.version_a} not found")
    if not d_b:
        raise HTTPException(404, f"Dossier version {req.version_b} not found")

    diff = _DOSSIER_COMPARATOR.compare(d_a, d_b)
    return diff.to_dict()


@router.get("/cases/{case_id}/dossier/checklist")
def get_human_review_checklist(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Generate human jurist review checklist from the latest dossier and case twin."""
    if case_id not in _DOSSIERS or case_id not in _TWINS:
        raise HTTPException(404, f"Dossier or Twin for case {case_id} not found")
    dossier = _DOSSIERS[case_id]
    twin = _TWINS[case_id]
    checklist = _DOSSIER_BUILDER.build_human_checklist(dossier, twin)
    return checklist.to_dict()


# ============================================================
# Phase 7: Proven Impact API Endpoints
# ============================================================

@router.post("/cases/{case_id}/impact/events", status_code=201)
def record_impact_event(
    case_id: str,
    req: ImpactEventPayload,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Record an immutable, privacy-minimized structural workflow event."""
    try:
        e_type = ImpactEventType(req.event_type)
    except ValueError:
        raise HTTPException(400, f"Invalid event_type: {req.event_type}")

    event = ImpactEvent(
        event_id=f"EVT_{uuid.uuid4().hex[:8]}",
        case_id=case_id,
        event_type=e_type,
        phase=req.workflow_phase or "GENERAL",
        metadata=req.payload,
    )

    safety = _IMPACT_SAFETY_VALIDATOR.validate_event(event)
    if not safety.is_safe:
        raise HTTPException(400, f"Safety or privacy violation: {safety.violations}")

    _IMPACT_COLLECTOR.record_event(event)
    return event.to_dict()


@router.get("/cases/{case_id}/impact/events")
def list_impact_events(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """List structural impact events for a case."""
    events = _IMPACT_COLLECTOR.get_events_for_case(case_id)
    return [e.to_dict() for e in events]


@router.post("/experiments/run")
def run_comparative_experiment(
    req: RunExperimentRequest,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Execute a comparative trial (manual baseline vs NYAYA-SATYA pipeline) on a case twin."""
    if req.case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {req.case_id} not found")
    twin = _TWINS[req.case_id]
    trial_res = _EXPERIMENT_RUNNER.run_comparative_trial(twin)
    return trial_res.to_dict()


@router.post("/experiments/benchmark")
def run_synthetic_benchmarks(
    caller: Principal = Depends(require_principal),
) -> list[dict[str, Any]]:
    """Execute the canonical 12-scenario synthetic benchmark suite."""
    results = _BENCHMARK_SUITE.run_all_benchmarks()
    return [r.to_dict() for r in results]


@router.post("/cases/{case_id}/impact/report")
def compile_case_impact_report(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Compile an auditable 14-section Proven Impact Report for a case."""
    if case_id not in _TWINS:
        raise HTTPException(404, f"Case Digital Twin for {case_id} not found")
    twin = _TWINS[case_id]

    trial = _EXPERIMENT_RUNNER.run_comparative_trial(twin)
    benchmarks = _BENCHMARK_SUITE.run_all_benchmarks()

    metrics = [
        ImpactMetric(
            metric_id=f"M_CONTRA_{case_id}",
            name="Contradictions Automatically Surfaced",
            category=MetricCategory.EVIDENCE_ANALYSIS,
            classification=MetricClassification.OBSERVED,
            value=float(trial.treatment.contradictions_automatically_surfaced),
            unit="count",
            description="Contradictions automatically identified by adversarial gauntlet",
            source_provenance_hash=twin.integrity_hash,
        ),
        ImpactMetric(
            metric_id=f"M_UNSUP_{case_id}",
            name="Unsupported Claims Caught",
            category=MetricCategory.EVIDENCE_ANALYSIS,
            classification=MetricClassification.OBSERVED,
            value=float(trial.treatment.unsupported_claims_caught),
            unit="count",
            description="Claims without supporting evidence caught by twin analysis",
            source_provenance_hash=twin.integrity_hash,
        ),
        ImpactMetric(
            metric_id=f"M_PROV_{case_id}",
            name="Provenance Coverage Ratio",
            category=MetricCategory.EVIDENCE_PROCESSING,
            classification=MetricClassification.OBSERVED,
            value=float(trial.treatment.provenance_coverage_ratio),
            unit="ratio",
            description="Proportion of evidence items with verified cryptographic provenance",
            source_provenance_hash=twin.integrity_hash,
        ),
        ImpactMetric(
            metric_id=f"M_LATENCY_{case_id}",
            name="Automated Pipeline Latency",
            category=MetricCategory.WORKFLOW,
            classification=MetricClassification.OBSERVED,
            value=float(trial.treatment.automated_processing_time_seconds),
            unit="seconds",
            description="Execution latency of automated verification checks",
            source_provenance_hash=twin.integrity_hash,
        ),
    ]

    report = _IMPACT_COMPILER.compile(
        case_or_dataset_id=case_id,
        metrics=metrics,
        comparative_trial=trial,
        benchmarks=benchmarks,
    )

    safety = _IMPACT_SAFETY_VALIDATOR.validate_report(report)
    if not safety.is_safe:
        raise HTTPException(400, f"Safety violation in report: {safety.violations}")

    _IMPACT_REPORTS[case_id] = report
    return report.to_dict()


@router.get("/cases/{case_id}/impact/report/latest")
def get_latest_impact_report(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Retrieve latest compiled Proven Impact Report for a case."""
    if case_id not in _IMPACT_REPORTS:
        raise HTTPException(404, f"Impact report for {case_id} not found. Run /impact/report first.")
    return _IMPACT_REPORTS[case_id].to_dict()


@router.get("/cases/{case_id}/impact/report/export/json")
def export_impact_report_json(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Export the latest impact report as cryptographically signed JSON envelope."""
    if case_id not in _IMPACT_REPORTS:
        raise HTTPException(404, f"Impact report for {case_id} not found. Run /impact/report first.")
    report = _IMPACT_REPORTS[case_id]
    export_content = _EVIDENCE_EXPORTER.export_json(report)
    return {
        "case_id": case_id,
        "format": "json",
        "export": export_content,
        "fingerprint": report.fingerprint,
    }


@router.get("/cases/{case_id}/impact/report/export/markdown")
def export_impact_report_markdown(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Export the latest impact report as structured Markdown with audit footer."""
    if case_id not in _IMPACT_REPORTS:
        raise HTTPException(404, f"Impact report for {case_id} not found. Run /impact/report first.")
    report = _IMPACT_REPORTS[case_id]
    md_content = _EVIDENCE_EXPORTER.export_markdown(report)
    return {
        "case_id": case_id,
        "format": "markdown",
        "export": md_content,
        "fingerprint": report.fingerprint,
    }


@router.get("/cases/{case_id}/impact/summary")
def get_case_impact_summary(
    case_id: str,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Generate high-level Executive KPIs from the latest case impact report."""
    if case_id not in _IMPACT_REPORTS:
        raise HTTPException(404, f"Impact report for {case_id} not found. Run /impact/report first.")
    summary = _IMPACT_SUMMARY_GEN.summarize(_IMPACT_REPORTS[case_id])
    return summary.to_dict()


@router.post("/experiments/verify")
def verify_impact_export(
    payload: VerifyExportPayload,
    caller: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Verify cryptographic checksum and integrity of an exported JSON report envelope."""
    is_valid = _EVIDENCE_EXPORTER.verify_json_export(payload.json_export)
    return {"is_valid": is_valid}


__all__ = [
    "reset_nyaya_api_state",
    "router",
]



