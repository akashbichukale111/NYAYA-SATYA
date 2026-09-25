"""PDF document parser for NYAYA-SATYA using pypdf.

Preserves page numbers, text/page relationships, and records OCR_NOT_AVAILABLE
when scanned/image-only pages contain no extractable text.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from nyaya_evidence.contracts.evidence import MediaType
from nyaya_evidence.parsers.base import (
    BaseDocumentParser,
    DocumentParserError,
    ExtractionMetadata,
    ParsedDocument,
    ParsedPage,
)


class PdfDocumentParser(BaseDocumentParser):
    @property
    def supported_media_types(self) -> set[MediaType]:
        return {MediaType.APPLICATION_PDF}

    @property
    def parser_name(self) -> str:
        return "PdfDocumentParser"

    @property
    def parser_version(self) -> str:
        return "pypdf-parser@1.0.0"

    def parse(self, *, evidence_id: str, raw_bytes: bytes, source_hash: str) -> ParsedDocument:
        stream = io.BytesIO(raw_bytes)
        try:
            reader = PdfReader(stream)
            if reader.is_encrypted:
                raise DocumentParserError("PDF is encrypted/password-protected; cannot extract text")

            total_pages = len(reader.pages)
            if total_pages == 0:
                raise DocumentParserError("PDF contains 0 pages")

            pages: list[ParsedPage] = []
            text_blocks: list[str] = []
            warnings: list[str] = []

            for i, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                clean_text = page_text.strip()

                if not clean_text:
                    # Scanned or image-only page
                    ocr_status = "OCR_NOT_AVAILABLE"
                    warnings.append(f"Page {i} contained no machine-readable text; OCR_NOT_AVAILABLE")
                    p = ParsedPage(page_number=i, text="[OCR_NOT_AVAILABLE]", ocr_applied=False, ocr_status=ocr_status)
                else:
                    p = ParsedPage(page_number=i, text=clean_text, ocr_applied=False, ocr_status=None)

                pages.append(p)
                text_blocks.append(f"--- PAGE {i} ---\n{p.text}")

            full_text = "\n\n".join(text_blocks)
            extraction_hash = self.compute_extraction_hash(full_text)

            meta = ExtractionMetadata(
                extraction_id=f"ext_{uuid.uuid4().hex[:16]}",
                evidence_id=evidence_id,
                media_type=MediaType.APPLICATION_PDF,
                parser_name=self.parser_name,
                parser_version=self.parser_version,
                source_hash=source_hash,
                extraction_hash=extraction_hash,
                total_pages=total_pages,
                char_count=len(full_text),
                extracted_at=datetime.now(UTC),
                warnings=warnings,
            )

            return ParsedDocument(evidence_id=evidence_id, text_content=full_text, pages=pages, metadata=meta)

        except (PdfReadError, Exception) as exc:
            if isinstance(exc, DocumentParserError):
                raise
            raise DocumentParserError(f"Failed to parse PDF document: {exc}") from exc


__all__ = ["PdfDocumentParser"]
