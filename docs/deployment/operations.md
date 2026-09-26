# NYAYA-SATYA — Production Operations & Runbook

## 1. Routine Health & Readiness Monitoring
Automated orchestrators and monitoring agents poll the standard observability endpoints:

- **Liveness Probe**: `GET /health`
  - Validates that the Python runtime and ASGI server process are responsive.
  - Returns HTTP 200 with JSON payload `{"status": "alive", "timestamp": "..."}`.
- **Readiness Probe**: `GET /ready`
  - Validates that downstream state machines, evidence registries, and database adapters are ready to accept traffic.
  - Returns HTTP 200 `{"status": "ready"}` or HTTP 503 `{"status": "unready", "reason": "..."}`.
- **Version Probe**: `GET /version`
  - Returns software release version, git commit hash, and API spec version without leaking environment configuration.

---

## 2. Structured Audit Log Inspection
Consequential actions (case creation, proposal submission, human decisions, execution guard verifications) emit structured JSON events to `stdout`.

### Sample Audit Event
```json
{
  "timestamp": "2026-09-26T16:00:00Z",
  "level": "INFO",
  "service": "nyaya-core",
  "event": "HUMAN_APPROVED",
  "request_id": "req-9a8b7c6d5e4f",
  "actor_id": "human::chief_counsel",
  "case_id_hash": "a1b2c3d4e5f6...",
  "duration_ms": 42.5,
  "status": "SUCCESS",
  "proposal_version_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 3. Incident Response & Security Triage

### Case 1: Prompt Injection Detected in Ingested Document
1. Ingestion parser flags `RiskLevel.HIGH` or `RiskLevel.CRITICAL` in `AdversarialSanitizer`.
2. File remains quarantined under `.quarantine/` with status `BLOCKED_MALICIOUS`.
3. An audit event `PROMPT_INJECTION_DETECTED` is emitted with the file hash and sanitized sample.
4. No automated execution or twin update occurs. Human jurist is notified via the Human Review Checklist.

### Case 2: Cross-Case Access Attempt
1. A caller authenticated for `CASE_001` attempts to query `/api/nyaya/cases/CASE_002/*`.
2. `require_case_access` rejects the request with HTTP 403 Forbidden.
3. An audit event `UNAUTHORIZED_CASE_ACCESS_BLOCKED` is emitted recording the caller's principal, targeted case ID, and correlation ID.
4. If repetitive, the IP / principal is temporarily throttled by the rate-limiting governor.

### Case 3: Proposal Tampering Detection
1. `ExecutionGuard` evaluates a proposal prior to execution and detects that the current proposal SHA-256 hash does not match `decision_record.proposal_version_hash`.
2. Execution is immediately halted; `ExecutionBlockedError` is raised.
3. Proposal transitions to `BLOCKED`. A new human review is required.

---

## 4. Backup & Disaster Recovery
- **Case State & Twins**: Backed up via transactional Firestore export snapshots or encrypted volume backups.
- **Integrity Verification**: All restored dossiers and twins are verified against their deterministic semantic fingerprints before resuming analysis traffic.
- **Rollback Procedure**: In case of application regression, traffic is reverted to the previous container image revision in Cloud Run within seconds.
