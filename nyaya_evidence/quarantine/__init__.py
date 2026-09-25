"""Quarantine package for NYAYA-SATYA Evidence Foundation."""

from nyaya_evidence.quarantine.manager import (
    QuarantineManager,
    QuarantineViolationError,
)

__all__ = [
    "QuarantineManager",
    "QuarantineViolationError",
]
