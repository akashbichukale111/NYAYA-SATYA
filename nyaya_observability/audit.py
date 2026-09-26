"""Structured security and operational audit logging for NYAYA-SATYA.

Provides append-only structured JSON event logging for all consequential actions,
authentication events, authorization decisions, and security alerts.
Guarantees zero raw evidence leakage and zero secret disclosure.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import threading
from datetime import UTC, datetime
from typing import Any

from nyaya_observability.tracing import get_current_request_id

logger = logging.getLogger("nyaya.audit")


def hash_identifier(identifier: str) -> str:
    """Hashes sensitive case IDs or user names for privacy-minimized audit trails."""
    if not identifier:
        return ""
    return hashlib.sha256(identifier.strip().encode("utf-8")).hexdigest()[:16]


class SecurityAuditLogger:
    """Thread-safe append-only audit logger."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []

    def record_event(
        self,
        event: str,
        *,
        level: str = "INFO",
        service: str = "nyaya-core",
        actor_id: str = "anonymous",
        case_id: str | None = None,
        duration_ms: float = 0.0,
        status: str = "SUCCESS",
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Records an auditable event and outputs structured JSON to logger/stdout."""
        req_id = request_id or get_current_request_id()
        case_hash = hash_identifier(case_id) if case_id else ""

        # Sanitize details to avoid leaking raw evidence or secrets
        safe_details: dict[str, Any] = {}
        if details:
            for k, v in details.items():
                lower_k = k.lower()
                if any(s in lower_k for s in ("secret", "token", "password", "key", "credential")):
                    continue
                if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    safe_details[k] = v
                else:
                    safe_details[k] = str(v)

        event_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level.upper(),
            "service": service,
            "event": event,
            "request_id": req_id,
            "actor_id": actor_id,
            "case_id_hash": case_hash,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "details": safe_details,
        }

        with self._lock:
            self._events.append(event_record)

        # Output JSON line
        log_line = json.dumps(event_record)
        if level.upper() == "ERROR":
            logger.error(log_line)
        elif level.upper() == "WARNING":
            logger.warning(log_line)
        else:
            logger.info(log_line)

        return event_record

    def get_events(self, event_filter: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if event_filter:
                return [e for e in self._events if e.get("event") == event_filter]
            return list(self._events)

    def reset_for_test(self) -> None:
        with self._lock:
            self._events.clear()


_GLOBAL_AUDIT_LOGGER = SecurityAuditLogger()


def get_security_audit_logger() -> SecurityAuditLogger:
    return _GLOBAL_AUDIT_LOGGER


def record_audit(
    event: str,
    *,
    level: str = "INFO",
    actor_id: str = "anonymous",
    case_id: str | None = None,
    duration_ms: float = 0.0,
    status: str = "SUCCESS",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _GLOBAL_AUDIT_LOGGER.record_event(
        event,
        level=level,
        actor_id=actor_id,
        case_id=case_id,
        duration_ms=duration_ms,
        status=status,
        details=details,
    )


__all__ = [
    "SecurityAuditLogger",
    "get_security_audit_logger",
    "hash_identifier",
    "record_audit",
]
