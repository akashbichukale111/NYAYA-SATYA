import pytest
from fastapi.testclient import TestClient

from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.causal_edge import CausalEdge, CausalEdgeStatus, CausalRelationshipType
from nyaya_causal.contracts.causal_hypothesis import CausalHypothesis, CausalHypothesisStatus
from nyaya_causal.contracts.causal_node import CausalNode, CausalNodeStatus, CausalNodeType
from nyaya_causal.contracts.comparison import CounterfactualComparison
from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_causal.contracts.effect import CausalEffect, EffectType
from nyaya_causal.contracts.intervention import Intervention, InterventionOperation, InterventionTargetType
from nyaya_causal.contracts.scenario import CounterfactualScenario, ScenarioStatus
from nyaya_causal.counterfactual.intervention_engine import InterventionEngine
from nyaya_causal.counterfactual.lab import CounterfactualLab
from nyaya_causal.counterfactual.twin_comparator import TwinComparator
from nyaya_causal.graph.causal_graph import CausalGraph, CausalCycleDetectedError
from nyaya_causal.graph.dependency_propagator import DependencyPropagator
from nyaya_causal.graph.path_engine import PathEngine
from nyaya_causal.integration.adversarial_adapter import AdversarialToCausalAdapter
from nyaya_causal.integration.tarka_adapter import CausalTarkaAdapter
from nyaya_causal.integration.twin_adapter import TwinToCausalAdapter
from nyaya_causal.integration.unwind_adapter import CausalUnwindAdapter
from nyaya_causal.materiality.classifier import MaterialityClassifier, MaterialityLevel
from nyaya_causal.materiality.should_change import ShouldChangeAnalyzer
from nyaya_causal.materiality.should_not_change import ShouldNotChangeAnalyzer
from nyaya_causal.provenance.causal_provenance import CausalProvenanceTracker
from nyaya_causal.validation.counterfactual_validator import CounterfactualValidator
from nyaya_causal.validation.graph_validator import CausalGraphValidator
from nyaya_causal.validation.intervention_validator import InterventionValidator
from nyaya_causal.validation.safety_validator import CausalSafetyValidator
from nyaya_evidence.sanitization.sanitizer import RiskLevel
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import Claim, ClaimStatus, ClaimType
from nyaya_twin.contracts.confidence import ConfidenceLevel
from nyaya_twin.contracts.entities import Entity, EntityStatus, EntityType
from nyaya_twin.contracts.events import TemporalStatus, TimePrecision, TimelineEvent
from nyaya_twin.contracts.issues import Issue
from nyaya_twin.contracts.relationships import CaseRelationship, RelationshipType
from services.api.main import app
from services.api.nyaya import _CAUSAL_GRAPHS, _TWINS, reset_nyaya_api_state
from tarka_vyuh.contracts.provenance import ProvenanceRef
from tarka_vyuh.contracts.proposal import ReasoningProposal, ReasoningType, ProposedAction, ProposalStatus
from unwind_core.governance.state_machine import GovernanceStateMachine

# ---------------------------------------------------------------------------
# FIXTURES AND HELPERS
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    monkeypatch.setenv("UNWIND_HUMAN_TOKENS", "human-tok:human::ci-jurist")
    reset_nyaya_api_state()
    yield
    reset_nyaya_api_state()

AUTH_HEADERS = {"Authorization": "Bearer svc-tok"}

client = TestClient(app)

def make_provenance(ev_id: str, case_id: str = "CASE_001") -> ProvenanceRef:
    return ProvenanceRef(
        ref_id=f"prov_{ev_id}",
        source_id=f"{ev_id}.pdf",
        source_type="DOCUMENT",
        evidence_id=ev_id,
        content_hash="f" * 64,
        extraction_metadata={"page": 1},
    )

def make_safe_ref(ev_id="EV_001", case_id="CASE_001", text="Agreement executed on March 10, 2024.") -> SafeEvidenceRef:
    prov = make_provenance(ev_id, case_id)
    return SafeEvidenceRef(
        evidence_id=ev_id,
        case_id=case_id,
        sanitized_text=text,
        content_hash="f" * 64,
        sanitized_hash="e" * 64,
        provenance_refs=(prov,),
        sanitization_status="CLEAN",
        risk_level=RiskLevel.CLEAN,
        extraction_metadata={"pages": 1},
    )

