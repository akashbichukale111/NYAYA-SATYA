"""Reasoning package for TARKA-VYUH."""

from tarka_vyuh.reasoning.engines import AdversarialChallengeEngine
from tarka_vyuh.reasoning.registry import (
    CapabilityDescriptor,
    CapabilityStatus,
    ReasoningEngineNotImplementedError,
    execute_reasoning,
    get_capability,
    list_capabilities,
    register_capability,
)

__all__ = [
    "AdversarialChallengeEngine",
    "CapabilityDescriptor",
    "CapabilityStatus",
    "ReasoningEngineNotImplementedError",
    "execute_reasoning",
    "get_capability",
    "list_capabilities",
    "register_capability",
]
