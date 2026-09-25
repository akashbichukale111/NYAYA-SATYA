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
from services.api.security import require_human_principal, require_principal
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


def reset_nyaya_api_state() -> None:
    """Test hook to reset API in-memory repositories."""
    _PROPOSALS.clear()
    _HUMAN_GATE.reset_for_test()
    _GUARD.reset_for_test()
    get_audit_store().reset_for_test()
    get_evidence_registry().reset_for_test()


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


__all__ = [
    "reset_nyaya_api_state",
    "router",
]

