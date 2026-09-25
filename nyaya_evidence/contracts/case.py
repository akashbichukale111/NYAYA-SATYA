"""Case contract for NYAYA-SATYA Evidence Foundation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Case:
    """A legal matter / case container for evidence and proceedings."""

    case_id: str
    title: str
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if len(self.case_id) > 128:
            raise ValueError("case_id cannot exceed 128 characters")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")
        if not self.title or not self.title.strip():
            raise ValueError("case title cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Case:
        d = dict(data)
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if isinstance(d.get("updated_at"), str):
            d["updated_at"] = datetime.fromisoformat(d["updated_at"])
        return cls(**d)


__all__ = [
    "Case",
]
