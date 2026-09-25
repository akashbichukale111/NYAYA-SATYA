"""Base Document Parser interfaces and schemas for NYAYA-SATYA."""

from __future__ import annotations

import abc
import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_evidence.contracts.evidence import MediaType


@dataclass
class ParsedPage:
    page_number: int  # 1-indexed
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ocr_applied: bool = False
    ocr_status: str | None = None  # None | "OCR_NOT_AVAILABLE" | "OCR_SUCCESS"


@dataclass
class ExtractionMetadata:
    extraction_id: str
    evidence_id: str
    media_type: MediaType
    parser_name: str
    parser_version: str
    source_hash: str
    extraction_hash: str
    total_pages: int
    char_count: int
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["media_type"] = self.media_type.value
        data["extracted_at"] = self.extracted_at.isoformat()
        return data


@dataclass
class ParsedDocument:
    evidence_id: str
    text_content: str
    pages: list[ParsedPage]
    metadata: ExtractionMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "text_content": self.text_content,
            "pages": [asdict(p) for p in self.pages],
            "metadata": self.metadata.to_dict(),
        }


class DocumentParserError(RuntimeError):
    """Raised when parsing fails."""


class BaseDocumentParser(abc.ABC):
    """Abstract base parser for supported evidence formats."""

    @property
    @abc.abstractmethod
    def supported_media_types(self) -> set[MediaType]:
        pass

    @property
    @abc.abstractmethod
    def parser_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def parser_version(self) -> str:
        pass

    @abc.abstractmethod
    def parse(self, *, evidence_id: str, raw_bytes: bytes, source_hash: str) -> ParsedDocument:
        pass

    def compute_extraction_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = [
    "BaseDocumentParser",
    "DocumentParserError",
    "ExtractionMetadata",
    "ParsedDocument",
    "ParsedPage",
]
