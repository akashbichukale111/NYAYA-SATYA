"""Experiment runner coordinating comparative trials between baseline and treatment.
"""

from __future__ import annotations

import uuid
from nyaya_impact.contracts.impact_baseline import ComparativeTrialResult
from nyaya_impact.contracts.impact_experiment import ExperimentResult, ImpactExperiment
from nyaya_impact.experiments.baseline_runner import BaselineRunner
from nyaya_impact.experiments.treatment_runner import TreatmentRunner
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class ExperimentRunner:
    """Coordinates and executes comparative baseline vs treatment experiments."""

    def __init__(
        self,
        baseline_runner: BaselineRunner | None = None,
        treatment_runner: TreatmentRunner | None = None,
    ) -> None:
        self.baseline_runner = baseline_runner or BaselineRunner()
        self.treatment_runner = treatment_runner or TreatmentRunner()

    def run_comparative_trial(
        self,
        twin: CaseDigitalTwin,
    ) -> ComparativeTrialResult:
        """Run both baseline simulation and treatment on twin, comparing outcomes."""
        base = self.baseline_runner.run_baseline(twin)
        trt = self.treatment_runner.run_treatment(twin)

        contra_delta = trt.contradictions_automatically_surfaced - base.contradictions_manually_found
        unsup_delta = trt.unsupported_claims_caught - base.unsupported_claims_caught
        prov_delta = trt.provenance_coverage_ratio - base.provenance_verified_manually_ratio

        # Ratio of automated checks to estimated manual minutes
        auto_to_manual = (
            trt.automated_checks_run / base.manual_review_time_estimated_minutes
            if base.manual_review_time_estimated_minutes > 0
            else 1.0
        )

        return ComparativeTrialResult(
            trial_id=f"TRIAL_{uuid.uuid4().hex[:8]}",
            case_id=twin.case_id,
            baseline=base,
            treatment=trt,
            contradiction_discovery_delta=contra_delta,
            unsupported_claim_detection_delta=unsup_delta,
            provenance_coverage_delta=prov_delta,
            automated_to_manual_ratio=auto_to_manual,
            notes="Comparative trial between estimated manual baseline and automated NYAYA-SATYA pipeline.",
        )
