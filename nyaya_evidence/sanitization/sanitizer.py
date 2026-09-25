"""Adversarial Sanitization Service for NYAYA-SATYA.

Protects against prompt injection, jailbreaking, and governance tampering inside evidence.
Treats all uploaded content as UNTRUSTED DATA and isolates hostile instruction sequences.
"""

from __future__ import annotations

import base64
import hashlib
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_evidence.contracts.evidence import EvidenceItem, EvidenceStatus


class RiskLevel(str, Enum):
    CLEAN = "CLEAN"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"


# Comprehensive regex rules for detecting adversarial prompts in evidence
_PATTERNS = [
    # Direct instruction overrides
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE), "DIRECT_OVERRIDE", RiskLevel.HIGH_RISK),
    (re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE), "DIRECT_OVERRIDE", RiskLevel.HIGH_RISK),
    (re.compile(r"forget\s+(everything\s+)?(you\s+know|previous)", re.IGNORECASE), "DIRECT_OVERRIDE", RiskLevel.HIGH_RISK),
    # System role spoofing
    (re.compile(r"<\s*\|?\s*im_start\s*\|?\s*>system", re.IGNORECASE), "SYSTEM_TAG_INJECTION", RiskLevel.BLOCKED),
    (re.compile(r"\[\s*system\s*:\s*", re.IGNORECASE), "SYSTEM_PREFIX_INJECTION", RiskLevel.HIGH_RISK),
    (re.compile(r"system\s*prompt\s*:", re.IGNORECASE), "SYSTEM_PROMPT_SPOOF", RiskLevel.HIGH_RISK),
    (re.compile(r"developer\s*mode\s*:\s*enabled?", re.IGNORECASE), "DEVELOPER_MODE_EXPLOIT", RiskLevel.BLOCKED),
    # Governance & authorization tampering
    (re.compile(r"mark\s+evidence\s+as\s+verified", re.IGNORECASE), "GOVERNANCE_TAMPERING", RiskLevel.BLOCKED),
    (re.compile(r"set\s+status\s*=\s*['\"]?human_approved['\"]?", re.IGNORECASE), "GOVERNANCE_TAMPERING", RiskLevel.BLOCKED),
    (re.compile(r"bypass\s+(governance|quarantine|human_gate)", re.IGNORECASE), "GOVERNANCE_TAMPERING", RiskLevel.BLOCKED),
    (re.compile(r"approve\s+this\s+action\s+immediately", re.IGNORECASE), "AUTHORITY_FORGERY", RiskLevel.HIGH_RISK),
    (re.compile(r"court\s+verdict\s*:\s*(guilty|innocent|liable)", re.IGNORECASE), "LEGAL_VERDICT_SPOOF", RiskLevel.SUSPICIOUS),
    # Secret exfiltration & command execution
    (re.compile(r"(reveal|print|expose|leak)\s+(the\s+)?(api_?key|password|token|secret|system_?prompt)", re.IGNORECASE), "EXFILTRATION_PROMPT", RiskLevel.HIGH_RISK),
    (re.compile(r"(execute\s+command|run\s+script|call\s+tool)\s*[:=]", re.IGNORECASE), "COMMAND_INJECTION", RiskLevel.BLOCKED),
]

# Zero-width spaces / invisible Unicode tricks
_ZERO_WIDTH_CHARS = re.compile(r"[\u200B-\u200D\uFEFF]")


@dataclass
class SanitizationResult:
    sanitization_id: str
    evidence_id: str
    risk_level: RiskLevel
    findings: list[str]
    detected_patterns: list[str]
    sanitized_content: str
    original_hash: str
    sanitized_hash: str
    sanitizer_version: str = "adversarial-sanitizer@1.0.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "COMPLETED"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk_level"] = self.risk_level.value
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AdversarialSanitizer:
    """Scans and sanitizes untrusted evidence text."""

    def sanitize(
        self,
        *,
        evidence_id: str,
        text_content: str,
        original_hash: str,
    ) -> SanitizationResult:
        findings: list[str] = []
        detected_patterns: list[str] = []
        max_risk = RiskLevel.CLEAN

        # 1. Detect zero-width characters
        if _ZERO_WIDTH_CHARS.search(text_content):
            findings.append("Detected zero-width / invisible Unicode obfuscation characters")
            detected_patterns.append("ZERO_WIDTH_UNICODE")
            max_risk = RiskLevel.SUSPICIOUS
            # Strip zero-width chars in sanitized output
            sanitized = _ZERO_WIDTH_CHARS.sub("", text_content)
        else:
            sanitized = text_content

        # 2. Pattern matching
        for pattern, pattern_name, risk in _PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                findings.append(f"Detected adversarial pattern {pattern_name} ({len(matches)} match(es))")
                detected_patterns.append(pattern_name)
                # Escalate risk level
                if risk is RiskLevel.BLOCKED:
                    max_risk = RiskLevel.BLOCKED
                elif risk is RiskLevel.HIGH_RISK and max_risk != RiskLevel.BLOCKED:
                    max_risk = RiskLevel.HIGH_RISK
                elif risk is RiskLevel.SUSPICIOUS and max_risk not in (RiskLevel.BLOCKED, RiskLevel.HIGH_RISK):
                    max_risk = RiskLevel.SUSPICIOUS

                # Neutralize matched injection text by wrapping in [QUARANTINED_UNTRUSTED_INSTRUCTION] tag
                sanitized = pattern.sub(f"[UNTRUSTED_INSTRUCTION_REDACTED:{pattern_name}]", sanitized)

        # 3. Base64 payload detection
        base64_blocks = re.findall(r"(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?", sanitized)
        for b64 in base64_blocks[:5]:
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                for pattern, pattern_name, risk in _PATTERNS:
                    if pattern.search(decoded):
                        findings.append(f"Obfuscated base64 payload containing {pattern_name} detected")
                        detected_patterns.append(f"BASE64_OBFUSCATED_{pattern_name}")
                        max_risk = RiskLevel.BLOCKED
            except Exception:
                pass

        sanitized_hash = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()

        return SanitizationResult(
            sanitization_id=f"san_{uuid.uuid4().hex[:16]}",
            evidence_id=evidence_id,
            risk_level=max_risk,
            findings=findings,
            detected_patterns=detected_patterns,
            sanitized_content=sanitized,
            original_hash=original_hash,
            sanitized_hash=sanitized_hash,
            timestamp=datetime.now(UTC),
            status="COMPLETED",
        )


__all__ = [
    "AdversarialSanitizer",
    "RiskLevel",
    "SanitizationResult",
]
