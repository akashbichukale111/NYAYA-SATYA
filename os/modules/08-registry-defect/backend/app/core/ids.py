"""ID generation and content-hashing helpers.

All entity IDs are prefixed ULIDs-lite (timestamp-sortable UUID4 strings
with a type prefix) so ids are stable, unique, and identifiable by type
in logs and audit records without a lookup.
"""
import hashlib
import uuid
from datetime import datetime, timezone


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
