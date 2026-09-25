"""Parsers package for NYAYA-SATYA Evidence Foundation."""

from nyaya_evidence.parsers.base import (
    BaseDocumentParser,
    DocumentParserError,
    ExtractionMetadata,
    ParsedDocument,
    ParsedPage,
)
from nyaya_evidence.parsers.csv_parser import CsvDocumentParser
from nyaya_evidence.parsers.dispatcher import DocumentParserDispatcher
from nyaya_evidence.parsers.docx_parser import DocxDocumentParser
from nyaya_evidence.parsers.json_parser import JsonDocumentParser
from nyaya_evidence.parsers.pdf_parser import PdfDocumentParser
from nyaya_evidence.parsers.text_parser import TextDocumentParser

__all__ = [
    "BaseDocumentParser",
    "CsvDocumentParser",
    "DocxDocumentParser",
    "DocumentParserDispatcher",
    "DocumentParserError",
    "ExtractionMetadata",
    "JsonDocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "PdfDocumentParser",
    "TextDocumentParser",
]
