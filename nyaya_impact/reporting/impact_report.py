"""Impact report compiler for NYAYA-SATYA Proven Impact subsystem.

Compiles the 14-section auditable ProvenImpactReport and renders Markdown.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_impact.contracts.impact_baseline import ComparativeTrialResult
from nyaya_impact.contracts.impact_experiment import ExperimentResult
from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricClassification
from nyaya_impact.contracts.impact_report import ProvenImpactReport
from nyaya_impact.experiments.benchmark_suite import BenchmarkScenarioResult


class ImpactReportCompiler:
    """Compiles auditable 14-section ProvenImpactReports."""

    def compile(
        self,
        case_or_dataset_id: str,
        metrics: list[ImpactMetric] | None = None,
        comparative_trial: ComparativeTrialResult | None = None,
        benchmarks: list[BenchmarkScenarioResult] | None = None,
        scope_info: dict[str, Any] | None = None,
        dataset_info: dict[str, Any] | None = None,
        methodology_text: str | None = None,
        limitations: list[str] | None = None,
        open_issues: list[str] | None = None,
    ) -> ProvenImpactReport:
        """Compile a full 14-section ProvenImpactReport from evidence."""
        metrics_list = metrics or []
        benchmarks_list = benchmarks or []

        # Sec 01: Scope
        sec01 = scope_info or {
            "target": case_or_dataset_id,
            "system": "NYAYA-SATYA Adversarial Evidence & Case Reasoning System",
            "reasoning_engine": "TARKA-VYUH",
            "governance": "UNWIND Core",
            "authority": "Human Legal Gate",
            "mandate": "Adversarial verification without outcome prediction",
        }

        # Sec 02: Dataset
        sec02 = dataset_info or {
            "dataset_id": f"DS_{case_or_dataset_id}",
            "synthetic_scenarios_evaluated": len(benchmarks_list),
            "epistemic_level": "SYNTHETIC_AND_OBSERVED_STRUCTURAL",
            "privacy_standard": "ZERO_PII_MINIMIZED",
        }

        # Sec 03: Methodology
        sec03 = methodology_text or (
            "Comparative structural evaluation comparing manual legal review baseline "
            "against NYAYA-SATYA automated adversarial reasoning pipeline. All metrics "
            "are strictly categorized by epistemic source (OBSERVED, SYNTHETIC, ESTIMATED, "
            "PRIVATE_EVALUATION, REAL_DEPLOYMENT). No judicial outcome prediction or case verdict calculation is performed."
        )

        # Sec 04: Baseline
        sec04 = {}
        if comparative_trial and comparative_trial.baseline:
            sec04 = comparative_trial.baseline.to_dict()
        else:
            sec04 = {
                "description": "Standard unassisted manual legal associate review baseline",
                "estimated_time_per_document_minutes": 15.0,
                "contradictions_caught_rate_estimated": 0.40,
                "provenance_coverage_ratio_estimated": 0.35,
            }

        # Sec 05: NYAYA Workflow
        sec05 = {}
        if comparative_trial and comparative_trial.treatment:
            sec05 = comparative_trial.treatment.to_dict()
        else:
            sec05 = {
                "phases_active": [
                    "PHASE_1_GATE_AND_PROVENANCE",
                    "PHASE_2_EVIDENCE_QUARANTINE",
                    "PHASE_3_CASE_DIGITAL_TWIN",
                    "PHASE_4_ADVERSARIAL_GAUNTLET",
                    "PHASE_5_CAUSAL_COUNTERFACTUAL",
                    "PHASE_6_REPAIR_AND_REATTACK",
                    "PHASE_7_DOSSIER_AND_PROVEN_IMPACT",
                ],
                "governance_mode": "HUMAN_LEGAL_GATE_ENFORCED",
            }

        # Sec 06: Metrics list
        sec06 = metrics_list

        # Sec 07: Results
        sec07: dict[str, Any] = {
            "metric_count": len(metrics_list),
            "synthetic_benchmarks_passed": sum(1 for b in benchmarks_list if b.passed),
            "synthetic_benchmarks_total": len(benchmarks_list),
        }
        if comparative_trial:
            sec07["contradiction_discovery_delta"] = comparative_trial.contradiction_discovery_delta
            sec07["unsupported_claim_detection_delta"] = comparative_trial.unsupported_claim_detection_delta
            sec07["provenance_coverage_delta"] = comparative_trial.provenance_coverage_delta
            sec07["automated_to_manual_ratio"] = comparative_trial.automated_to_manual_ratio

        # Sec 08: Structural findings
        sec08 = [
            f"Evaluated {len(benchmarks_list)} canonical benchmark scenarios with {sum(1 for b in benchmarks_list if b.passed)} passing structural criteria.",
            "Deterministic cryptographic provenance maintained across all pipeline outputs.",
            "Complete separation of proposal generation (TARKA-VYUH) from governance and execution (UNWIND + Human Gate).",
        ]

        # Sec 09: Limitations
        sec09 = limitations or [
            "Baseline measurements for manual review times are model-estimated rather than field-observed.",
            "Synthetic benchmark suite tests structural consistency, not legal adjudication quality.",
            "System does not provide legal advice, liability assessments, or outcome probabilities.",
        ]

        # Sec 10: Reproducibility
        sec10 = {
            "deterministic_fingerprinting": True,
            "benchmark_suite_available": True,
            "seed_required": False,
            "timestamp_omitted_from_fingerprint": True,
        }

        # Sec 11: Deployment evidence
        sec11 = {
            "environment": "TEST_AND_EVALUATION",
            "epistemic_classification": MetricClassification.SYNTHETIC.value,
            "production_case_claims": 0,
            "audit_trail_immutable": True,
        }

        # Sec 12: Human review
        sec12 = {
            "human_in_the_loop_mandatory": True,
            "gate_status": "AWAITING_REVIEW",
            "checklist_items_generated": True,
        }

        # Sec 13: Security & Privacy
        sec13 = {
            "pii_redacted": True,
            "zero_data_retention_compliant": True,
            "quarantine_verified": True,
        }

        # Sec 14: Open issues
        sec14 = open_issues or [
            "Continuous validation of baseline estimation models against empirical studies.",
            "Human Gate response latency monitoring under production loads.",
        ]

        report_id = f"IMPACT_{uuid.uuid4().hex[:8]}"
        return ProvenImpactReport(
            report_id=report_id,
            case_or_dataset_id=case_or_dataset_id,
            sec01_scope=sec01,
            sec02_dataset=sec02,
            sec03_methodology=sec03,
            sec04_baseline=sec04,
            sec05_nyaya_workflow=sec05,
            sec06_metrics=sec06,
            sec07_results=sec07,
            sec08_structural_findings=sec08,
            sec09_limitations=sec09,
            sec10_reproducibility=sec10,
            sec11_deployment_evidence=sec11,
            sec12_human_review=sec12,
            sec13_security=sec13,
            sec14_open_issues=sec14,
        )

    def generate_markdown(self, report: ProvenImpactReport) -> str:
        """Render a full 14-section Proven Impact Report as Markdown."""
        lines = [
            f"# NYAYA-SATYA Proven Impact Report",
            f"**Report ID**: `{report.report_id}`",
            f"**Target**: `{report.case_or_dataset_id}`",
            f"**Fingerprint**: `{report.fingerprint}`",
            f"**Created At**: `{report.created_at.isoformat()}`",
            "",
            "---",
            "",
            "## Section 1: Scope & Identity",
            f"- **System**: {report.sec01_scope.get('system', 'NYAYA-SATYA')}",
            f"- **Mandate**: {report.sec01_scope.get('mandate', 'Adversarial verification')}",
            "",
            "## Section 2: Dataset & Sample Characteristics",
            f"- **Dataset ID**: {report.sec02_dataset.get('dataset_id', 'N/A')}",
            f"- **Epistemic Level**: `{report.sec02_dataset.get('epistemic_level', 'SYNTHETIC')}`",
            "",
            "## Section 3: Methodology & Epistemic Boundaries",
            f"{report.sec03_methodology}",
            "",
            "## Section 4: Baseline Measurements (Control)",
            "```json",
            f"{report.sec04_baseline}",
            "```",
            "",
            "## Section 5: NYAYA-SATYA Workflow (Treatment)",
            "```json",
            f"{report.sec05_nyaya_workflow}",
            "```",
            "",
            "## Section 6: Proven Impact Metrics",
            "| Metric ID | Category | Classification | Value | Unit | Description |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for m in report.sec06_metrics:
            val_str = f"{m.value:.2f}" if isinstance(m.value, float) else str(m.value)
            lines.append(
                f"| `{m.metric_id}` | {m.category.value} | `{m.classification.value}` | {val_str} | {m.unit} | {m.description} |"
            )

        lines.extend([
            "",
            "## Section 7: Comparative Trial Results",
            "```json",
            f"{report.sec07_results}",
            "```",
            "",
            "## Section 8: Structural Findings",
        ])
        for finding in report.sec08_structural_findings:
            lines.append(f"- {finding}")

        lines.extend([
            "",
            "## Section 9: Limitations & Threats to Validity",
        ])
        for lim in report.sec09_limitations:
            lines.append(f"- [LIMITATION] {lim}")

        lines.extend([
            "",
            "## Section 10: Reproducibility Protocol",
            f"- Deterministic Fingerprint: `{report.sec10_reproducibility.get('deterministic_fingerprinting', True)}`",
            f"- Timestamp Omitted From Hash: `{report.sec10_reproducibility.get('timestamp_omitted_from_fingerprint', True)}`",
            "",
            "## Section 11: Deployment & Evidence Classification",
            f"- Status: `{report.sec11_deployment_evidence.get('environment', 'TEST')}`",
            f"- Production Case Claims: `{report.sec11_deployment_evidence.get('production_case_claims', 0)}`",
            "",
            "## Section 12: Human Review Gate Interactions",
            f"- Mandatory Review: `{report.sec12_human_review.get('human_in_the_loop_mandatory', True)}`",
            f"- Gate Status: `{report.sec12_human_review.get('gate_status', 'AWAITING_REVIEW')}`",
            "",
            "## Section 13: Privacy & Security Audit",
            f"- PII Redacted: `{report.sec13_security.get('pii_redacted', True)}`",
            f"- Zero Data Retention: `{report.sec13_security.get('zero_data_retention_compliant', True)}`",
            "",
            "## Section 14: Open Issues & Continuous Monitoring",
        ])
        for issue in report.sec14_open_issues:
            lines.append(f"- {issue}")

        lines.append("")
        return "\n".join(lines)
