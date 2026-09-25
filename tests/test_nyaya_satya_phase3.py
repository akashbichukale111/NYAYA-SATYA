"""Comprehensive Test Suite for NYAYA-SATYA Phase 3.

Validates:
- Case Digital Twin container, deterministic serialization, integrity hash, versioning
- Entity model, resolution states (exact, alias, possible match, unresolved)
- Claims, structured evidence states (SUPPORTED, CONTRADICTED, UNSUPPORTED)
- Issues, questions, and claim/evidence associations
- Timeline, exact/approximate/month/year/unknown precisions, temporal conflict detection
- Graph models (CaseGraph, ClaimGraph, EvidenceGraph, TimelineGraph, DependencyGraph)
- Graph integrity validation against all 15 rules
- Provenance validation, unbroken lineage, hash integrity
- Cross-case security isolation (Case A vs Case B)
- TARKA-VYUH integration and blocked unimplemented capabilities
- UNWIND governance compatibility and human legal gate alignment
- Complete REST API lifecycle (/api/nyaya/cases/{id}/twin/...)
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime
from fastapi.testclient import TestClient

from lib.auth import Principal
from nyaya_evidence.contracts.case import Case
from nyaya_evidence.contracts.evidence import (
    EvidenceItem,
    EvidenceSource,
    EvidenceStatus,
    MediaType,
)
from nyaya_evidence.quarantine.manager import QuarantineViolationError
from nyaya_evidence.sanitization.sanitizer import RiskLevel
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_evidence.contradiction.engine import (
    ContradictionCandidate,
    ContradictionType,
)
from nyaya_twin.contracts.confidence import (
    ConfidenceAssessment,
    ConfidenceLevel,
    assess_claim_confidence,
)
from nyaya_twin.contracts.entities import (
    Entity,
    EntityResolutionType,
    EntityStatus,
    EntityType,
)
from nyaya_twin.contracts.claims import (
    Claim,
    ClaimStatus,
    ClaimType,
)
from nyaya_twin.contracts.issues import (
    Issue,
    IssueStatus,
)
from nyaya_twin.contracts.events import (
    TemporalStatus,
    TimePrecision,
    TimelineEvent,
)
from nyaya_twin.contracts.relationships import (
    CaseRelationship,
    RelationshipType,
)
from nyaya_twin.contracts.case_twin import (
    CaseDigitalTwin,
    compute_twin_hash,
)
from nyaya_twin.graph.dependency_graph import (
    DependencyCycleError,
    DependencyGraph,
)
from nyaya_twin.graph.claim_graph import ClaimGraph
from nyaya_twin.graph.evidence_graph import EvidenceGraph
from nyaya_twin.graph.timeline_graph import TimelineGraph
from nyaya_twin.graph.case_graph import CaseGraph
from nyaya_twin.builders.entity_builder import EntityBuilder
from nyaya_twin.builders.claim_builder import ClaimBuilder
from nyaya_twin.builders.timeline_builder import TimelineBuilder
from nyaya_twin.builders.twin_builder import CaseTwinBuilder
from nyaya_twin.validation.graph_validator import (
    GraphValidationResult,
    validate_case_graph,
)
from nyaya_twin.validation.provenance_validator import validate_provenance_chain
from nyaya_twin.validation.temporal_validator import validate_temporal_integrity
from nyaya_twin.traversal.evidence_paths import (
    get_contradicting_evidence_for_claim,
    get_evidence_dependent_claims,
    get_supporting_evidence_for_claim,
    get_unsupported_claims,
)
from nyaya_twin.traversal.claim_dependencies import (
    get_claim_ancestors,
    get_claim_descendants,
    get_claim_dependents,
    get_claim_prerequisites,
)
from nyaya_twin.traversal.downstream_impact import compute_evidence_invalidation_impact
from nyaya_twin.integration.evidence_adapter import CaseTwinEvidenceAdapter
from nyaya_twin.integration.tarka_adapter import CaseTwinTarkaAdapter
from tarka_vyuh.contracts.proposal import ReasoningType
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256
from tarka_vyuh.reasoning.registry import ReasoningEngineNotImplementedError
from services.api.main import app
from services.api.nyaya import reset_nyaya_api_state
from nyaya_evidence.registry.store import get_evidence_registry


# ============================================================================
# TEST FIXTURES & HELPERS
# ============================================================================
@pytest.fixture(autouse=True)
def clean_state():
    reset_nyaya_api_state()
    yield
    reset_nyaya_api_state()


def make_provenance(ev_id: str, case_id: str = "CASE_001") -> ProvenanceRef:
    return ProvenanceRef(
        ref_id=f"prov_{ev_id}",
        source_id="affidavit_01.pdf",
        source_type="AFFIDAVIT",
        evidence_id=ev_id,
        content_hash="a" * 64,
        extraction_metadata={"page": 1},
    )


def make_safe_ref(
    ev_id: str = "EV_001",
    case_id: str = "CASE_001",
    text: str = "Agreement executed on March 10, 2024.",
) -> SafeEvidenceRef:
    prov = make_provenance(ev_id, case_id)
    return SafeEvidenceRef(
        evidence_id=ev_id,
        case_id=case_id,
        sanitized_text=text,
        content_hash="a" * 64,
        sanitized_hash="b" * 64,
        provenance_refs=(prov,),
        sanitization_status="CLEAN",
        risk_level=RiskLevel.CLEAN,
        extraction_metadata={"pages": 1},
    )


def make_evidence_item(
    evidence_id: str = "EV_001",
    case_id: str = "CASE_001",
    status: EvidenceStatus = EvidenceStatus.REGISTERED,
) -> EvidenceItem:
    src = EvidenceSource(source_id=f"src_{evidence_id}", source_type="DOCUMENT_UPLOAD")
    return EvidenceItem(
        evidence_id=evidence_id,
        case_id=case_id,
        source_id=f"src_{evidence_id}",
        filename=f"{evidence_id.lower()}.pdf",
        media_type=MediaType.APPLICATION_PDF,
        size_bytes=1024,
        content_hash="a" * 64,
        source=src,
        status=status,
    )


# ============================================================================
# 1. CASE DIGITAL TWIN CONTAINER & INTEGRITY
# ============================================================================
def test_case_digital_twin_creation():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    assert twin.twin_id == "twin_01"
    assert twin.case_id == "CASE_001"
    assert twin.version == 1
    assert len(twin.integrity_hash) == 64


def test_case_digital_twin_deterministic_serialization():
    twin1 = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin2 = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    assert twin1.integrity_hash == twin2.integrity_hash
    snap1 = twin1.snapshot()
    snap2 = twin2.snapshot()
    assert snap1["integrity_hash"] == snap2["integrity_hash"]


def test_case_digital_twin_version_increment_and_audit():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    assert twin.version == 1
    initial_hash = twin.integrity_hash

    twin.record_version(
        actor="advocate_smith",
        reason="Added lease agreement evidence",
        changed_nodes=["ent_01", "clm_01"],
        changed_relationships=["rel_01"],
    )
    assert twin.version == 2
    assert len(twin.version_history) == 1
    rec = twin.version_history[0]
    assert rec.actor == "advocate_smith"
    assert rec.parent_version is None
    assert rec.integrity_hash == initial_hash


def test_case_digital_twin_snapshot_integrity_hash():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    snap = twin.snapshot()
    assert "entities" in snap
    assert "claims" in snap
    assert "evidence_refs" in snap
    assert "version_history" in snap
    assert snap["source_version"] == "3.0.0"


def test_case_digital_twin_invalid_id_raises():
    with pytest.raises(ValueError, match="blank"):
        CaseDigitalTwin(twin_id="", case_id="CASE_001")
    with pytest.raises(ValueError, match="Invalid twin_id"):
        CaseDigitalTwin(twin_id="twin with spaces", case_id="CASE_001")


# ============================================================================
# 2. ENTITY MODEL & RESOLUTION
# ============================================================================
def test_entity_creation_and_fields():
    ent = Entity(
        entity_id="ent_person_a",
        case_id="CASE_001",
        entity_type=EntityType.PERSON,
        canonical_label="Rajesh Kumar",
        aliases=["R. Kumar", "Rajesh K."],
        status=EntityStatus.POSSIBLE_MATCH,
    )
    assert ent.canonical_label == "Rajesh Kumar"
    assert ent.status == EntityStatus.POSSIBLE_MATCH
    assert ent.confidence == ConfidenceLevel.MEDIUM


def test_entity_exact_label_match():
    ent = Entity(
        entity_id="ent_p1",
        case_id="CASE_001",
        entity_type=EntityType.PERSON,
        canonical_label="Rajesh Kumar",
    )
    assert ent.matches_label("Rajesh Kumar") is EntityResolutionType.EXACT_MATCH
    assert ent.matches_label("rajesh kumar") is EntityResolutionType.EXACT_MATCH


def test_entity_alias_match():
    ent = Entity(
        entity_id="ent_p1",
        case_id="CASE_001",
        entity_type=EntityType.PERSON,
        canonical_label="Rajesh Kumar",
        aliases=["Mr. Kumar", "R. Kumar"],
    )
    assert ent.matches_label("Mr. Kumar") is EntityResolutionType.ALIAS_MATCH
    assert ent.matches_label("r. kumar") is EntityResolutionType.ALIAS_MATCH


def test_entity_possible_match_partial_tokens():
    ent = Entity(
        entity_id="ent_p1",
        case_id="CASE_001",
        entity_type=EntityType.PERSON,
        canonical_label="Rajesh Kumar",
    )
    # Partial token "Rajesh" is a possible match, not exact
    assert ent.matches_label("Rajesh") is EntityResolutionType.POSSIBLE_MATCH


def test_entity_unresolved_match():
    ent = Entity(
        entity_id="ent_p1",
        case_id="CASE_001",
        entity_type=EntityType.PERSON,
        canonical_label="Rajesh Kumar",
    )
    assert ent.matches_label("Vikram Sharma") is EntityResolutionType.UNRESOLVED


def test_entity_builder_auto_id_and_resolution():
    eb = EntityBuilder(case_id="CASE_001")
    e1 = eb.add_entity(canonical_label="Acme Infra Corp", entity_type=EntityType.ORGANIZATION)
    assert e1.entity_type == EntityType.ORGANIZATION
    assert e1.entity_id.startswith("ent_acme_infra_corp")

    resolved_ent, res_type = eb.resolve_label("Acme Infra Corp")
    assert resolved_ent is not None
    assert res_type is EntityResolutionType.EXACT_MATCH


# ============================================================================
# 3. CLAIM MODEL & CONFIDENCE EVALUATION
# ============================================================================
def test_claim_creation_and_statement():
    prov = make_provenance("EV_001")
    clm = Claim(
        claim_id="clm_01",
        case_id="CASE_001",
        subject_entity_id="ent_person_a",
        predicate="EXECUTED",
        object_value="AGREEMENT_2024",
        source_evidence_ids=["EV_001"],
        supporting_evidence_ids=["EV_001"],
        provenance_refs=[prov],
    )
    assert clm.statement == "ent_person_a EXECUTED AGREEMENT_2024"
    assert clm.claim_type == ClaimType.FACTUAL


def test_claim_status_supported_when_evidence_linked():
    clm = Claim(
        claim_id="clm_01",
        case_id="CASE_001",
        subject_entity_id="ent_p1",
        predicate="RECEIVED",
        object_value="PAYMENT",
        source_evidence_ids=["EV_001"],
        supporting_evidence_ids=["EV_001", "EV_002"],
    )
    assert clm.evaluate_evidence_status() == ClaimStatus.SUPPORTED


def test_claim_status_contradicted_when_conflict_linked():
    clm = Claim(
        claim_id="clm_01",
        case_id="CASE_001",
        subject_entity_id="ent_p1",
        predicate="DEFAULTED_ON",
        object_value="LOAN",
        supporting_evidence_ids=["EV_001"],
        contradicting_evidence_ids=["EV_003"],
    )
    assert clm.evaluate_evidence_status() == ClaimStatus.CONTRADICTED


def test_claim_status_unsupported_when_no_evidence():
    clm = Claim(
        claim_id="clm_01",
        case_id="CASE_001",
        subject_entity_id="ent_p1",
        predicate="PROMISED",
        object_value="REPAIR",
        supporting_evidence_ids=[],
    )
    assert clm.evaluate_evidence_status() == ClaimStatus.UNSUPPORTED


def test_claim_confidence_high_with_corroboration():
    conf = assess_claim_confidence(supporting_count=2, contradicting_count=0)
    assert conf.level == ConfidenceLevel.HIGH
    assert "Corroborated by 2 independent" in conf.basis[0]


def test_claim_confidence_medium_with_single_evidence():
    conf = assess_claim_confidence(supporting_count=1, contradicting_count=0)
    assert conf.level == ConfidenceLevel.MEDIUM


def test_claim_confidence_low_with_contradiction_or_broken_provenance():
    conf_broken = assess_claim_confidence(
        supporting_count=2, contradicting_count=0, has_unbroken_provenance=False
    )
    assert conf_broken.level == ConfidenceLevel.LOW

    conf_contra = assess_claim_confidence(supporting_count=0, contradicting_count=1)
    assert conf_contra.level == ConfidenceLevel.LOW


def test_claim_confidence_unknown_when_no_evidence():
    conf = assess_claim_confidence(supporting_count=0, contradicting_count=0)
    assert conf.level == ConfidenceLevel.UNKNOWN


# ============================================================================
# 4. ISSUE MODEL
# ============================================================================
def test_issue_creation_and_status():
    issue = Issue(
        issue_id="iss_01",
        case_id="CASE_001",
        title="Dispute over Payment Timeliness",
        description="Whether payment on March 15 met contractual deadline",
        related_claim_ids=["clm_01", "clm_02"],
        related_evidence_ids=["EV_001"],
        unresolved_questions=["Was grace period invoked in writing?"],
        status=IssueStatus.OPEN,
    )
    assert issue.status == IssueStatus.OPEN
    assert len(issue.related_claim_ids) == 2
    assert "grace period" in issue.unresolved_questions[0]


# ============================================================================
# 5. TIMELINE EVENTS & PRECISION PRESERVATION
# ============================================================================
def test_timeline_event_exact_precision():
    ev = TimelineEvent(
        event_id="evt_01",
        case_id="CASE_001",
        event_type="EXECUTION",
        title="Signing of Contract",
        event_time="2024-03-10T14:30:00Z",
        time_precision=TimePrecision.EXACT,
    )
    assert ev.time_precision == TimePrecision.EXACT
    assert ev.event_time == "2024-03-10T14:30:00Z"


def test_timeline_event_approximate_month_precision_rejects_exact_clock_time():
    with pytest.raises(ValueError, match="Fabrication error"):
        TimelineEvent(
            event_id="evt_02",
            case_id="CASE_001",
            event_type="MEETING",
            title="Informal Meeting",
            event_time="2024-03-10T14:30:00Z",
            time_precision=TimePrecision.MONTH,
        )


def test_timeline_event_year_precision_preserves_year():
    ev = TimelineEvent(
        event_id="evt_03",
        case_id="CASE_001",
        event_type="FORMATION",
        title="Company Founded",
        event_time="2021",
        time_precision=TimePrecision.YEAR,
    )
    assert ev.time_precision == TimePrecision.YEAR
    assert ev.event_time == "2021"


def test_timeline_graph_chronological_ordering():
    tg = TimelineGraph(case_id="CASE_001")
    e3 = TimelineEvent(event_id="e3", case_id="CASE_001", event_type="E", title="Third", event_time="2024-05-01", time_precision=TimePrecision.DATE)
    e1 = TimelineEvent(event_id="e1", case_id="CASE_001", event_type="E", title="First", event_time="2024-01-10", time_precision=TimePrecision.DATE)
    e2 = TimelineEvent(event_id="e2", case_id="CASE_001", event_type="E", title="Second", event_time="2024-03-15", time_precision=TimePrecision.DATE)
    e_unk = TimelineEvent(event_id="e0", case_id="CASE_001", event_type="E", title="Unknown Date", time_precision=TimePrecision.UNKNOWN)

    tg.add_event(e3)
    tg.add_event(e1)
    tg.add_event(e2)
    tg.add_event(e_unk)

    stream = tg.get_chronological_stream()
    assert [ev.event_id for ev in stream] == ["e1", "e2", "e3", "e0"]


def test_timeline_graph_participant_filtering():
    tg = TimelineGraph(case_id="CASE_001")
    e1 = TimelineEvent(event_id="e1", case_id="CASE_001", event_type="E", title="Meeting A", participants=["Alice", "Bob"], time_precision=TimePrecision.DATE)
    e2 = TimelineEvent(event_id="e2", case_id="CASE_001", event_type="E", title="Meeting B", participants=["Bob", "Charlie"], time_precision=TimePrecision.DATE)
    tg.add_event(e1)
    tg.add_event(e2)

    alice_events = tg.get_events_for_participant("Alice")
    assert len(alice_events) == 1
    assert alice_events[0].event_id == "e1"

    bob_events = tg.get_events_for_participant("bob")
    assert len(bob_events) == 2


def test_timeline_temporal_conflict_detection():
    tg = TimelineGraph(case_id="CASE_001")
    # Two events regarding the same agreement signing with discordant dates
    e1 = TimelineEvent(
        event_id="e1",
        case_id="CASE_001",
        event_type="EXECUTION",
        title="Agreement Execution Signed",
        event_time="2024-03-10",
        time_precision=TimePrecision.DATE,
        source_evidence_ids=["EV_001"],
    )
    e2 = TimelineEvent(
        event_id="e2",
        case_id="CASE_001",
        event_type="EXECUTION",
        title="Agreement Execution Signed",
        event_time="2024-04-15",
        time_precision=TimePrecision.DATE,
        source_evidence_ids=["EV_002"],
    )
    tg.add_event(e1)
    tg.add_event(e2)

    conflicts = tg.detect_temporal_conflicts()
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["conflict_type"] == "TEMPORAL_CONFLICT"
    assert c["date_a"] == "2024-03-10"
    assert c["date_b"] == "2024-04-15"
    assert c["status"] == "UNRESOLVED"


def test_temporal_validator_flags_interval_inversion():
    ev = TimelineEvent(
        event_id="e1",
        case_id="CASE_001",
        event_type="LEASE",
        title="Lease Period",
        start_time="2024-12-01",
        end_time="2024-01-01",
        time_precision=TimePrecision.RANGE,
    )
    errors = validate_temporal_integrity([ev])
    assert len(errors) == 1
    assert "Temporal inversion" in errors[0]


# ============================================================================
# 6. DEPENDENCY GRAPH & CYCLE PREVENTION
# ============================================================================
def test_dependency_graph_add_and_prerequisites():
    dg = DependencyGraph()
    # c2 depends on c1, c3 depends on c2
    dg.add_dependency("c2", "c1")
    dg.add_dependency("c3", "c2")

    assert dg.get_prerequisites("c2") == ["c1"]
    assert dg.get_dependents("c2") == ["c3"]
    assert dg.get_ancestors("c3") == ["c1", "c2"]
    assert dg.get_descendants("c1") == ["c2", "c3"]


def test_dependency_graph_topological_sort():
    dg = DependencyGraph()
    dg.add_dependency("c2", "c1")
    dg.add_dependency("c3", "c2")
    order = dg.topological_sort()
    assert order == ["c1", "c2", "c3"]


def test_dependency_graph_detects_direct_cycle():
    dg = DependencyGraph()
    dg.add_dependency("c2", "c1")
    with pytest.raises(DependencyCycleError, match="Dependency cycle detected"):
        dg.add_dependency("c1", "c2")


def test_dependency_graph_detects_indirect_cycle():
    dg = DependencyGraph()
    dg.add_dependency("c2", "c1")
    dg.add_dependency("c3", "c2")
    with pytest.raises(DependencyCycleError, match="Dependency cycle detected"):
        dg.add_dependency("c1", "c3")


def test_dependency_graph_prohibits_self_dependency():
    dg = DependencyGraph()
    with pytest.raises(DependencyCycleError, match="Self-dependency prohibited"):
        dg.add_dependency("c1", "c1")


# ============================================================================
# 7. EVIDENCE GRAPH & TRAVERSAL
# ============================================================================
def test_evidence_graph_supporting_and_contradicting_queries():
    eg = EvidenceGraph(case_id="CASE_001")
    ref1 = make_safe_ref("EV_001")
    ref2 = make_safe_ref("EV_002")
    eg.add_evidence_ref(ref1)
    eg.add_evidence_ref(ref2)

    rel_sup = CaseRelationship(
        relationship_id="r1",
        case_id="CASE_001",
        source_id="EV_001",
        source_type="EVIDENCE",
        target_id="clm_01",
        target_type="CLAIM",
        relationship_type=RelationshipType.SUPPORTS,
    )
    rel_con = CaseRelationship(
        relationship_id="r2",
        case_id="CASE_001",
        source_id="EV_002",
        source_type="EVIDENCE",
        target_id="clm_01",
        target_type="CLAIM",
        relationship_type=RelationshipType.CONTRADICTS,
    )
    eg.add_relationship(rel_sup)
    eg.add_relationship(rel_con)

    assert eg.get_supporting_evidence("clm_01") == ["EV_001"]
    assert eg.get_contradicting_evidence("clm_01") == ["EV_002"]


def test_evidence_graph_unsupported_claims_discovery():
    eg = EvidenceGraph(case_id="CASE_001")
    eg.register_claim("clm_supported")
    eg.register_claim("clm_unsupported")

    rel = CaseRelationship(
        relationship_id="r1",
        case_id="CASE_001",
        source_id="EV_001",
        source_type="EVIDENCE",
        target_id="clm_supported",
        target_type="CLAIM",
        relationship_type=RelationshipType.SUPPORTS,
    )
    eg.add_relationship(rel)

    assert eg.get_unsupported_claims() == ["clm_unsupported"]


# ============================================================================
# 8. TRAVERSAL & DOWNSTREAM IMPACT ANALYSIS
# ============================================================================
def test_traversal_claim_ancestors_and_descendants():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    prov = make_provenance("EV_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])
    twin.claims["c2"] = Claim(claim_id="c2", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])
    twin.claims["c3"] = Claim(claim_id="c3", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])

    # c2 depends on c1, c3 depends on c2
    twin.relationships["r1"] = CaseRelationship(relationship_id="r1", case_id="CASE_001", source_id="c2", source_type="CLAIM", target_id="c1", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)
    twin.relationships["r2"] = CaseRelationship(relationship_id="r2", case_id="CASE_001", source_id="c3", source_type="CLAIM", target_id="c2", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)

    assert get_claim_prerequisites(twin, "c2") == ["c1"]
    assert get_claim_ancestors(twin, "c3") == ["c1", "c2"]
    assert get_claim_descendants(twin, "c1") == ["c2", "c3"]


def test_traversal_downstream_impact_computation():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    prov = make_provenance("EV_001")
    twin.evidence_refs["EV_001"] = make_safe_ref("EV_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", supporting_evidence_ids=["EV_001"], provenance_refs=[prov])
    twin.claims["c2"] = Claim(claim_id="c2", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])
    twin.issues["iss_01"] = Issue(issue_id="iss_01", case_id="CASE_001", title="Issue 1", related_claim_ids=["c2"])

    # c2 depends on c1
    twin.relationships["r1"] = CaseRelationship(relationship_id="r1", case_id="CASE_001", source_id="c2", source_type="CLAIM", target_id="c1", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)

    report = compute_evidence_invalidation_impact(twin, "EV_001")
    assert report.target_id == "EV_001"
    assert report.directly_affected_claims == ("c1",)
    assert report.transitively_affected_claims == ("c2",)
    assert report.affected_issues == ("iss_01",)
    assert "impacts 1 direct claim(s)" in report.impact_summary


# ============================================================================
# 9. GRAPH INTEGRITY VALIDATOR (15 RULES)
# ============================================================================
def test_graph_validator_rule1_invalid_case_id():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.case_id = ""
    res = validate_case_graph(twin)
    assert not res.is_valid
    assert any("Rule 1" in e for e in res.errors)


def test_graph_validator_rule4_quarantined_evidence_rejected():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.evidence_refs["EV_001"] = make_safe_ref("EV_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", supporting_evidence_ids=["EV_001"])

    ev_item = make_evidence_item("EV_001", case_id="CASE_001", status=EvidenceStatus.QUARANTINED)
    res = validate_case_graph(twin, evidence_items={"EV_001": ev_item})
    assert not res.is_valid
    assert any("Rule 4" in e for e in res.errors)


def test_graph_validator_rule5_nonexistent_evidence_rejected():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", supporting_evidence_ids=["EV_GHOST"])
    res = validate_case_graph(twin)
    assert not res.is_valid
    assert any("Rule 5" in e for e in res.errors)


def test_graph_validator_rule6_nonexistent_relationship_node_rejected():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O")
    twin.relationships["r1"] = CaseRelationship(
        relationship_id="r1",
        case_id="CASE_001",
        source_id="c1",
        source_type="CLAIM",
        target_id="c_nonexistent",
        target_type="CLAIM",
        relationship_type=RelationshipType.DEPENDS_ON,
    )
    res = validate_case_graph(twin)
    assert not res.is_valid
    assert any("Rule 6" in e for e in res.errors)


def test_graph_validator_rule8_cross_case_contamination_rejected():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_002", subject_entity_id="A", predicate="P", object_value="O")
    res = validate_case_graph(twin)
    assert not res.is_valid
    assert any("Rule 8" in e for e in res.errors)


def test_graph_validator_rule11_self_dependency_rejected():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O")
    # Force bypass __post_init__ to test validator defense in depth
    object.__setattr__(
        twin,
        "relationships",
        {"r1": CaseRelationship.__new__(CaseRelationship)}
    )
    rel = twin.relationships["r1"]
    object.__setattr__(rel, "relationship_id", "r1")
    object.__setattr__(rel, "case_id", "CASE_001")
    object.__setattr__(rel, "source_id", "c1")
    object.__setattr__(rel, "source_type", "CLAIM")
    object.__setattr__(rel, "target_id", "c1")
    object.__setattr__(rel, "target_type", "CLAIM")
    object.__setattr__(rel, "relationship_type", RelationshipType.DEPENDS_ON)
    object.__setattr__(rel, "weight", 1.0)
    object.__setattr__(rel, "metadata", {})
    object.__setattr__(rel, "provenance_refs", ())
    object.__setattr__(rel, "created_at", datetime.now(UTC))

    res = validate_case_graph(twin)
    assert not res.is_valid
    assert any("Rule 11" in e for e in res.errors)


def test_graph_validator_rule12_dependency_cycle_rejected():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    prov = make_provenance("EV_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])
    twin.claims["c2"] = Claim(claim_id="c2", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])
    twin.relationships["r1"] = CaseRelationship(relationship_id="r1", case_id="CASE_001", source_id="c2", source_type="CLAIM", target_id="c1", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)
    twin.relationships["r2"] = CaseRelationship(relationship_id="r2", case_id="CASE_001", source_id="c1", source_type="CLAIM", target_id="c2", target_type="CLAIM", relationship_type=RelationshipType.DEPENDS_ON)

    res = validate_case_graph(twin)
    assert not res.is_valid
    assert any("Rule 12" in e for e in res.errors)


def test_graph_validator_rule15_missing_provenance_flagged_incomplete():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[])
    res = validate_case_graph(twin)
    assert res.provenance_status == "INCOMPLETE"
    assert any("Rule 15" in w for w in res.warnings)


# ============================================================================
# 10. PROVENANCE CHAIN VALIDATION
# ============================================================================
def test_provenance_validator_detects_hash_tampering():
    prov = ProvenanceRef(
        ref_id="pr1",
        source_id="affidavit.pdf",
        source_type="AFFIDAVIT",
        evidence_id="EV_001",
        content_hash="bad_hash",
    )
    clm = Claim(
        claim_id="c1",
        case_id="CASE_001",
        subject_entity_id="A",
        predicate="P",
        object_value="O",
        provenance_refs=[prov],
    )
    errs = validate_provenance_chain(clm, safe_evidence_hashes={"EV_001": "a" * 64})
    assert len(errs) > 0
    assert "invalid SHA-256 hash" in errs[0]


def test_provenance_validator_accepts_clean_chain():
    valid_hash = "a" * 64
    prov = ProvenanceRef(
        ref_id="pr1",
        source_id="affidavit.pdf",
        source_type="AFFIDAVIT",
        evidence_id="EV_001",
        content_hash=valid_hash,
    )
    clm = Claim(
        claim_id="c1",
        case_id="CASE_001",
        subject_entity_id="A",
        predicate="P",
        object_value="O",
        provenance_refs=[prov],
    )
    errs = validate_provenance_chain(clm, safe_evidence_hashes={"EV_001": valid_hash})
    assert len(errs) == 0


# ============================================================================
# 11. CROSS-CASE SECURITY ISOLATION
# ============================================================================
def test_cross_case_evidence_isolation_case_a_vs_case_b():
    builder_a = CaseTwinBuilder(case_id="CASE_ALPHA")
    ref_b = make_safe_ref("EV_B01", case_id="CASE_BETA")
    item_b = make_evidence_item("EV_B01", case_id="CASE_BETA", status=EvidenceStatus.REGISTERED)

    with pytest.raises(ValueError, match="Cross-case contamination"):
        CaseTwinEvidenceAdapter.attach_safe_evidence(builder_a, ref_b, item_b)


# ============================================================================
# 12. TARKA-VYUH INTEGRATION & UNWIND GOVERNANCE
# ============================================================================
def test_case_twin_tarka_adapter_extracts_sanitized_context():
    twin = CaseDigitalTwin(twin_id="twin_01", case_id="CASE_001")
    prov = make_provenance("EV_001")
    twin.evidence_refs["EV_001"] = make_safe_ref("EV_001")
    twin.claims["c1"] = Claim(claim_id="c1", case_id="CASE_001", subject_entity_id="A", predicate="P", object_value="O", provenance_refs=[prov])

    ctx = CaseTwinTarkaAdapter.extract_reasoning_context(twin)
    assert ctx["case_id"] == "CASE_001"
    assert len(ctx["claims"]) == 1
    assert "evidence_summaries" in ctx
    # Raw file bytes are structurally absent from the context
    assert "raw_bytes" not in ctx


def test_case_twin_tarka_adapter_blocks_unimplemented_reasoning():
    # CAUSAL_ANALYSIS is planned for Phase 4/5 and strictly NOT_IMPLEMENTED
    with pytest.raises(ReasoningEngineNotImplementedError, match="NOT_IMPLEMENTED"):
        CaseTwinTarkaAdapter.verify_capability_available(ReasoningType.CAUSAL_ANALYSIS)


def test_case_twin_evidence_adapter_blocks_quarantined_items():
    builder = CaseTwinBuilder(case_id="CASE_001")
    ref = make_safe_ref("EV_001")
    item_quarantined = make_evidence_item("EV_001", case_id="CASE_001", status=EvidenceStatus.QUARANTINED)
    with pytest.raises(QuarantineViolationError, match="Quarantine violation"):
        CaseTwinEvidenceAdapter.attach_safe_evidence(builder, ref, item_quarantined)


# ============================================================================
# 13. REST API LIFECYCLE TESTS (/api/nyaya/cases/{id}/twin/...)
# ============================================================================
def test_api_build_twin_lifecycle(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_01", title="Property Boundary Matter"))

    payload = {
        "twin_id": "twin_p01",
        "entities": [
            {"canonical_label": "Suresh Raina", "entity_type": "PERSON", "entity_id": "ent_p1"},
            {"canonical_label": "Green Acres Plot", "entity_type": "ASSET", "entity_id": "ent_a1"},
        ],
        "claims": [
            {
                "claim_id": "clm_01",
                "subject_entity_id": "ent_p1",
                "predicate": "PURCHASED",
                "object_value": "ent_a1",
            }
        ],
        "issues": [
            {
                "issue_id": "iss_01",
                "title": "Title Ownership Dispute",
            }
        ],
        "events": [
            {
                "event_id": "evt_01",
                "title": "Sale Deed Execution",
                "event_time": "2024-02-14",
                "time_precision": "DATE",
            }
        ],
        "relationships": [
            {
                "source_id": "clm_01",
                "source_type": "CLAIM",
                "target_id": "iss_01",
                "target_type": "ISSUE",
                "relationship_type": "SUBMITTED_UNDER",
            }
        ],
    }
    resp = client.post("/api/nyaya/cases/C_TWIN_01/twin/build", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["twin_id"] == "twin_p01"
    assert data["entities_count"] == 2
    assert data["claims_count"] == 1
    assert data["issues_count"] == 1
    assert data["events_count"] == 1
    assert data["relationships_count"] == 1


def test_api_twin_entities_claims_issues_endpoints(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_02", title="Contract Matter"))

    payload = {
        "entities": [{"canonical_label": "Party One", "entity_type": "PERSON", "entity_id": "p1"}],
        "claims": [{"claim_id": "c1", "subject_entity_id": "p1", "predicate": "DELIVERED", "object_value": "GOODS"}],
        "issues": [{"issue_id": "i1", "title": "Goods Quality"}],
    }
    client.post("/api/nyaya/cases/C_TWIN_02/twin/build", json=payload, headers=headers)

    # GET entities
    r_ent = client.get("/api/nyaya/cases/C_TWIN_02/twin/entities", headers=headers)
    assert r_ent.status_code == 200
    assert len(r_ent.json()["entities"]) == 1

    # GET claims
    r_clm = client.get("/api/nyaya/cases/C_TWIN_02/twin/claims", headers=headers)
    assert r_clm.status_code == 200
    assert len(r_clm.json()["claims"]) == 1

    # GET issues
    r_iss = client.get("/api/nyaya/cases/C_TWIN_02/twin/issues", headers=headers)
    assert r_iss.status_code == 200
    assert len(r_iss.json()["issues"]) == 1


def test_api_twin_timeline_and_temporal_conflicts(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_03", title="Temporal Matter"))

    payload = {
        "events": [
            {"event_id": "ev1", "title": "Inspection Visit", "event_time": "2024-03-01", "time_precision": "DATE"},
            {"event_id": "ev2", "title": "Inspection Visit", "event_time": "2024-03-20", "time_precision": "DATE"},
        ]
    }
    client.post("/api/nyaya/cases/C_TWIN_03/twin/build", json=payload, headers=headers)

    resp = client.get("/api/nyaya/cases/C_TWIN_03/twin/timeline", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["timeline_events"]) == 2
    assert len(data["temporal_conflicts"]) == 1
    assert data["temporal_conflicts"][0]["conflict_type"] == "TEMPORAL_CONFLICT"


def test_api_twin_graph_and_snapshot_endpoints(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_04", title="Graph Matter"))

    payload = {
        "entities": [{"canonical_label": "Company X", "entity_type": "ORGANIZATION", "entity_id": "ent_cx"}],
        "claims": [{"claim_id": "c1", "subject_entity_id": "ent_cx", "predicate": "OWED", "object_value": "TAX"}],
    }
    client.post("/api/nyaya/cases/C_TWIN_04/twin/build", json=payload, headers=headers)

    r_graph = client.get("/api/nyaya/cases/C_TWIN_04/twin/graph", headers=headers)
    assert r_graph.status_code == 200
    assert "nodes" in r_graph.json()

    r_snap = client.get("/api/nyaya/cases/C_TWIN_04/twin/snapshot", headers=headers)
    assert r_snap.status_code == 200
    snap = r_snap.json()
    assert "integrity_hash" in snap
    assert snap["case_id"] == "C_TWIN_04"


def test_api_twin_evidence_dependencies_impact_endpoint(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_05", title="Dependency Matter"))

    payload = {
        "claims": [
            {"claim_id": "c1", "subject_entity_id": "P", "predicate": "IS", "object_value": "OWNER", "source_evidence_ids": ["EV_DEED"]},
            {"claim_id": "c2", "subject_entity_id": "P", "predicate": "CAN", "object_value": "SELL"},
        ],
        "relationships": [
            {"source_id": "c2", "source_type": "CLAIM", "target_id": "c1", "target_type": "CLAIM", "relationship_type": "DEPENDS_ON"}
        ]
    }
    client.post("/api/nyaya/cases/C_TWIN_05/twin/build", json=payload, headers=headers)

    resp = client.get("/api/nyaya/cases/C_TWIN_05/twin/evidence/EV_DEED/dependencies", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_id"] == "EV_DEED"
    assert "c1" in data["directly_affected_claims"]
    assert "c2" in data["transitively_affected_claims"]


def test_api_twin_claims_support_and_dependencies_endpoints(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_06", title="Support Query Matter"))

    payload = {
        "claims": [
            {"claim_id": "c1", "subject_entity_id": "P", "predicate": "PAID", "object_value": "RENT", "supporting_evidence_ids": ["EV_REC1"]},
            {"claim_id": "c2", "subject_entity_id": "P", "predicate": "HAS", "object_value": "TENANCY"},
        ],
        "relationships": [
            {"source_id": "c2", "source_type": "CLAIM", "target_id": "c1", "target_type": "CLAIM", "relationship_type": "DEPENDS_ON"}
        ]
    }
    client.post("/api/nyaya/cases/C_TWIN_06/twin/build", json=payload, headers=headers)

    # Support query
    r_sup = client.get("/api/nyaya/cases/C_TWIN_06/twin/claims/c1/support", headers=headers)
    assert r_sup.status_code == 200
    assert r_sup.json()["supporting_evidence_ids"] == ["EV_REC1"]

    # Dependencies query
    r_dep = client.get("/api/nyaya/cases/C_TWIN_06/twin/claims/c2/dependencies", headers=headers)
    assert r_dep.status_code == 200
    assert r_dep.json()["direct_prerequisites"] == ["c1"]


def test_api_twin_validation_endpoint(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}

    registry = get_evidence_registry()
    registry.register_case(Case(case_id="C_TWIN_07", title="Validation Test Matter"))

    payload = {
        "claims": [
            {"claim_id": "c1", "subject_entity_id": "A", "predicate": "P", "object_value": "O"}
        ]
    }
    client.post("/api/nyaya/cases/C_TWIN_07/twin/build", json=payload, headers=headers)

    resp = client.post("/api/nyaya/cases/C_TWIN_07/twin/validate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["rules_checked"] == 15


def test_api_twin_case_not_found_returns_404(monkeypatch):
    monkeypatch.setenv("UNWIND_OPERATOR_TOKENS", "svc-tok:service::ci-analyst")
    client = TestClient(app)
    headers = {"Authorization": "Bearer svc-tok"}
    resp = client.get("/api/nyaya/cases/NON_EXISTENT_CASE_999/twin", headers=headers)
    assert resp.status_code == 404