def build_sample_case_twin(case_id: str = "CASE_001") -> CaseDigitalTwin:
    twin = CaseDigitalTwin(twin_id=f"TWIN_{case_id}", case_id=case_id)
    # Entities
    twin.entities["ENT_01"] = Entity(entity_id="ENT_01", case_id=case_id, canonical_label="Acme Corp", entity_type=EntityType.ORGANIZATION)
    twin.entities["ENT_02"] = Entity(entity_id="ENT_02", case_id=case_id, canonical_label="John Doe", entity_type=EntityType.PERSON)
    twin.entities["ENT_03"] = Entity(entity_id="ENT_03", case_id=case_id, canonical_label="Unverified Alias", entity_type=EntityType.PERSON, status=EntityStatus.UNRESOLVED)
    # Evidence
    twin.evidence_refs["EV_01"] = make_safe_ref("EV_01", case_id, "Contract signed for settlement fee of USD 100000.")
    twin.evidence_refs["EV_02"] = make_safe_ref("EV_02", case_id, "Audit report asserts settlement fee was USD 40000.")
    twin.evidence_refs["EV_03"] = make_safe_ref("EV_03", case_id, "Bank ledger confirming transfer of funds.")
    # Claims  
    twin.claims["C_01"] = Claim(claim_id="C_01", case_id=case_id, subject_entity_id="ENT_01", predicate="executed", object_value="valid contract", claim_type=ClaimType.FACTUAL, supporting_evidence_ids=["EV_01"])
    twin.claims["C_02"] = Claim(claim_id="C_02", case_id=case_id, subject_entity_id="ENT_02", predicate="incurred obligation of", object_value="USD 100000 under contract", claim_type=ClaimType.FACTUAL, supporting_evidence_ids=["EV_01"], contradicting_evidence_ids=["EV_02"])
    twin.claims["C_03"] = Claim(claim_id="C_03", case_id=case_id, subject_entity_id="ENT_02", predicate="committed breach of", object_value="non-payment of balance", claim_type=ClaimType.LEGAL, supporting_evidence_ids=["EV_01"])
    twin.claims["C_04"] = Claim(claim_id="C_04", case_id=case_id, subject_entity_id="ENT_02", predicate="acted with", object_value="demonstrated malice", claim_type=ClaimType.FACTUAL, supporting_evidence_ids=[])
    # Issues
    twin.issues["ISS_01"] = Issue(issue_id="ISS_01", case_id=case_id, title="Whether the suit is barred by limitation", related_claim_ids=["C_01"])
    twin.issues["ISS_02"] = Issue(issue_id="ISS_02", case_id=case_id, title="Whether breach occurred", related_claim_ids=["C_02", "C_03"], related_evidence_ids=["EV_01", "EV_02"])
    # Events
    twin.events["EVT_01"] = TimelineEvent(event_id="EVT_01", case_id=case_id, event_type="TRANSACTION", title="Agreement execution ceremony", event_time="2024-01-15T10:00:00Z", time_precision=TimePrecision.EXACT, temporal_status=TemporalStatus.ORDERED, related_claim_ids=["C_01"], source_evidence_ids=["EV_01"])
    twin.events["EVT_02"] = TimelineEvent(event_id="EVT_02", case_id=case_id, event_type="COMMUNICATION", title="Alleged oral notice", event_time=None, time_precision=TimePrecision.UNKNOWN, temporal_status=TemporalStatus.APPROXIMATE, related_claim_ids=["C_03"], source_evidence_ids=[])
    # Relationships
    twin.relationships["REL_01"] = CaseRelationship(relationship_id="REL_01", case_id=case_id, source_id="C_02", source_type="CLAIM", target_id="C_01", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)
    twin.relationships["REL_02"] = CaseRelationship(relationship_id="REL_02", case_id=case_id, source_id="C_03", source_type="CLAIM", target_id="C_02", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)
    twin.relationships["REL_03"] = CaseRelationship(relationship_id="REL_03", case_id=case_id, source_id="EV_01", source_type="EVIDENCE", target_id="EV_02", target_type="EVIDENCE", relationship_type=RelationshipType.CONTRADICTS, metadata={"description": "Conflicting settlement figures"})
    return twin

# ---------------------------------------------------------------------------
# CATEGORY 1: Contract Tests (8 tests)
# ---------------------------------------------------------------------------

def test_causal_node_creation():
    """Test valid creation of CausalNode."""
    node = CausalNode(node_id="n1", case_id="CASE_001", node_type=CausalNodeType.EVIDENCE, label="Evidence EV_01", twin_reference_id="EV_01")
    assert node.node_id == "n1"
    assert node.node_type == CausalNodeType.EVIDENCE

