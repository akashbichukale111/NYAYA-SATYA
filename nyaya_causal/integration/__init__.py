"""Integration adapters for NYAYA-SATYA Causal Reasoning."""

from nyaya_causal.integration.adversarial_adapter import AdversarialToCausalAdapter
from nyaya_causal.integration.tarka_adapter import CausalTarkaAdapter
from nyaya_causal.integration.twin_adapter import TwinToCausalAdapter
from nyaya_causal.integration.unwind_adapter import CausalUnwindAdapter

__all__ = [
    "AdversarialToCausalAdapter",
    "CausalTarkaAdapter",
    "CausalUnwindAdapter",
    "TwinToCausalAdapter",
]
