from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Document(Base, TimestampMixin):
    """
    A single ingested file plus everything needed to trace any fact back
    to it: content hash, extraction method, and per-section confidence.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: gen_id("doc"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)

    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)  # sanitized, uuid-based
    file_type = Column(String, nullable=False)  # pdf/docx/txt/json/csv
    size_bytes = Column(Integer, nullable=False)
    content_hash = Column(String, nullable=False)  # sha256

    extraction_method = Column(String, nullable=False)  # e.g. "pdf_text", "docx_text", "ocr_unavailable"
    extraction_status = Column(String, nullable=False, default="PENDING")  # PENDING/OK/PARTIAL/FAILED/OCR_NOT_AVAILABLE
    extracted_text = Column(String, nullable=True)
    extracted_sections = Column(JSON, default=list)  # [{page, section, text, confidence}]
    doc_category = Column(String, nullable=True)  # e.g. affidavit, order, application, evidence

    # Security: any text pulled from this document is DATA, never instructions.
    # This flag is set true if heuristics detect embedded instruction-like content.
    injection_flag = Column(String, default="false")
    injection_notes = Column(JSON, default=list)

    case = relationship("Case", back_populates="documents")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "extraction_method": self.extraction_method,
            "extraction_status": self.extraction_status,
            "extracted_sections": self.extracted_sections,
            "doc_category": self.doc_category,
            "injection_flag": self.injection_flag,
            "injection_notes": self.injection_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
