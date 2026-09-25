"""FastAPI router for NYAYA-SATYA / TARKA-VYUH / UNWIND Core boundary.

Enforces deterministic governance, Human Legal Gate verification, and Execution Guard.
Every mutating route requires an authenticated principal, with judicial decisions
requiring an authenticated human principal.
"""

from __future__ import annotations

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


def reset_nyaya_api_state() -> None:
    """Test hook to reset API in-memory repositories."""
    _PROPOSALS.clear()
    _TWINS.clear()
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


__all__ = [
    "reset_nyaya_api_state",
    "router",
]

