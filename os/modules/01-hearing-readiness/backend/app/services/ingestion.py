"""
Ingestion pipeline (section 4). Extraction is intentionally simple and
honest: every result carries extraction_method + extraction_status, and
we never invent content OCR/parsing couldn't find. Adding a new format
means adding one function and one dispatch entry -- see EXTRACTORS below.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    text: str
    sections: list[dict] = field(default_factory=list)  # [{page, section, text, confidence}]
    method: str = "unknown"
    status: str = "OK"  # OK/PARTIAL/FAILED/OCR_NOT_AVAILABLE


def extract_txt(raw: bytes) -> ExtractionResult:
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return ExtractionResult(text="", method="txt_decode", status="FAILED")
    return ExtractionResult(
        text=text,
        sections=[{"page": None, "section": "full_text", "text": text, "confidence": "HIGH"}],
        method="txt_decode",
        status="OK",
    )


def extract_json(raw: bytes) -> ExtractionResult:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return ExtractionResult(text="", method="json_parse", status="FAILED")
    text = json.dumps(parsed, indent=2, ensure_ascii=False)
    return ExtractionResult(
        text=text,
        sections=[{"page": None, "section": "json_root", "text": text, "confidence": "HIGH"}],
        method="json_parse",
        status="OK",
    )


def extract_csv(raw: bytes) -> ExtractionResult:
    try:
        decoded = raw.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)
    except Exception:
        return ExtractionResult(text="", method="csv_parse", status="FAILED")
    text = "\n".join(", ".join(r) for r in rows)
    return ExtractionResult(
        text=text,
        sections=[{"page": None, "section": f"row_{i}", "text": ", ".join(r), "confidence": "HIGH"}
                   for i, r in enumerate(rows)],
        method="csv_parse",
        status="OK" if rows else "PARTIAL",
    )


def extract_docx(raw: bytes) -> ExtractionResult:
    try:
        import docx  # python-docx
    except ImportError:
        return ExtractionResult(text="", method="docx_unavailable", status="FAILED")
    try:
        doc = docx.Document(io.BytesIO(raw))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
    except Exception:
        return ExtractionResult(text="", method="docx_text", status="FAILED")
    text = "\n".join(paras)
    sections = [{"page": None, "section": f"para_{i}", "text": p, "confidence": "HIGH"}
                for i, p in enumerate(paras)]
    return ExtractionResult(text=text, sections=sections, method="docx_text",
                             status="OK" if paras else "PARTIAL")


def extract_pdf(raw: bytes) -> ExtractionResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractionResult(text="", method="pdf_unavailable", status="FAILED")
    try:
        reader = PdfReader(io.BytesIO(raw))
    except Exception:
        return ExtractionResult(text="", method="pdf_text", status="FAILED")

    sections, all_text, any_text = [], [], False
    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            any_text = True
        sections.append({
            "page": i + 1,
            "section": f"page_{i+1}",
            "text": page_text,
            "confidence": "MEDIUM" if page_text.strip() else "UNKNOWN",
        })
        all_text.append(page_text)

    if not any_text:
        # We do not have OCR wired up in this build -- say so explicitly
        # rather than pretending the page is empty of content.
        return ExtractionResult(
            text="",
            sections=sections,
            method="pdf_text_no_layer",
            status="OCR_NOT_AVAILABLE",
        )
    return ExtractionResult(text="\n".join(all_text), sections=sections,
                             method="pdf_text", status="OK")


EXTRACTORS = {
    ".txt": extract_txt,
    ".json": extract_json,
    ".csv": extract_csv,
    ".docx": extract_docx,
    ".pdf": extract_pdf,
}


def extract(ext: str, raw: bytes) -> ExtractionResult:
    fn = EXTRACTORS.get(ext)
    if fn is None:
        return ExtractionResult(text="", method="unsupported_type", status="FAILED")
    return fn(raw)