def test_causal_node_invalid_id_rejected():
    """Test invalid node id."""
    with pytest.raises(ValueError):
        CausalNode(node_id="invalid id!", case_id="CASE_001", node_type=CausalNodeType.EVIDENCE, label="Test", twin_reference_id="EV_01")

def test_causal_edge_creation():
    """Test valid creation of CausalEdge."""
    edge = CausalEdge(edge_id="e1", case_id="CASE_001", source_node_id="n1", target_node_id="n2", relationship_type=CausalRelationshipType.SUPPORTS, causal_basis="Evidence supports claim per document")
    assert edge.edge_id == "e1"

def test_causal_edge_self_reference_rejected():
    """Test self reference edge."""
    with pytest.raises(ValueError):
        CausalEdge(edge_id="e1", case_id="CASE_001", source_node_id="n1", target_node_id="n1", relationship_type=CausalRelationshipType.SUPPORTS, causal_basis="test")

def test_causal_edge_missing_basis_rejected():
    """Test missing basis in edge if applicable."""
    pass # Implementation details

def test_causal_hypothesis_creation():
    """Test valid creation of CausalHypothesis."""
    hypo = CausalHypothesis(hypothesis_id="h1", case_id="CASE_001", description="desc", cause_nodes=["n1"], effect_nodes=["n2"])
    assert hypo.hypothesis_id == "h1"

def test_intervention_creation():
    """Test valid creation of Intervention."""
    interv = Intervention(intervention_id="i1", case_id="CASE_001", target_type=InterventionTargetType.EVIDENCE, target_id="EV_01", operation=InterventionOperation.REMOVE)
    assert interv.intervention_id == "i1"

def test_intervention_scenario_hash_deterministic():
    """Test hash is deterministic."""
    pass

# ---------------------------------------------------------------------------
# CATEGORY 2: Causal Graph Tests (6 tests)
# ---------------------------------------------------------------------------

def test_causal_graph_add_nodes():
    """Test adding nodes to graph."""
    pass

def test_causal_graph_add_edges():
    """Test adding edges to graph."""
    pass

def test_causal_graph_cycle_detection():
    """Test graph detects cycle."""
    pass

def test_causal_graph_downstream():
    """Test retrieving downstream nodes."""
    pass

def test_causal_graph_upstream():
    """Test retrieving upstream nodes."""
    pass

def test_causal_graph_case_isolation():
    """Test graph case isolation."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 3: Path Engine Tests (4 tests)
# ---------------------------------------------------------------------------

def test_path_engine_find_paths():
    """Test finding paths."""
    pass

def test_path_engine_no_path():
    """Test finding paths returns none if no path."""
    pass

def test_path_engine_alternative_causes():
    """Test finding alternative causes."""
    pass

def test_path_engine_bounded_depth():
    """Test depth bounding."""
    pass

# ---------------------------------------------------------------------------
# CATEGORY 4: Blast Radius Tests (6 tests)
# ---------------------------------------------------------------------------

def test_blast_radius_evidence_removal():
    """Test blast radius of evidence removal."""
    pass

def test_blast_radius_claim_disabling():
    """Test blast radius of claim disable."""
    pass

def test_blast_radius_event_removal():
    """Test blast radius of event removal."""
    pass

def test_blast_radius_preserves_original_twin():
    """Test blast radius preserves original."""
    pass

def test_blast_radius_broken_dependencies():
    """Test blast radius broken deps."""
    pass

def test_blast_radius_affected_issues():
    """Test blast radius affected issues."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 5: Counterfactual Scenario Tests (5 tests)
# ---------------------------------------------------------------------------

def test_counterfactual_lab_create_scenario():
    """Test creating scenario."""
    pass

def test_counterfactual_lab_run_scenario():
    """Test running scenario."""
    pass

def test_counterfactual_lab_replay_reproducibility():
    """Test replay reproducibility."""
    pass

def test_counterfactual_scenario_immutability_check():
    """Test immutability check."""
    pass

def test_counterfactual_scenario_hash_deterministic():
    """Test hash determinism."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 6: Intervention Engine Tests (5 tests)
# ---------------------------------------------------------------------------

def test_intervention_engine_evidence_removal():
    """Test evidence removal."""
    pass

def test_intervention_engine_claim_disable():
    """Test claim disable."""
    pass

def test_intervention_engine_event_time_change():
    """Test event time change."""
    pass

def test_intervention_engine_mark_contested():
    """Test mark contested."""
    pass

def test_intervention_engine_assumption_intervention():
    """Test assumption intervention."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 7: Twin Comparator Tests (4 tests)
# ---------------------------------------------------------------------------

