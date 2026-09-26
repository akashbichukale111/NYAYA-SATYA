"""Dossier versioning and historical tracking for NYAYA-SATYA Dossier 2.0.

Ensures that new dossier versions preserve historical lineage without overwriting.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class DossierVersionRecord:
    """Historical record representing a distinct versioned checkpoint of a judicial dossier."""

    version_id: str
    case_id: str
    version_number: int
    current_fingerprint: str
    previous_fingerprint: str | None
    change_summary: str
    actor_id: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "case_id": self.case_id,
            "version_number": self.version_number,
            "current_fingerprint": self.current_fingerprint,
            "previous_fingerprint": self.previous_fingerprint,
            "change_summary": self.change_summary,
            "actor_id": self.actor_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DossierVersionRecord:
        d = dict(data)
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        return cls(**d)


class DossierVersionStore:
    """Append-only store managing historical dossier versions per case."""

    def __init__(self) -> None:
        self._versions: dict[str, list[DossierVersionRecord]] = {}

    def record_version(
        self,
        case_id: str,
        current_fingerprint: str,
        change_summary: str,
        actor_id: str = "system",
    ) -> DossierVersionRecord:
        """Create and store a new sequential version record for a case."""
        history = self._versions.setdefault(case_id, [])
        version_number = len(history) + 1
        prev_fp = history[-1].current_fingerprint if history else None

        record = DossierVersionRecord(
            version_id=f"VER_{case_id}_{version_number}_{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            version_number=version_number,
            current_fingerprint=current_fingerprint,
            previous_fingerprint=prev_fp,
            change_summary=change_summary,
            actor_id=actor_id,
        )
        history.append(record)
        return record

    def get_history(self, case_id: str) -> list[DossierVersionRecord]:
        """Get complete sequential version history for a case."""
        return list(self._versions.get(case_id, []))

    def get_latest_version(self, case_id: str) -> DossierVersionRecord | None:
        """Get latest version record for a case if one exists."""
        history = self._versions.get(case_id, [])
        return history[-1] if history else None

    def reset_for_test(self) -> None:
        self._versions.clear()
