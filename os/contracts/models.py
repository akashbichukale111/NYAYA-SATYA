"""NYAYA-SATYA OS Contracts
Defines standard schemas for:
- CaseContext: Global unified case scope with deep Digital Twin entity representations
- ModuleDefinition: Metadata for each of the 12 OS engines
- AttentionItem: Cross-project alert / action required
- CrossProjectEvent: Inter-module communication events
- SystemHealthReport: Real-time health metrics across all 12 modules
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class JurisdictionalDomain(str, Enum):
    CIVIL = "CIVIL"
    CRIMINAL = "CRIMINAL"
    CONSTITUTIONAL = "CONSTITUTIONAL"
    COMMERCIAL = "COMMERCIAL"
    REVENUE = "REVENUE"
    APPELLATE = "APPELLATE"


class ProceduralStage(str, Enum):
    INTAKE = "INTAKE"
    FILING_DEFECT_SCRUTINY = "FILING_DEFECT_SCRUTINY"
    BAIL_HEARING = "BAIL_HEARING"
    FRAMING_CHARGES = "FRAMING_CHARGES"
    EVIDENCE_RECORDING = "EVIDENCE_RECORDING"
    ARGUMENTS = "ARGUMENTS"
    JUDGMENT_RESERVED = "JUDGMENT_RESERVED"
    POST_JUDGMENT_REMEDIES = "POST_JUDGMENT_REMEDIES"


class ModuleCategory(str, Enum):
    EVIDENCE_REASONING = "Evidence & Reasoning"
    PROCEDURAL_GOVERNANCE = "Procedural & Compliance"
    CASE_ACCELERATION = "Case Acceleration & Bottlenecks"
    RIGHTS_PROTECTION = "Human Rights & Liberty"
    PRACTICE_AUTOMATION = "Personal OS & Autopilot"


class CaseContext(BaseModel):
    """The authoritative global case context passed across all 13 application experiences.
    Deeply embodies the Case Digital Twin entities, causal links, and operational status.
    """
    case_id: str = Field(..., description="Unique case identifier, e.g. CASE-2024-DEL-0482")
    title: str = Field(..., description="Human-readable title e.g. State v. Rajesh Kumar")
    court: str = Field("Tis Hazari District Court, Delhi", description="Court or registry jurisdiction")
    jurisdiction: JurisdictionalDomain = Field(JurisdictionalDomain.CRIMINAL)
    stage: ProceduralStage = Field(ProceduralStage.BAIL_HEARING)
    statute: str = Field("Bhartiya Nyaya Sanhita (BNS) §§ 303, 318 / CrPC § 437", description="Primary statute")
    filing_date: str = Field("2024-03-15")
    next_hearing: Optional[str] = Field("2024-10-14")
    lead_counsel: str = Field("Adv. Meenakshi Sundaram")
    undertrial_in_custody: bool = Field(True, description="Whether undertrial accused is in custody")
    custody_start_date: Optional[str] = Field("2023-08-10")
    human_authorized: bool = Field(False, description="UNWIND Gate: whether actions are signed by counsel")
    summary: str = Field("", description="Executive case background")
    tags: List[str] = Field(default_factory=list)

    # Deep Case Digital Twin Entities & Relations
    parties: List[Dict[str, Any]] = Field(default_factory=list, description="Parties and legal representations")
    documents: List[Dict[str, Any]] = Field(default_factory=list, description="Pleadings, annexures, and filings")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Evidence graph nodes with admissibility status")
    claims: List[Dict[str, Any]] = Field(default_factory=list, description="Substantive and procedural claims")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Framed legal & factual issues")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Factual and procedural events")
    timeline: List[Dict[str, Any]] = Field(default_factory=list, description="Chronological timeline of events")
    hearings: List[Dict[str, Any]] = Field(default_factory=list, description="Scheduled and concluded court hearings")
    orders: List[Dict[str, Any]] = Field(default_factory=list, description="Interlocutory and substantive court orders")
    obligations: List[Dict[str, Any]] = Field(default_factory=list, description="Statutory obligations (WHO/WHAT/LOSS/SIGN)")
    deadlines: List[Dict[str, Any]] = Field(default_factory=list, description="Statutory and court limitation deadlines")
    dependencies: List[Dict[str, Any]] = Field(default_factory=list, description="Causal and procedural dependencies")
    contradictions: List[Dict[str, Any]] = Field(default_factory=list, description="Contradictions flagged across evidence/claims")
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list, description="Procedural and evidentiary friction points")
    registry_defects: List[Dict[str, Any]] = Field(default_factory=list, description="Curable and non-curable defects from scrutiny")
    liberty_events: List[Dict[str, Any]] = Field(default_factory=list, description="Custody milestones and Sec 479 BNSS eligibility")
    workflows: List[Dict[str, Any]] = Field(default_factory=list, description="Active multi-stage workflow templates")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Action items pending or completed")
    reviews: List[Dict[str, Any]] = Field(default_factory=list, description="TARKA-VYUH adversarial review records")
    approvals: List[Dict[str, Any]] = Field(default_factory=list, description="UNWIND Human Legal Gate approvals")
    verification_state: Dict[str, Any] = Field(default_factory=dict, description="Integrity hashes and cross-check state")
    simulations: List[Dict[str, Any]] = Field(default_factory=list, description="Isolated counterfactual simulation records")
    provenance: List[Dict[str, Any]] = Field(default_factory=list, description="Evidence chains of custody & SHA256 hashes")
    audit_records: List[Dict[str, Any]] = Field(default_factory=list, description="Immutable ledger events")
    governance_state: Dict[str, Any] = Field(default_factory=dict, description="Active UNWIND state machine status")


class AttentionSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Immediate statutory/liberty jeopardy
    HIGH = "HIGH"          # Filing defect / unserved notice blocking hearing
    MEDIUM = "MEDIUM"      # Evidentiary gap / upcoming limitation deadline
    LOW = "LOW"            # Recommended optimization / workflow cleanup
    INFO = "INFO"          # System update


class AttentionItem(BaseModel):
    id: str
    case_id: str
    source_module_id: str
    source_module_name: str
    severity: AttentionSeverity
    title: str
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action_label: Optional[str] = None
    target_route: Optional[str] = None
    is_resolved: bool = False
    requires_human_signoff: bool = True


class CrossProjectEventType(str, Enum):
    EVIDENCE_GAP_DETECTED = "EVIDENCE_GAP_DETECTED"
    STATUTORY_DEADLINE_APPROACHING = "STATUTORY_DEADLINE_APPROACHING"
    REGISTRY_DEFECT_DETECTED = "REGISTRY_DEFECT_DETECTED"
    LIBERTY_THRESHOLD_SURPASSED = "LIBERTY_THRESHOLD_SURPASSED"
    BOTTLENECK_IDENTIFIED = "BOTTLENECK_IDENTIFIED"
    HEARING_UNREADY = "HEARING_UNREADY"
    OBLIGATION_UNFULFILLED = "OBLIGATION_UNFULFILLED"
    HUMAN_ACTION_AUTHORIZED = "HUMAN_ACTION_AUTHORIZED"


class CrossProjectEvent(BaseModel):
    event_id: str
    event_type: CrossProjectEventType
    case_id: str
    origin_module: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)


class ModuleHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    PARTIAL = "PARTIAL"
    OFFLINE = "OFFLINE"


class ModuleMetadata(BaseModel):
    module_id: str
    number: int
    name: str
    slug: str
    category: ModuleCategory
    tagline: str
    status: ModuleHealthStatus
    notes: Optional[str] = None
    api_prefix: str
    ui_route: str
    has_custom_frontend: bool
    features: List[str]
    active_attention_count: int = 0
