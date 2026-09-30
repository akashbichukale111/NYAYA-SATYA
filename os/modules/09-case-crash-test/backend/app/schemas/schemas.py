from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_demo: bool = False


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: Optional[str] = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class NodeCreate(BaseModel):
    node_type: str
    label: str
    status: str = "KNOWN"
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance_ref: Optional[str] = None


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    node_type: str
    label: str
    status: str
    attributes: dict[str, Any]
    provenance_ref: Optional[str] = None


class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    rel_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    source_id: str
    target_id: str
    rel_type: str
    attributes: dict[str, Any]


class GraphOut(BaseModel):
    nodes: list[NodeOut]
    relationships: list[RelationshipOut]


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    version: int
    label: Optional[str] = None
    created_at: datetime
    created_by: str


class SnapshotCreate(BaseModel):
    label: Optional[str] = None
    created_by: str = "user"


class MutationSpec(BaseModel):
    mutation_type: str
    target_node_id: str


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    preconditions: dict[str, Any] = Field(default_factory=dict)
    mutations: list[MutationSpec]
    is_technical_resilience_test: bool = False


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    name: str
    description: Optional[str] = None
    mutations: list[dict[str, Any]]
    is_technical_resilience_test: bool
    created_at: datetime


class SimulationCreate(BaseModel):
    base_snapshot_id: str
    scenario_id: Optional[str] = None
    inline_mutations: Optional[list[MutationSpec]] = None
    created_by: str = "user"
    explain: bool = False
    llm_provider: str = "mock"


class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    base_snapshot_id: str
    scenario_id: Optional[str] = None
    status: str
    created_at: datetime
    created_by: str
    result: Optional[dict[str, Any]] = None
    human_review_required: bool


class CompareRequest(BaseModel):
    simulation_id_a: str
    simulation_id_b: str


class RecoverySimulationRequest(BaseModel):
    """Apply a recovery mutation on top of an existing simulation's simulated state, as a further simulation only."""
    additional_mutations: list[MutationSpec]


class ReviewDecision(BaseModel):
    decided_by: str = "user"
    note: Optional[str] = None


class ReviewTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    simulation_id: Optional[str] = None
    node_id: Optional[str] = None
    reason: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    event_type: str
    actor: str
    payload: dict[str, Any]
    created_at: datetime


class IntegrationSummary(BaseModel):
    case_id: str
    base_state_version: Optional[int] = None
    active_simulations: int
    critical_dependencies: list[str]
    fragile_nodes: list[str]
    recent_failures: list[dict[str, Any]]
    affected_claims: list[str]
    affected_issues: list[str]
    affected_obligations: list[str]
    affected_deadlines: list[str]
    affected_hearings: list[str]
    affected_registry_defects: list[str]
    blocked_workflows: list[str]
    verification_gaps: list[str]
    human_review_items: list[str]
    provenance_refs: list[str]
    last_updated: Optional[datetime] = None
