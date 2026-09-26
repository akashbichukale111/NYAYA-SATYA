"""Integration components for NYAYA-SATYA Auto-Healer subsystem."""

from nyaya_repair.integration.adversarial_adapter import AdversarialRepairAdapter
from nyaya_repair.integration.causal_adapter import CausalRepairAdapter
from nyaya_repair.integration.tarka_adapter import TarkaRepairAdapter
from nyaya_repair.integration.unwind_adapter import (
    AutomatedRepairExecutionProhibitedError,
    UnwindRepairAdapter,
)

__all__ = [
    "AdversarialRepairAdapter",
    "AutomatedRepairExecutionProhibitedError",
    "CausalRepairAdapter",
    "TarkaRepairAdapter",
    "UnwindRepairAdapter",
]
