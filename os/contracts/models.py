"""NYAYA-SATYA OS Contracts
Defines standard schemas for:
- CaseContext: Global unified case scope (case_id, title, jurisdiction, stage, flags)
- ModuleDefinition: Metadata for each of the 12 OS engines
- AttentionItem: Cross-project alert / action required
- CrossProjectEvent: Inter-module communication events
- SystemHealthReport: Real-time health metrics across all 12 modules
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


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
    """The authoritative global case context passed across all 12 OS engines."""
    case_id: str = Field(..., description="Unique case identifier, e.g. CASE-2024-DEL-0482")
    title: str = Field(..., description="Human-readable title e.g. State v. Rajesh Kumar")
    court: str = Field("Tis Hazari District Court, Delhi", description="Court or registry jurisdiction")
    jurisdiction: JurisdictionalDomain = Field(JurisdictionalDomain.CRIMINAL)
    stage: ProceduralStage = Field(ProceduralStage.BAIL_HEARING)
    statute: str = Field("Bhartiya Nyaya Sanhita (BNS) / CrPC", description="Primary substantive/procedural statute")
    filing_date: str = Field("2024-03-15")
    next_hearing: Optional[str] = Field("2024-10-14")
    lead_counsel: str = Field("Adv. Meenakshi Sundaram")
    undertrial_in_custody: bool = Field(True, description="Whether undertrial accused is in judicial custody")
    custody_start_date: Optional[str] = Field("2023-08-10")
    human_authorized: bool = Field(False, description="UNWIND Gate: whether pending actions are signed by human lawyer")
    summary: str = Field("", description="Executive case background")
    tags: List[str] = Field(default_factory=list)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
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
