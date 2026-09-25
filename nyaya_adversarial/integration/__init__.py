"""Integration module for NYAYA-SATYA Adversarial Subsystem."""

from __future__ import annotations

from nyaya_adversarial.integration.tarka_adapter import TarkaAdversarialAdapter
from nyaya_adversarial.integration.twin_adapter import TwinAdversarialAdapter
from nyaya_adversarial.integration.unwind_adapter import UnwindAdversarialAdapter

__all__ = [
    "TarkaAdversarialAdapter",
    "TwinAdversarialAdapter",
    "UnwindAdversarialAdapter",
]
