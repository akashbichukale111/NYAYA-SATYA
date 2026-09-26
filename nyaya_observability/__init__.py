"""NYAYA-SATYA Observability Subsystem.

Provides metrics, tracing, health probes, readiness checks, audit logging,
and performance benchmarking.
"""

from __future__ import annotations

from nyaya_observability.audit import (
    SecurityAuditLogger,
    get_security_audit_logger,
    hash_identifier,
    record_audit,
)
from nyaya_observability.health import check_liveness, get_uptime_seconds
from nyaya_observability.metrics import (
    MetricSummary,
    ObservabilityMetricsRegistry,
    get_metrics_registry,
)
from nyaya_observability.performance import measure_execution_time
from nyaya_observability.readiness import check_readiness
from nyaya_observability.tracing import (
    generate_request_id,
    get_current_case_id,
    get_current_correlation_id,
    get_current_request_id,
    set_current_case_id,
    set_current_correlation_id,
    set_current_request_id,
    trace_scope,
)

__all__ = [
    "MetricSummary",
    "ObservabilityMetricsRegistry",
    "SecurityAuditLogger",
    "check_liveness",
    "check_readiness",
    "generate_request_id",
    "get_current_case_id",
    "get_current_correlation_id",
    "get_current_request_id",
    "get_metrics_registry",
    "get_security_audit_logger",
    "get_uptime_seconds",
    "hash_identifier",
    "measure_execution_time",
    "record_audit",
    "set_current_case_id",
    "set_current_correlation_id",
    "set_current_request_id",
    "trace_scope",
]
