"""Experiments module for NYAYA-SATYA Proven Impact subsystem.

Provides baseline runners, treatment runners, comparative trial coordinators,
and the canonical 12-scenario synthetic benchmark suite.
"""

from nyaya_impact.experiments.baseline_runner import BaselineRunner
from nyaya_impact.experiments.benchmark_suite import (
    BenchmarkScenarioResult,
    SyntheticBenchmarkSuite,
)
from nyaya_impact.experiments.experiment_runner import ExperimentRunner
from nyaya_impact.experiments.treatment_runner import TreatmentRunner

__all__ = [
    "BaselineRunner",
    "BenchmarkScenarioResult",
    "ExperimentRunner",
    "SyntheticBenchmarkSuite",
    "TreatmentRunner",
]
