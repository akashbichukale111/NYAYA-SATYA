"""Tracing and request correlation for NYAYA-SATYA Observability Subsystem.

Provides request ID injection, correlation tracing across API and reasoning layers,
and context propagation.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

# Context variables for tracing within async tasks
_CURRENT_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_request_id", default=""
)
_CURRENT_CORRELATION_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_correlation_id", default=""
)
_CURRENT_CASE_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_case_id", default=""
)


def generate_request_id() -> str:
    """Generates a unique request identifier."""
    return f"req-{uuid.uuid4().hex[:16]}"


def get_current_request_id() -> str:
    """Retrieves current request ID, or generates a default if not set."""
    rid = _CURRENT_REQUEST_ID.get()
    return rid if rid else generate_request_id()


def set_current_request_id(request_id: str) -> None:
    _CURRENT_REQUEST_ID.set(request_id)


def get_current_correlation_id() -> str:
    return _CURRENT_CORRELATION_ID.get()


def set_current_correlation_id(correlation_id: str) -> None:
    _CURRENT_CORRELATION_ID.set(correlation_id)


def get_current_case_id() -> str:
    return _CURRENT_CASE_ID.get()


def set_current_case_id(case_id: str) -> None:
    _CURRENT_CASE_ID.set(case_id)


@contextmanager
def trace_scope(
    request_id: str | None = None,
    correlation_id: str | None = None,
    case_id: str | None = None,
) -> Iterator[dict[str, str]]:
    """Context manager to scope request and correlation context."""
    req_id = request_id or generate_request_id()
    corr_id = correlation_id or req_id
    c_id = case_id or ""

    t_req = _CURRENT_REQUEST_ID.set(req_id)
    t_corr = _CURRENT_CORRELATION_ID.set(corr_id)
    t_case = _CURRENT_CASE_ID.set(c_id)

    try:
        yield {
            "request_id": req_id,
            "correlation_id": corr_id,
            "case_id": c_id,
        }
    finally:
        _CURRENT_REQUEST_ID.reset(t_req)
        _CURRENT_CORRELATION_ID.reset(t_corr)
        _CURRENT_CASE_ID.reset(t_case)


__all__ = [
    "generate_request_id",
    "get_current_case_id",
    "get_current_correlation_id",
    "get_current_request_id",
    "set_current_case_id",
    "set_current_correlation_id",
    "set_current_request_id",
    "trace_scope",
]
