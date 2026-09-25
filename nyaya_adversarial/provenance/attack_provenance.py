"""Attack Provenance and Reproducibility for NYAYA-SATYA.

Guarantees full reproducibility and deterministic audit tracking for all
adversarial scenarios, findings, and gauntlet reports.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from nyaya_adversarial.contracts.attack import AttackScenario
from nyaya_adversarial.contracts.result import AdversarialFinding, AdversarialGauntletReport
from tarka_vyuh.contracts.provenance import ProvenanceRef


def compute_scenario_hash(scenario: AttackScenario) -> str:
    """Computes deterministic SHA-256 fingerprint for an AttackScenario."""
    payload = {
        "case_id": scenario.case_id,
        "attack_type": scenario.attack_type.value,
        "target_node_id": scenario.target_node_id,
        "target_node_type": scenario.target_node_type,
        "premise": scenario.premise,
        "attack_question": scenario.attack_question,
        "required_evidence": sorted(scenario.required_evidence),
        "parameters": {k: str(v) for k, v in sorted(scenario.parameters.items())},
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_finding_hash(finding: AdversarialFinding) -> str:
    """Computes deterministic SHA-256 fingerprint for an AdversarialFinding."""
    payload = {
        "case_id": finding.case_id,
        "finding_type": finding.finding_type.value,
        "target_id": finding.target_id,
        "severity": finding.severity.value,
        "evidence_ids": sorted(finding.evidence_ids),
        "claim_ids": sorted(finding.claim_ids),
        "issue_ids": sorted(finding.issue_ids),
        "explanation": finding.explanation,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_gauntlet_hash(report: AdversarialGauntletReport) -> str:
    """Computes deterministic SHA-256 fingerprint for an AdversarialGauntletReport."""
    finding_hashes = [compute_finding_hash(f) for f in report.findings]
    payload = {
        "case_id": report.case_id,
        "twin_hash": report.twin_hash,
        "total_attacks": report.total_attacks_executed,
        "finding_hashes": sorted(finding_hashes),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_attack_provenance_ref(scenario: AttackScenario) -> ProvenanceRef:
    """Creates a verifiable ProvenanceRef for an attack scenario."""
    s_hash = compute_scenario_hash(scenario)
    return ProvenanceRef.create(
        source_id=f"attack_{scenario.attack_id}",
        source_type="ADVERSARIAL_GAUNTLET",
        evidence_id=scenario.target_node_id,
        content_hash=s_hash,
        extraction_metadata={
            "actor": "TARKA_VYUH_ADVERSARIAL_ENGINE",
            "method": "DETERMINISTIC_RULE_ENGINE",
        },
    )