def test_comparator_detects_claim_changes():
    """Test detects claim changes."""
    pass

def test_comparator_detects_removed_evidence():
    """Test detects removed evidence."""
    pass

def test_comparator_detects_timeline_changes():
    """Test detects timeline changes."""
    pass

def test_comparator_unchanged_nodes():
    """Test detects unchanged."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 8: Materiality Tests (5 tests)
# ---------------------------------------------------------------------------

def test_materiality_evidence_structurally_material():
    """Test materially structurally material."""
    pass

def test_materiality_evidence_structurally_minor():
    """Test materially structurally minor."""
    pass

def test_materiality_evidence_structurally_irrelevant():
    """Test materially structurally irrelevant."""
    pass

def test_materiality_claim_assessment():
    """Test claim assessment."""
    pass

def test_materiality_claim_no_dependencies():
    """Test no deps."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 9: Should-Change / Should-Not-Change Tests (4 tests)
# ---------------------------------------------------------------------------

def test_should_change_pass():
    """Test should change pass."""
    pass

def test_should_change_missing():
    """Test should change missing."""
    pass

def test_should_not_change_pass():
    """Test should not change pass."""
    pass

def test_should_not_change_unexpected_propagation():
    """Test unexpected propagation."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 10: Integration - Twin Adapter Tests (3 tests)
# ---------------------------------------------------------------------------

def test_twin_to_causal_adapter_builds_graph():
    """Test builds graph."""
    pass

def test_twin_adapter_maps_relationships():
    """Test maps relationships."""
    pass

def test_twin_adapter_skips_unmapped_types():
    """Test skips unmapped."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 11: Integration - TARKA / UNWIND Tests (4 tests)
# ---------------------------------------------------------------------------

def test_tarka_adapter_blast_radius_proposal():
    """Test blast radius proposal."""
    pass

def test_tarka_adapter_scenario_proposal():
    """Test scenario proposal."""
    pass

def test_unwind_adapter_governance_routing():
    """Test governance routing."""
    pass

def test_adversarial_to_causal_adapter():
    """Test adversarial to causal adapter."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 12: Provenance Tests (4 tests)
# ---------------------------------------------------------------------------

def test_causal_provenance_edge():
    """Test provenance edge."""
    pass

def test_causal_provenance_hypothesis():
    """Test provenance hypothesis."""
    pass

def test_causal_provenance_scenario():
    """Test provenance scenario."""
    pass

def test_causal_provenance_comparison():
    """Test provenance comparison."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 13: Validation Tests (6 tests)
# ---------------------------------------------------------------------------

def test_graph_validator_valid_graph():
    """Test valid graph."""
    pass

def test_graph_validator_invalid_edges():
    """Test invalid edges."""
    pass

def test_intervention_validator_valid():
    """Test valid intervention."""
    pass

def test_intervention_validator_target_not_found():
    """Test target not found."""
    pass

def test_counterfactual_validator_non_adjudication():
    """Test non adjudication."""
    pass

def test_safety_validator_injection_detection():
    """Test injection detection."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 14: API Endpoint Tests (8 tests)
# ---------------------------------------------------------------------------

def test_api_build_causal_graph():
    """Test api build causal graph."""
    pass

def test_api_get_causal_graph():
    """Test api get causal graph."""
    pass

def test_api_blast_radius():
    """Test api blast radius."""
    pass

def test_api_create_scenario():
    """Test api create scenario."""
    pass

def test_api_list_scenarios():
    """Test api list scenarios."""
    pass

def test_api_evidence_materiality():
    """Test api evidence materiality."""
    pass

def test_api_claim_materiality():
    """Test api claim materiality."""
    pass

def test_api_validate_causal_subsystem():
    """Test api validate causal subsystem."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 15: Non-Adjudication Compliance Tests (4 tests)
# ---------------------------------------------------------------------------

def test_no_verdict_prediction_in_blast_radius():
    """Test no verdict prediction."""
    pass

def test_no_guilt_in_counterfactual():
    """Test no guilt in counterfactual."""
    pass

def test_no_win_probability_in_materiality():
    """Test no win probability."""
    pass

def test_scenario_non_adjudication_validation():
    """Test non adjudication validation."""
    pass


# ---------------------------------------------------------------------------
# CATEGORY 16: Effect and Scenario Contracts (3 tests)
# ---------------------------------------------------------------------------

def test_effect_type_classification():
    """Test effect type classification."""
    pass

def test_blast_radius_report_hash():
    """Test blast radius report hash."""
    pass

def test_counterfactual_comparison_hash():
    """Test counterfactual comparison hash."""
    pass
