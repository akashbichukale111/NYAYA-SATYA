"""Document Parser Dispatcher for NYAYA-SATYA."""

from __future__ import annotations

from nyaya_evidence.contracts.evidence import MediaType
from nyaya_evidence.parsers.base import (
    BaseDocumentParser,
    DocumentParserError,
    ParsedDocument,
)
from nyaya_evidence.parsers.csv_parser import CsvDocumentParser
from nyaya_evidence.parsers.docx_parser import DocxDocumentParser
from nyaya_evidence.parsers.json_parser import JsonDocumentParser
from nyaya_evidence.parsers.pdf_parser import PdfDocumentParser
from nyaya_evidence.parsers.text_parser import TextDocumentParser


class DocumentParserDispatcher:
    """Dispatches raw evidence to the appropriate validated parser."""

    def __init__(self) -> None:
        self._parsers: dict[MediaType, BaseDocumentParser] = {}
        # Register standard parsers
        for p in (
            TextDocumentParser(),
            PdfDocumentParser(),
            DocxDocumentParser(),
            JsonDocumentParser(),
            CsvDocumentParser(),
        ):
            for m in p.supported_media_types:
                self._parsers[m] = p

    def parse(
        self,
        *,
        evidence_id: str,
        media_type: MediaType,
        raw_bytes: bytes,
        source_hash: str,
    ) -> ParsedDocument:
        parser = self._parsers.get(media_type)
        if not parser:
            raise DocumentParserError(
                f"No parser available for media type: {media_type.value}. "
                "Supported formats are TXT, PDF, DOCX, JSON, CSV."
            )
        return parser.parse(evidence_id=evidence_id, raw_bytes=raw_bytes, source_hash=source_hash)


__all__ = ["DocumentParserDispatcher"]
