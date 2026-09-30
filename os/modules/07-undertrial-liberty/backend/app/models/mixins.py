import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime


def gen_id(prefix: str):
    def _gen():
        return f"{prefix}_{uuid.uuid4().hex[:16]}"
    return _gen


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProvenanceMixin:
    """
    Common provenance fields. Any field left null must be treated as
    'not available' by API responses (rendered as SOURCE LOCATION UNKNOWN),
    never fabricated.
    """
    source_document_id = Column(String, nullable=True)
    source_page = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
    source_text_snippet = Column(String, nullable=True)
    extraction_method = Column(String, nullable=True)
    reported_by_user_id = Column(String, nullable=True)
