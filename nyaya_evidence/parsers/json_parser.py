"""JSON document parser for NYAYA-SATYA."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from nyaya_evidence.contracts.evidence import MediaType
from nyaya_evidence.parsers.base import (
    BaseDocumentParser,
    DocumentParserError,
    ExtractionMetadata,
    ParsedDocument,
    ParsedPage,
)


class JsonDocumentParser(BaseDocumentParser):
    @property
    def supported_media_types(self) -> set[MediaType]:
        return {MediaType.APPLICATION_JSON}

    @property
    def parser_name(self) -> str:
        return "JsonDocumentParser"

    @property
    def parser_version(self) -> str:
        return "json-parser@1.0.0"

    def parse(self, *, evidence_id: str, raw_bytes: bytes, source_hash: str) -> ParsedDocument:
        try:
            parsed_json = json.loads(raw_bytes.decode("utf-8"))
            formatted = json.dumps(parsed_json, indent=2, sort_keys=True)
        except Exception as exc:
            raise DocumentParserError(f"Malformed JSON document: {exc}") from exc

        extraction_hash = self.compute_extraction_hash(formatted)
        page = ParsedPage(page_number=1, text=formatted)

        meta = ExtractionMetadata(
            extraction_id=f"ext_{uuid.uuid4().hex[:16]}",
            evidence_id=evidence_id,
            media_type=MediaType.APPLICATION_JSON,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            source_hash=source_hash,
            extraction_hash=extraction_hash,
            total_pages=1,
            char_count=len(formatted),
            extracted_at=datetime.now(UTC),
        )

        return ParsedDocument(evidence_id=evidence_id, text_content=formatted, pages=[page], metadata=meta)


__all__ = ["JsonDocumentParser"]
