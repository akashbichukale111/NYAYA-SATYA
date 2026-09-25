"""Plain text parser for NYAYA-SATYA."""

from __future__ import annotations

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


class TextDocumentParser(BaseDocumentParser):
    @property
    def supported_media_types(self) -> set[MediaType]:
        return {MediaType.TEXT_PLAIN}

    @property
    def parser_name(self) -> str:
        return "TextDocumentParser"

    @property
    def parser_version(self) -> str:
        return "text-parser@1.0.0"

    def parse(self, *, evidence_id: str, raw_bytes: bytes, source_hash: str) -> ParsedDocument:
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("latin-1")
            except Exception as exc:
                raise DocumentParserError(f"Failed to decode text: {exc}") from exc

        extraction_hash = self.compute_extraction_hash(text)
        page = ParsedPage(page_number=1, text=text)

        meta = ExtractionMetadata(
            extraction_id=f"ext_{uuid.uuid4().hex[:16]}",
            evidence_id=evidence_id,
            media_type=MediaType.TEXT_PLAIN,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            source_hash=source_hash,
            extraction_hash=extraction_hash,
            total_pages=1,
            char_count=len(text),
            extracted_at=datetime.now(UTC),
        )

        return ParsedDocument(evidence_id=evidence_id, text_content=text, pages=[page], metadata=meta)


__all__ = ["TextDocumentParser"]
