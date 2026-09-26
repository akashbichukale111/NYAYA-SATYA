"""NYAYA-SATYA Proven Impact Subsystem.

Provides auditable, reproducible, non-predictive structural impact measurement,
benchmarks, and reports for the NYAYA-SATYA Adversarial Evidence System.
"""

from nyaya_impact.collection.event_collector import ImpactEventCollector
from nyaya_impact.collection.session_tracker import SessionTracker
from nyaya_impact.collection.workflow_tracker import WorkflowTracker
from nyaya_impact.contracts.impact_baseline import (
    BaselineMeasurement,
    ComparativeTrialResult,
    TreatmentMeasurement,
)
from nyaya_impact.contracts.impact_event import ImpactEvent, ImpactEventType
from nyaya_impact.contracts.impact_experiment import (
    ExperimentResult,
    ImpactExperiment,
)
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

ContradictionMetricCalculator = ContradictionMetrics
EvidenceGapMetricCalculator = EvidenceGapMetrics
ProcessingTimeMetricCalculator = ProcessingTimeMetrics
ProvenanceMetricCalculator = ProvenanceMetrics
ReattackMetricCalculator = ReAttackMetrics
RepairMetricCalculator = RepairMetrics
ReviewMetricCalculator = ReviewMetrics

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

__all__ = [
    # Contracts
    "BaselineMeasurement",
    "BenchmarkScenarioResult",
    "ComparativeTrialResult",
    "EvidenceExporter",
    "ExperimentResult",
    "ExecutiveKPIs",
    "ImpactEvent",
    "ImpactEventType",
    "ImpactExperiment",
    "ImpactMeasurement",
    "ImpactMetric",
    "ImpactReportCompiler",
    "ImpactSafetyResult",
    "ImpactSafetyValidator",
    "ImpactSummaryGenerator",
    "MetricCategory",
    "MetricClassification",
    "MetricValidationResult",
    "MetricValidator",
    "ProvenImpactReport",
    "ProvenanceValidationResult",
    "ProvenanceValidator",
    "SyntheticBenchmarkSuite",
    "TreatmentMeasurement",
    # Collection
    "ImpactEventCollector",
    "SessionTracker",
    "WorkflowTracker",
    # Experiments
    "BaselineRunner",
    "ExperimentRunner",
    "TreatmentRunner",
    # Metrics
    "ContradictionMetricCalculator",
    "EvidenceGapMetricCalculator",
    "ProcessingTimeMetricCalculator",
    "ProvenanceMetricCalculator",
    "ReattackMetricCalculator",
    "RepairMetricCalculator",
    "ReviewMetricCalculator",
]
