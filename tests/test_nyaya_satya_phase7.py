"""Comprehensive test suite for NYAYA-SATYA Phase 7 Master Build.

Dossier 2.0 (Versioning, Structural Diff, Human Checklist) +
Proven Impact Subsystem (Honest Metrics, Comparative Trials, Synthetic Benchmarks, Safety Validators, API).

Categories:
A. Dossier Version Record contracts
B. Dossier Version Store
C. Human Review Checklist contracts & lifecycle
D. Dossier Diff & Section Diffing Engine
E. DossierBuilder 2.0 with versioning & checklist generation
F. ExportFormatter Markdown formatting (checklist & diff)
G. Deterministic semantic fingerprinting (excluding timestamps)
H. Impact Event contracts & immutability
I. Impact Metric contracts & epistemic classifications
J. Impact Measurement & cryptographic fingerprinting
K. Event Collector & thread-safety
L. Session & Workflow Trackers
M. Metric Calculators (time, contradictions, gaps, provenance, repair, reattack, review)
N. Baseline, Treatment, and Comparative Trial Execution
O. Synthetic Benchmark Suite (12 canonical scenarios)
P. Impact Report Compiler (14 canonical sections & Markdown)
Q. Executive KPI Summaries
R. Cryptographic Evidence Exporter & verification
S. Metric, Provenance & Safety Validators (Zero fake impact, Privacy, Non-adjudication)
T. Phase 7 FastAPI Endpoints Integration
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from nyaya_dossier.dossier_builder import DossierBuilder
from nyaya_dossier.dossier_diff import DossierComparator, DossierDiff, SectionDiff
from nyaya_dossier.dossier_model import DossierEntry, DossierItemCategory, JudicialReviewDossier
from nyaya_dossier.dossier_version import DossierVersionRecord, DossierVersionStore
from nyaya_dossier.export_formatter import DossierFormatter
from nyaya_dossier.human_checklist import (
    HumanReviewChecklist,
    ReviewItem,
    ReviewSeverity,
    ReviewStatus,
)
from nyaya_evidence.sanitization.sanitizer import RiskLevel
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_impact.collection.event_collector import EventCollector, ImpactEventCollector
from nyaya_impact.collection.session_tracker import ActiveSession, SessionTracker
from nyaya_impact.collection.workflow_tracker import WorkflowStats, WorkflowTracker
from nyaya_impact.contracts.impact_baseline import (
    BaselineMeasurement,
    ComparativeTrialResult,
    TreatmentMeasurement,
)
from nyaya_impact.contracts.impact_event import ImpactEvent, ImpactEventType
from nyaya_impact.contracts.impact_measurement import ImpactMeasurement
from nyaya_impact.contracts.impact_metric import (
    ImpactMetric,
    MetricCategory,
    MetricClassification,
)
from nyaya_impact.contracts.impact_report import ProvenImpactReport
from nyaya_impact.experiments.baseline_runner import BaselineRunner
from nyaya_impact.experiments.benchmark_suite import (
    BenchmarkScenarioResult,
    SyntheticBenchmarkSuite,
)
from nyaya_impact.experiments.experiment_runner import ExperimentRunner
from nyaya_impact.experiments.treatment_runner import TreatmentRunner
from nyaya_impact.metrics.contradiction_metrics import ContradictionMetrics
from nyaya_impact.metrics.evidence_gap_metrics import EvidenceGapMetrics
from nyaya_impact.metrics.processing_time import ProcessingTimeMetrics
from nyaya_impact.metrics.provenance_metrics import ProvenanceMetrics
from nyaya_impact.metrics.reattack_metrics import ReAttackMetrics
from nyaya_impact.metrics.repair_metrics import RepairMetrics
from nyaya_impact.metrics.review_metrics import ReviewMetrics
from nyaya_impact.reporting.evidence_exporter import EvidenceExporter
from nyaya_impact.reporting.impact_report import ImpactReportCompiler
from nyaya_impact.reporting.impact_summary import ExecutiveKPIs, ImpactSummaryGenerator
from nyaya_impact.validation.impact_safety_validator import (
    ImpactSafetyResult,
    ImpactSafetyValidator,
)
from nyaya_impact.validation.metric_validator import (
    MetricValidationResult,
    MetricValidator,
)
from nyaya_impact.validation.provenance_validator import (
    ProvenanceValidationResult,
    ProvenanceValidator,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import Claim, ClaimStatus, ClaimType
from nyaya_twin.contracts.events import TemporalStatus, TimePrecision, TimelineEvent
from services.api.main import app
from services.api.nyaya import _TWINS, reset_nyaya_api_state
from tarka_vyuh.contracts.provenance import ProvenanceRef


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
HUMAN_AUTH_HEADERS = {"Authorization": "Bearer human-tok"}
client = TestClient(app)


def make_provenance(ev_id: str, case_id: str = "CASE_P7") -> ProvenanceRef:
    return ProvenanceRef(
        ref_id=f"prov_{ev_id}",
        source_id=f"{ev_id}.pdf",
        source_type="DOCUMENT",
        evidence_id=ev_id,
        content_hash="a" * 64,
        extraction_metadata={"page": 1},
    )


def make_safe_ref(ev_id: str = "EV_001", case_id: str = "CASE_P7", text: str = "Contract signed March 2024") -> SafeEvidenceRef:
    prov = make_provenance(ev_id, case_id)
    return SafeEvidenceRef(
        evidence_id=ev_id,
        case_id=case_id,
        sanitized_text=text,
        content_hash="a" * 64,
        sanitized_hash="a" * 64,
        provenance_refs=(prov,),
        sanitization_status="CLEAN",
        risk_level=RiskLevel.CLEAN,
        extraction_metadata={"page": 1},
    )


def make_sample_twin(case_id: str = "CASE_P7_01") -> CaseDigitalTwin:
    twin = CaseDigitalTwin(case_id=case_id, twin_id=f"TWIN_{case_id}")
    ref = make_safe_ref("EV_01", case_id, "Sample agreement text")
    twin.evidence_refs["EV_01"] = ref

    claim1 = Claim(
        claim_id="CLM_01",
        case_id=case_id,
        claim_type=ClaimType.FACTUAL,
        subject_entity_id="ENT_A",
        predicate="SIGNED",
        object_value="AGREEMENT",
        status=ClaimStatus.SUPPORTED,
        supporting_evidence_ids=["EV_01"],
        provenance_refs=list(ref.provenance_refs),
    )
    claim2 = Claim(
        claim_id="CLM_02",
        case_id=case_id,
        claim_type=ClaimType.FACTUAL,
        subject_entity_id="ENT_B",
        predicate="PAID",
        object_value="CONSIDERATION",
        status=ClaimStatus.UNSUPPORTED,
        supporting_evidence_ids=[],
    )
    twin.claims["CLM_01"] = claim1
    twin.claims["CLM_02"] = claim2
    return twin


# ===========================================================================
# CATEGORY A: Dossier Version Record contracts
# ===========================================================================

def test_dossier_version_record_creation():
    rec = DossierVersionRecord(
        version_id="VER_001",
        case_id="CASE_01",
        version_number=1,
        current_fingerprint="fp_current_abc",
        previous_fingerprint=None,
        change_summary="Initial dossier baseline",
        actor_id="ci-jurist",
    )
    assert rec.version_id == "VER_001"
    assert rec.version_number == 1
    assert rec.previous_fingerprint is None
    d = rec.to_dict()
    assert d["current_fingerprint"] == "fp_current_abc"
    assert d["actor_id"] == "ci-jurist"

    rec2 = DossierVersionRecord.from_dict(d)
    assert rec2.version_id == rec.version_id
    assert rec2.version_number == rec.version_number


# ===========================================================================
# CATEGORY B: Dossier Version Store
# ===========================================================================

def test_dossier_version_store_sequential():
    store = DossierVersionStore()
    v1 = store.record_version("CASE_01", "fp_1", "Initial baseline", "jurist_1")
    assert v1.version_number == 1
    assert v1.previous_fingerprint is None

    v2 = store.record_version("CASE_01", "fp_2", "Added evidence ref", "jurist_1")
    assert v2.version_number == 2
    assert v2.previous_fingerprint == "fp_1"

    history = store.get_history("CASE_01")
    assert len(history) == 2
    assert store.get_latest_version("CASE_01") == v2

    store.reset_for_test()
    assert len(store.get_history("CASE_01")) == 0


# ===========================================================================
# CATEGORY C: Human Review Checklist models & lifecycle
# ===========================================================================

def test_human_review_checklist_lifecycle():
    item1 = ReviewItem(
        review_id="REV_01",
        severity=ReviewSeverity.CRITICAL,
        source="unresolved_contradiction",
        explanation="Conflicting execution dates between Agreement and Affidavit",
        recommended_action="Summon original records for cross-verification",
    )
    item2 = ReviewItem(
        review_id="REV_02",
        severity=ReviewSeverity.HIGH,
        source="unsupported_claim",
        explanation="Claim CLM_02 lacks supporting evidence",
        recommended_action="Request document proof from claimant",
    )
    checklist = HumanReviewChecklist(
        case_id="CASE_01",
        dossier_id="DOS_01",
        items=[item1, item2],
    )

    assert checklist.total_count == 2
    assert checklist.pending_count == 2
    assert checklist.critical_count == 1

    item1.resolve(notes="Reconciled via original ledger", actor="ci-jurist")
    assert checklist.pending_count == 1
    assert checklist.resolved_count == 1
    assert checklist.critical_count == 0

    d = checklist.to_dict()
    assert d["pending_count"] == 1
    assert d["resolved_count"] == 1


# ===========================================================================
# CATEGORY D: Dossier Diff & Section Diffing Engine
# ===========================================================================

def test_dossier_diff_engine():
    d1 = JudicialReviewDossier(case_id="CASE_01", dossier_id="DOS_01", version=1)
    d1.sec04_claim_graph.append(
        DossierEntry(
            entry_id="C_01",
            section_index=4,
            section_name="sec04_claim_graph",
            category=DossierItemCategory.FACT,
            title="Claim 1",
            description="Claim 1 description",
        )
    )

    d2 = JudicialReviewDossier(case_id="CASE_01", dossier_id="DOS_02", version=2)
    # C_01 is modified
    d2.sec04_claim_graph.append(
        DossierEntry(
            entry_id="C_01",
            section_index=4,
            section_name="sec04_claim_graph",
            category=DossierItemCategory.FACT,
            title="Claim 1 (Amended)",
            description="Claim 1 description amended",
        )
    )
    # New claim C_02 added
    d2.sec04_claim_graph.append(
        DossierEntry(
            entry_id="C_02",
            section_index=4,
            section_name="sec04_claim_graph",
            category=DossierItemCategory.FACT,
            title="Claim 2",
            description="Claim 2 description",
        )
    )

    diff = DossierComparator.compare(d1, d2)
    assert diff.case_id == "CASE_01"
    assert diff.version_a == 1
    assert diff.version_b == 2
    assert diff.total_added == 1
    assert diff.total_changed == 1
    assert "sec04_claim_graph" in diff.section_diffs
    assert "C_02" in diff.section_diffs["sec04_claim_graph"].added_ids
    assert "C_01" in diff.section_diffs["sec04_claim_graph"].changed_ids


# ===========================================================================
# CATEGORY E: DossierBuilder 2.0 with versioning & checklist generation
# ===========================================================================

def test_dossier_builder_v2_with_checklist():
    builder = DossierBuilder()
    twin = make_sample_twin("CASE_BUILD_01")
    dossier = builder.build_dossier(twin, version=2, previous_fingerprint="prev_fp_123")

    assert dossier.version == 2
    assert dossier.previous_fingerprint == "prev_fp_123"
    assert dossier.fingerprint != ""

    checklist = builder.build_human_checklist(dossier, twin)
    assert isinstance(checklist, HumanReviewChecklist)
    assert checklist.case_id == "CASE_BUILD_01"
    # Claim CLM_02 was unsupported -> should generate high severity review item
    unsupported_items = [it for it in checklist.items if "CLM_02" in it.review_id]
    assert len(unsupported_items) == 1
    assert unsupported_items[0].severity == ReviewSeverity.HIGH


# ===========================================================================
# CATEGORY F: ExportFormatter Markdown formatting (checklist & diff)
# ===========================================================================

def test_export_formatter_checklist_and_diff_markdown():
    item = ReviewItem(
        review_id="REV_MOCK",
        severity=ReviewSeverity.CRITICAL,
        source="unresolved_contradiction",
        explanation="Test explanation",
        recommended_action="Take action",
    )
    chk = HumanReviewChecklist(case_id="CASE_TEST", dossier_id="DOS_TEST", items=[item])
    md_chk = DossierFormatter.format_checklist_markdown(chk)
    assert "HUMAN REVIEW CHECKLIST" in md_chk
    assert "REV_MOCK" in md_chk
    assert "CRITICAL" in md_chk

    diff = DossierDiff(
        case_id="CASE_TEST",
        dossier_a_id="D1",
        dossier_b_id="D2",
        version_a=1,
        version_b=2,
        fingerprint_a="fp_a",
        fingerprint_b="fp_b",
        total_added=2,
        total_removed=0,
        total_changed=1,
        total_unchanged=5,
        summary="Version 2 adds 2 items and changes 1",
    )
    md_diff = DossierFormatter.format_diff_markdown(diff)
    assert "DOSSIER STRUCTURAL DIFF" in md_diff
    assert "v1" in md_diff and "v2" in md_diff
    assert "Section" in md_diff


# ===========================================================================
# CATEGORY G: Deterministic semantic fingerprinting
# ===========================================================================

def test_deterministic_semantic_fingerprinting_independent_of_time():
    d1 = JudicialReviewDossier(case_id="CASE_DETERMINISTIC", dossier_id="DOS_01", version=1)
    d1.sec03_evidence_provenance.append(
        DossierEntry(
            entry_id="P_01",
            section_index=3,
            section_name="sec03_evidence_provenance",
            category=DossierItemCategory.FACT,
            title="Party 1",
            description="Party 1 description",
        )
    )

    d2 = JudicialReviewDossier(case_id="CASE_DETERMINISTIC", dossier_id="DOS_02", version=1)
    d2.sec03_evidence_provenance.append(
        DossierEntry(
            entry_id="P_01",
            section_index=3,
            section_name="sec03_evidence_provenance",
            category=DossierItemCategory.FACT,
            title="Party 1",
            description="Party 1 description",
        )
    )

    # Even though dossier_id and created_at timestamps differ, semantic fingerprint MUST match
    assert d1.fingerprint == d2.fingerprint


# ===========================================================================
# CATEGORY H: Impact Event contracts & immutability
# ===========================================================================

def test_impact_event_contracts():
    evt = ImpactEvent(
        event_id="EVT_001",
        case_id="CASE_IMPACT",
        event_type=ImpactEventType.CONTRADICTION_DETECTED,
        phase="PHASE_4_GAUNTLET",
        metadata={"candidate_id": "c_1", "confidence": 0.95},
    )
    assert evt.event_id == "EVT_001"
    assert evt.event_type == ImpactEventType.CONTRADICTION_DETECTED
    d = evt.to_dict()
    assert d["event_type"] == "CONTRADICTION_DETECTED"
    assert d["metadata"]["confidence"] == 0.95


# ===========================================================================
# CATEGORY I: Impact Metric contracts & epistemic classifications
# ===========================================================================

def test_impact_metric_classifications():
    metric = ImpactMetric(
        metric_id="M_CONTRA_01",
        name="Contradictions Detected",
        category=MetricCategory.EVIDENCE_ANALYSIS,
        classification=MetricClassification.OBSERVED,
        value=3.0,
        unit="count",
        description="Number of detected factual conflicts",
    )
    assert metric.classification == MetricClassification.OBSERVED
    assert metric.category == MetricCategory.EVIDENCE_ANALYSIS
    d = metric.to_dict()
    assert d["classification"] == "OBSERVED"
    assert d["value"] == 3.0


# ===========================================================================
# CATEGORY J: Impact Measurement & cryptographic fingerprinting
# ===========================================================================

def test_impact_measurement_cryptographic_fingerprint():
    metric = ImpactMetric(
        metric_id="M_TIME_01",
        name="Processing Latency",
        category=MetricCategory.WORKFLOW,
        classification=MetricClassification.OBSERVED,
        value=1.45,
        unit="seconds",
        description="Automated pipeline latency",
    )
    measurement = ImpactMeasurement(
        measurement_id="MEAS_01",
        case_or_dataset_id="CASE_01",
        metric=metric,
        experiment_id="EXP_01",
    )
    fp1 = measurement.fingerprint
    assert len(fp1) == 64

    # Different metric value produces different fingerprint
    metric2 = ImpactMetric(
        metric_id="M_TIME_01",
        name="Processing Latency",
        category=MetricCategory.WORKFLOW,
        classification=MetricClassification.OBSERVED,
        value=2.50,
        unit="seconds",
        description="Automated pipeline latency",
    )
    measurement2 = ImpactMeasurement(
        measurement_id="MEAS_01",
        case_or_dataset_id="CASE_01",
        metric=metric2,
        experiment_id="EXP_01",
    )
    fp2 = measurement2.fingerprint
    assert fp1 != fp2


# ===========================================================================
# CATEGORY K: Event Collector & thread-safety
# ===========================================================================

def test_event_collector():
    collector = EventCollector()
    collector.record_event(
        ImpactEvent(
            event_id="E1",
            case_id="CASE_A",
            event_type=ImpactEventType.CONTRADICTION_DETECTED,
            phase="PHASE_4",
        )
    )
    collector.record_event(
        ImpactEvent(
            event_id="E2",
            case_id="CASE_A",
            event_type=ImpactEventType.MISSING_EVIDENCE_FOUND,
            phase="PHASE_4",
        )
    )
    collector.record_event(
        ImpactEvent(
            event_id="E3",
            case_id="CASE_B",
            event_type=ImpactEventType.CONTRADICTION_DETECTED,
            phase="PHASE_4",
        )
    )

    case_a_events = collector.get_events_for_case("CASE_A")
    assert len(case_a_events) == 2
    assert collector.count_by_type("CASE_A", ImpactEventType.CONTRADICTION_DETECTED) == 1
    assert collector.count_by_type("CASE_A", ImpactEventType.REPAIR_PROPOSED) == 0

    all_evts = collector.all_events()
    assert len(all_evts) == 3


# ===========================================================================
# CATEGORY L: Session & Workflow Trackers
# ===========================================================================

def test_session_and_workflow_trackers():
    s_tracker = SessionTracker()
    session_id = s_tracker.start_phase("CASE_SESS", "PHASE_4_GAUNTLET")
    assert session_id.startswith("SESS_")
    assert s_tracker.active_sessions_count == 1

    event = s_tracker.end_phase(session_id, ImpactEventType.ADVERSARIAL_ATTACK_RUN)
    assert event.event_type == ImpactEventType.ADVERSARIAL_ATTACK_RUN
    assert event.duration_ms >= 0.0

    w_tracker = WorkflowTracker()
    w_tracker.record_automated_check("CASE_WF", count=5)
    w_tracker.record_manual_checkpoint("CASE_WF", count=2)
    stats = w_tracker.get_or_create("CASE_WF")
    assert stats.automated_checks_run == 5
    assert stats.manual_checkpoints_required == 2


# ===========================================================================
# CATEGORY M: Metric Calculators
# ===========================================================================

def test_metric_calculators():
    twin = make_sample_twin("CASE_M")

    contra_calc = ContradictionMetrics()
    contra_m = contra_calc.compute_metrics(twin)
    assert len(contra_m) >= 1

    gap_calc = EvidenceGapMetrics()
    gap_m = gap_calc.compute_metrics(twin)
    assert len(gap_m) >= 1
    assert any("UNSUP" in m.metric_id for m in gap_m)

    prov_calc = ProvenanceMetrics()
    prov_m = prov_calc.compute_metrics(twin)
    assert len(prov_m) >= 1
    assert any("PROV" in m.metric_id for m in prov_m)

    item = ReviewItem(
        review_id="REV_1",
        severity=ReviewSeverity.CRITICAL,
        source="contra",
        explanation="Conflict",
        recommended_action="Resolve",
    )
    chk = HumanReviewChecklist(case_id="CASE_M", dossier_id="DOS_M", items=[item])
    rev_calc = ReviewMetrics()
    rev_m = rev_calc.compute_metrics(chk)
    assert len(rev_m) >= 1


# ===========================================================================
# CATEGORY N: Baseline, Treatment, and Comparative Trial Execution
# ===========================================================================

def test_comparative_trial_runner():
    twin = make_sample_twin("CASE_TRIAL_01")
    runner = ExperimentRunner()
    result = runner.run_comparative_trial(twin)

    assert isinstance(result, ComparativeTrialResult)
    assert result.case_id == "CASE_TRIAL_01"
    assert result.baseline.manual_review_time_estimated_minutes > 0.0
    assert result.treatment.automated_checks_run >= 2
    assert result.treatment.provenance_coverage_ratio > 0.0


# ===========================================================================
# CATEGORY O: Synthetic Benchmark Suite (12 canonical scenarios)
# ===========================================================================

def test_synthetic_benchmark_suite_all_pass():
    suite = SyntheticBenchmarkSuite()
    results = suite.run_all_benchmarks()

    assert len(results) == 12
    for r in results:
        assert isinstance(r, BenchmarkScenarioResult)
        assert r.passed, f"Benchmark scenario failed: {r.scenario_id} - {r.name}"
        assert r.label == "SYNTHETIC BENCHMARK SUITE"
        assert r.limitations != ""

    scenario_ids = [r.scenario_id for r in results]
    expected_ids = [
        "BM_01_CONTRADICTION",
        "BM_02_TIMELINE",
        "BM_03_MISSING_EVIDENCE",
        "BM_04_UNSUPPORTED_ASSERTION",
        "BM_05_PROVENANCE_BREAK",
        "BM_06_CAUSAL_DEPENDENCY",
        "BM_07_IRRELEVANT_PERTURBATION",
        "BM_08_MATERIAL_REMOVAL",
        "BM_09_REPAIR_REGRESSION",
        "BM_10_PROMPT_INJECTION",
        "BM_11_AUTHORITY_VERIFICATION",
        "BM_12_CROSS_CASE_ISOLATION",
    ]
    assert scenario_ids == expected_ids


# ===========================================================================
# CATEGORY P: Impact Report Compiler (14 canonical sections & Markdown)
# ===========================================================================

def test_impact_report_compiler_14_sections():
    compiler = ImpactReportCompiler()
    benchmarks = SyntheticBenchmarkSuite().run_all_benchmarks()
    metrics = [
        ImpactMetric(
            metric_id="M_CONTRA_TEST",
            name="Contradiction Count",
            category=MetricCategory.EVIDENCE_ANALYSIS,
            classification=MetricClassification.OBSERVED,
            value=4.0,
            unit="count",
            description="Detected factual contradictions",
        )
    ]
    report = compiler.compile(
        case_or_dataset_id="CASE_REPORT_01",
        metrics=metrics,
        benchmarks=benchmarks,
    )

    assert isinstance(report, ProvenImpactReport)
    d = report.to_dict()
    for sec_num in range(1, 15):
        key = f"sec{sec_num:02d}"
        matching_keys = [k for k in d if k.startswith(key)]
        assert len(matching_keys) == 1, f"Missing report section {key}"

    # Verify Markdown generation
    md = compiler.generate_markdown(report)
    assert "# NYAYA-SATYA Proven Impact Report" in md
    assert "Section 1: Scope & Identity" in md
    assert "Section 6: Proven Impact Metrics" in md
    assert "Section 14: Open Issues & Continuous Monitoring" in md


# ===========================================================================
# CATEGORY Q: Executive KPI Summaries
# ===========================================================================

def test_executive_kpi_summary():
    compiler = ImpactReportCompiler()
    report = compiler.compile(case_or_dataset_id="CASE_EXEC_01")
    generator = ImpactSummaryGenerator()
    kpis = generator.summarize(report)

    assert isinstance(kpis, ExecutiveKPIs)
    assert kpis.case_or_dataset_id == "CASE_EXEC_01"
    assert kpis.epistemic_classification == MetricClassification.SYNTHETIC.value
    d = kpis.to_dict()
    assert "automated_contradiction_discovery_count" in d
    assert "provenance_coverage_ratio" in d


# ===========================================================================
# CATEGORY R: Cryptographic Evidence Exporter & verification
# ===========================================================================

def test_evidence_exporter_and_verification():
    compiler = ImpactReportCompiler()
    report = compiler.compile(case_or_dataset_id="CASE_EXPORT_01")
    exporter = EvidenceExporter(compiler)

    json_export = exporter.export_json(report)
    assert exporter.verify_json_export(json_export) is True

    # Tampering check
    parsed = json.loads(json_export)
    parsed["payload"]["case_or_dataset_id"] = "TAMPERED_CASE"
    tampered_json = json.dumps(parsed)
    assert exporter.verify_json_export(tampered_json) is False

    # Markdown export check
    md_export = exporter.export_markdown(report)
    assert "Audit Checksum" in md_export


# ===========================================================================
# CATEGORY S: Metric, Provenance & Safety Validators
# ===========================================================================

def test_metric_validator():
    validator = MetricValidator()

    valid_m = ImpactMetric(
        metric_id="M_VALID",
        name="Valid Ratio",
        category=MetricCategory.EVIDENCE_PROCESSING,
        classification=MetricClassification.OBSERVED,
        value=0.85,
        unit="ratio",
        description="A sound ratio metric",
        source_provenance_hash="a" * 64,
    )
    res = validator.validate_metric(valid_m)
    assert res.is_valid is True

    # Ratio out of range
    invalid_ratio = ImpactMetric(
        metric_id="M_INVALID_RATIO",
        name="Bad Ratio",
        category=MetricCategory.EVIDENCE_PROCESSING,
        classification=MetricClassification.OBSERVED,
        value=1.5,
        unit="ratio",
        description="Out of range ratio",
        source_provenance_hash="a" * 64,
    )
    res_bad = validator.validate_metric(invalid_ratio)
    assert res_bad.is_valid is False
    assert any("must be between 0.0 and 1.0" in v for v in res_bad.violations)

    # Disallowed marketing claim
    marketing_m = ImpactMetric(
        metric_id="M_WIN_RATE",
        name="Win Rate Predictor",
        category=MetricCategory.EVIDENCE_ANALYSIS,
        classification=MetricClassification.OBSERVED,
        value=0.99,
        unit="ratio",
        description="Win rate prediction metric",
        source_provenance_hash="a" * 64,
    )
    res_mkt = validator.validate_metric(marketing_m)
    assert res_mkt.is_valid is False
    assert any("Forbidden predictive/marketing claim" in v for v in res_mkt.violations)


def test_provenance_validator():
    validator = ProvenanceValidator()
    metric = ImpactMetric(
        metric_id="M_PROV_TEST",
        name="Test Metric",
        category=MetricCategory.EVIDENCE_PROCESSING,
        classification=MetricClassification.OBSERVED,
        value=1.0,
        unit="count",
        description="Test",
    )
    meas = ImpactMeasurement(
        measurement_id="M_001",
        case_or_dataset_id="C_001",
        metric=metric,
    )
    res = validator.verify_measurement(meas)
    assert res.is_valid is True


def test_safety_validator_privacy_and_non_adjudication():
    validator = ImpactSafetyValidator()

    # PII rejection: Aadhaar card pattern
    aadhaar_text = "Review for client with Aadhaar 2345 6789 0123 submitted"
    violations = validator.check_text(aadhaar_text)
    assert any("Aadhaar number detected" in v for v in violations)

    # PII rejection: Indian 10-digit mobile
    phone_text = "Contact representative at 9876543210 regarding evidence"
    violations_phone = validator.check_text(phone_text)
    assert any("mobile number detected" in v for v in violations_phone)

    # Non-adjudication rejection: verdict prediction
    verdict_text = "The AI system provided a verdict prediction of guilt"
    violations_verdict = validator.check_text(verdict_text)
    assert any("NON-ADJUDICATION VIOLATION" in v for v in violations_verdict)

    # Fake impact rejection: 100% success guarantee
    fake_impact_text = "Achieved 100% success rate on court judgments"
    violations_fake = validator.check_text(fake_impact_text)
    assert any("NO-FAKE-IMPACT VIOLATION" in v for v in violations_fake)


# ===========================================================================
# CATEGORY T: Phase 7 FastAPI Endpoints Integration
# ===========================================================================

def test_api_dossier_versioning_and_diff():
    case_id = "CASE_API_P7_01"
    twin = make_sample_twin(case_id)
    _TWINS[case_id] = twin

    # 1. Build Dossier version 1
    resp_v1 = client.post(
        f"/api/nyaya/cases/{case_id}/dossier/build",
        headers=AUTH_HEADERS,
    )
    assert resp_v1.status_code == 200
    v1_data = resp_v1.json()
    assert v1_data["version"] == 1

    # 2. Build Dossier version 2
    resp_v2 = client.post(
        f"/api/nyaya/cases/{case_id}/dossier/build",
        headers=AUTH_HEADERS,
    )
    assert resp_v2.status_code == 200
    v2_data = resp_v2.json()
    assert v2_data["version"] == 2
    assert v2_data["previous_fingerprint"] == v1_data["fingerprint"]

    # 3. List versions
    resp_list = client.get(
        f"/api/nyaya/cases/{case_id}/dossier/versions",
        headers=AUTH_HEADERS,
    )
    assert resp_list.status_code == 200
    versions = resp_list.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 1
    assert versions[1]["version_number"] == 2

    # 4. Get specific version
    resp_get_v1 = client.get(
        f"/api/nyaya/cases/{case_id}/dossier/versions/1",
        headers=AUTH_HEADERS,
    )
    assert resp_get_v1.status_code == 200
    assert resp_get_v1.json()["version"] == 1

    # 5. Diff versions
    resp_diff = client.post(
        f"/api/nyaya/cases/{case_id}/dossier/diff",
        json={"version_a": 1, "version_b": 2},
        headers=AUTH_HEADERS,
    )
    assert resp_diff.status_code == 200
    diff_data = resp_diff.json()
    assert diff_data["version_a"] == 1
    assert diff_data["version_b"] == 2

    # 6. Get Human Review Checklist
    resp_chk = client.get(
        f"/api/nyaya/cases/{case_id}/dossier/checklist",
        headers=AUTH_HEADERS,
    )
    assert resp_chk.status_code == 200
    chk_data = resp_chk.json()
    assert "items" in chk_data


def test_api_impact_events_and_privacy_guard():
    case_id = "CASE_API_IMPACT_01"

    # 1. Clean event recording
    resp = client.post(
        f"/api/nyaya/cases/{case_id}/impact/events",
        json={
            "event_type": "CONTRADICTION_DETECTED",
            "payload": {"candidate_id": "c_1", "severity": "HIGH"},
            "workflow_phase": "PHASE_4_GAUNTLET",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201
    evt_data = resp.json()
    assert evt_data["case_id"] == case_id

    # 2. Query events
    resp_get = client.get(
        f"/api/nyaya/cases/{case_id}/impact/events",
        headers=AUTH_HEADERS,
    )
    assert resp_get.status_code == 200
    events = resp_get.json()
    assert len(events) == 1

    # 3. Privacy violation attempt (Aadhaar number) -> Must be rejected with 400
    resp_pii = client.post(
        f"/api/nyaya/cases/{case_id}/impact/events",
        json={
            "event_type": "CONTRADICTION_DETECTED",
            "payload": {"details": "Witness Aadhaar: 9876 5432 1098 provided"},
        },
        headers=AUTH_HEADERS,
    )
    assert resp_pii.status_code == 400
    assert "Safety or privacy violation" in resp_pii.text


def test_api_experiments_and_benchmarks():
    case_id = "CASE_API_EXP_01"
    twin = make_sample_twin(case_id)
    _TWINS[case_id] = twin

    # 1. Run comparative experiment
    resp_exp = client.post(
        "/api/nyaya/experiments/run",
        json={"case_id": case_id},
        headers=AUTH_HEADERS,
    )
    assert resp_exp.status_code == 200
    exp_data = resp_exp.json()
    assert exp_data["case_id"] == case_id
    assert "baseline" in exp_data
    assert "treatment" in exp_data

    # 2. Run synthetic benchmark suite
    resp_bench = client.post(
        "/api/nyaya/experiments/benchmark",
        headers=AUTH_HEADERS,
    )
    assert resp_bench.status_code == 200
    benchmarks = resp_bench.json()
    assert len(benchmarks) == 12
    assert all(b["passed"] for b in benchmarks)


def test_api_impact_report_workflow_and_verification():
    case_id = "CASE_API_REPORT_01"
    twin = make_sample_twin(case_id)
    _TWINS[case_id] = twin

    # 1. Compile Impact Report
    resp_rep = client.post(
        f"/api/nyaya/cases/{case_id}/impact/report",
        headers=AUTH_HEADERS,
    )
    assert resp_rep.status_code == 200, resp_rep.text
    rep_data = resp_rep.json()
    assert rep_data["case_or_dataset_id"] == case_id
    assert "sec01_scope" in rep_data

    # 2. Get latest report
    resp_latest = client.get(
        f"/api/nyaya/cases/{case_id}/impact/report/latest",
        headers=AUTH_HEADERS,
    )
    assert resp_latest.status_code == 200

    # 3. Export JSON
    resp_json = client.get(
        f"/api/nyaya/cases/{case_id}/impact/report/export/json",
        headers=AUTH_HEADERS,
    )
    assert resp_json.status_code == 200
    json_export = resp_json.json()["export"]

    # 4. Verify Export via API
    resp_verify = client.post(
        "/api/nyaya/experiments/verify",
        json={"json_export": json_export},
        headers=AUTH_HEADERS,
    )
    assert resp_verify.status_code == 200
    assert resp_verify.json()["is_valid"] is True

    # 5. Export Markdown
    resp_md = client.get(
        f"/api/nyaya/cases/{case_id}/impact/report/export/markdown",
        headers=AUTH_HEADERS,
    )
    assert resp_md.status_code == 200
    assert "# NYAYA-SATYA Proven Impact Report" in resp_md.json()["export"]

    # 6. Executive KPI Summary
    resp_sum = client.get(
        f"/api/nyaya/cases/{case_id}/impact/summary",
        headers=AUTH_HEADERS,
    )
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    assert "automated_contradiction_discovery_count" in sum_data


# ===========================================================================
# CATEGORY U: Multi-Version Chain Integrity
# ===========================================================================

def test_multi_version_chain_integrity():
    store = DossierVersionStore()
    v1 = store.record_version("CASE_CHAIN", "fp_1", "Initial baseline", "jurist_1")
    v2 = store.record_version("CASE_CHAIN", "fp_2", "Evidence amendment", "jurist_2")
    v3 = store.record_version("CASE_CHAIN", "fp_3", "Causal graph refined", "jurist_1")
    v4 = store.record_version("CASE_CHAIN", "fp_4", "Repair simulation applied", "jurist_3")

    history = store.get_history("CASE_CHAIN")
    assert len(history) == 4
    assert [h.version_number for h in history] == [1, 2, 3, 4]
    assert history[0].previous_fingerprint is None
    assert history[1].previous_fingerprint == "fp_1"
    assert history[2].previous_fingerprint == "fp_2"
    assert history[3].previous_fingerprint == "fp_3"
    assert store.get_latest_version("CASE_CHAIN") == v4


# ===========================================================================
# CATEGORY V: SectionDiff Net Change Calculations
# ===========================================================================

def test_section_diff_net_change():
    sd = SectionDiff(
        section_name="sec04_claim_graph",
        added_ids=["C_1", "C_2", "C_3"],
        removed_ids=["C_old"],
        changed_ids=["C_mod"],
        unchanged_ids=["C_const_1", "C_const_2"],
    )
    d = sd.to_dict()
    assert d["section_name"] == "sec04_claim_graph"
    assert d["net_change"] == 2
    assert len(d["added_ids"]) == 3
    assert len(d["removed_ids"]) == 1


# ===========================================================================
# CATEGORY W: DossierDiff Across Multiple Sections
# ===========================================================================

def test_dossier_diff_multiple_sections():
    d1 = JudicialReviewDossier(case_id="CASE_MULTI", dossier_id="D1", version=1)
    d1.sec06_timeline.append(
        DossierEntry(entry_id="EVT_1", section_index=6, section_name="sec06_timeline", category=DossierItemCategory.FACT, title="Event 1", description="desc 1")
    )
    d1.sec13_vulnerabilities.append(
        DossierEntry(entry_id="VUL_1", section_index=13, section_name="sec13_vulnerabilities", category=DossierItemCategory.INFERENCE, title="Vuln 1", description="desc vuln")
    )

    d2 = JudicialReviewDossier(case_id="CASE_MULTI", dossier_id="D2", version=2)
    # EVT_1 remains
    d2.sec06_timeline.append(
        DossierEntry(entry_id="EVT_1", section_index=6, section_name="sec06_timeline", category=DossierItemCategory.FACT, title="Event 1", description="desc 1")
    )
    # VUL_1 removed, VUL_2 added
    d2.sec13_vulnerabilities.append(
        DossierEntry(entry_id="VUL_2", section_index=13, section_name="sec13_vulnerabilities", category=DossierItemCategory.INFERENCE, title="Vuln 2", description="desc vuln 2")
    )

    diff = DossierComparator.compare(d1, d2)
    assert diff.total_added == 1
    assert diff.total_removed == 1
    assert diff.total_unchanged == 1
    assert "sec13_vulnerabilities" in diff.section_diffs
    assert "VUL_2" in diff.section_diffs["sec13_vulnerabilities"].added_ids
    assert "VUL_1" in diff.section_diffs["sec13_vulnerabilities"].removed_ids


# ===========================================================================
# CATEGORY X: Human Review Item Status Transitions
# ===========================================================================

def test_human_review_item_all_statuses():
    item = ReviewItem(
        review_id="REV_LIFECYCLE",
        severity=ReviewSeverity.MEDIUM,
        source="unverified_authority",
        explanation="Foreign case citation requires gazette check",
        recommended_action="Verify citation in official gazette",
    )
    assert item.status == ReviewStatus.OPEN

    item.acknowledge(actor="ci-associate")
    assert item.status == ReviewStatus.ACKNOWLEDGED
    assert item.assigned_to == "ci-associate"

    item.reject(notes="Authority confirmed inapplicable", actor="ci-senior-jurist")
    assert item.status == ReviewStatus.REJECTED
    assert item.resolution_notes == "Authority confirmed inapplicable"
    assert item.resolved_at is not None

    d = item.to_dict()
    reconstructed = ReviewItem.from_dict(d)
    assert reconstructed.review_id == item.review_id
    assert reconstructed.status == ReviewStatus.REJECTED


# ===========================================================================
# CATEGORY Y: Empty Checklist and Serialization Edge Cases
# ===========================================================================

def test_empty_checklist():
    chk = HumanReviewChecklist(case_id="CASE_EMPTY", dossier_id="DOS_EMPTY", items=[])
    assert chk.total_count == 0
    assert chk.pending_count == 0
    assert chk.resolved_count == 0
    assert chk.critical_count == 0

    md = DossierFormatter.format_checklist_markdown(chk)
    assert "Total Review Items**: 0" in md

    d = chk.to_dict()
    reconstructed = HumanReviewChecklist.from_dict(d)
    assert reconstructed.total_count == 0


# ===========================================================================
# CATEGORY Z: Concurrent Event Collection
# ===========================================================================

def test_concurrent_event_collection():
    import threading

    collector = EventCollector()

    def record_batch(worker_id: int):
        for i in range(10):
            collector.record_event(
                ImpactEvent(
                    event_id=f"EVT_CONC_{worker_id}_{i}",
                    case_id=f"CASE_CONC_{worker_id}",
                    event_type=ImpactEventType.ADVERSARIAL_ATTACK_RUN,
                    phase="PHASE_4",
                )
            )

    threads = [threading.Thread(target=record_batch, args=(w,)) for w in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(collector.all_events()) == 50
    assert len(collector.get_events_for_case("CASE_CONC_0")) == 10


# ===========================================================================
# CATEGORY AA: Metric Calculators Boundary Testing
# ===========================================================================

def test_metric_calculators_empty_twin():
    empty_twin = CaseDigitalTwin(case_id="CASE_ZERO", twin_id="TWIN_ZERO")

    contra_metrics = ContradictionMetrics().compute_metrics(empty_twin)
    assert any(m.metric_id == "MET_CONTRA_TOTAL_CASE_ZERO" and m.value == 0.0 for m in contra_metrics)

    gap_metrics = EvidenceGapMetrics().compute_metrics(empty_twin)
    assert any(m.metric_id == "MET_GAP_UNSUP_COUNT_CASE_ZERO" and m.value == 0.0 for m in gap_metrics)

    prov_metrics = ProvenanceMetrics().compute_metrics(empty_twin)
    assert any(m.metric_id == "MET_PROV_COVERAGE_CASE_ZERO" and m.value == 1.0 for m in prov_metrics)


def test_repair_and_reattack_metrics():
    case_id = "CASE_REP_MET"

    # Repair metrics
    rep_metrics = RepairMetrics().compute_metrics(case_id, candidates=[], simulated_reports=[])
    assert any(m.metric_id == f"MET_REP_TOTAL_GEN_{case_id}" and m.value == 0.0 for m in rep_metrics)

    # Reattack metrics
    reatt_metrics = ReAttackMetrics().compute_metrics(case_id, assessments=[])
    assert any(m.metric_id == f"MET_REATK_IMMUNITY_RATE_{case_id}" and m.value == 0.0 for m in reatt_metrics)


# ===========================================================================
# CATEGORY BB: Privacy PII Patterns (PAN, Email, SSN)
# ===========================================================================

def test_safety_validator_pan_email_ssn():
    validator = ImpactSafetyValidator()

    pan_text = "Income tax filing references PAN ABCDE1234F for party"
    assert any("PAN card number detected" in v for v in validator.check_text(pan_text))

    email_text = "Direct correspondence sent to counsel@chambers.org on May 1st"
    assert any("Email address detected" in v for v in validator.check_text(email_text))

    ssn_text = "US citizen witness identifier 123-45-6789 provided in annexure"
    assert any("SSN detected" in v for v in validator.check_text(ssn_text))


# ===========================================================================
# CATEGORY CC: Forbidden Marketing Terms Rejection
# ===========================================================================

def test_forbidden_marketing_terms_rejection():
    validator = ImpactSafetyValidator()

    bad_texts = [
        "System guarantees a 10x lawyer speedup across filings",
        "Autonomous judge module decides the petition",
        "Platform replaces lawyers for supreme court litigation",
    ]
    for text in bad_texts:
        violations = validator.check_text(text)
        assert any("NO-FAKE-IMPACT VIOLATION" in v for v in violations)


# ===========================================================================
# CATEGORY DD: Metric Validator Range Boundaries
# ===========================================================================

def test_metric_validator_boundaries():
    validator = MetricValidator()

    # Negative latency
    m_neg_time = ImpactMetric(
        metric_id="M_TIME_NEG",
        name="Latency",
        category=MetricCategory.WORKFLOW,
        classification=MetricClassification.OBSERVED,
        value=-5.0,
        unit="seconds",
        description="Invalid negative latency",
    )
    assert validator.validate_metric(m_neg_time).is_valid is False

    # Negative count
    m_neg_count = ImpactMetric(
        metric_id="M_COUNT_NEG",
        name="Count",
        category=MetricCategory.EVIDENCE_ANALYSIS,
        classification=MetricClassification.OBSERVED,
        value=-1.0,
        unit="count",
        description="Invalid negative count",
    )
    assert validator.validate_metric(m_neg_count).is_valid is False


# ===========================================================================
# CATEGORY EE: API Error Handling (404, 401)
# ===========================================================================

def test_api_404_missing_twin_handling():
    missing_id = "NON_EXISTENT_CASE_999"

    resp1 = client.get(f"/api/nyaya/cases/{missing_id}/dossier/latest", headers=AUTH_HEADERS)
    assert resp1.status_code == 404

    resp2 = client.post(f"/api/nyaya/cases/{missing_id}/dossier/build", headers=AUTH_HEADERS)
    assert resp2.status_code == 404

    resp3 = client.get(f"/api/nyaya/cases/{missing_id}/dossier/versions/1", headers=AUTH_HEADERS)
    assert resp3.status_code == 404

    resp4 = client.post("/api/nyaya/experiments/run", json={"case_id": missing_id}, headers=AUTH_HEADERS)
    assert resp4.status_code == 404

    resp5 = client.get(f"/api/nyaya/cases/{missing_id}/impact/report/latest", headers=AUTH_HEADERS)
    assert resp5.status_code == 404


def test_api_unauthorized_access():
    resp = client.post("/api/nyaya/experiments/benchmark")
    assert resp.status_code == 401

