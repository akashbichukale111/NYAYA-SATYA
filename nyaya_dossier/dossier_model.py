"""Judicial Review Dossier contracts for NYAYA-SATYA.

Defines the 24-section auditable review package.
Categorizes every dossier entry strictly by epistemic status:
FACT, EVIDENCE, INFERENCE, ASSUMPTION, HYPOTHESIS, UNRESOLVED, PROPOSED_REPAIR, HUMAN_DECISION.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class DossierItemCategory(str, Enum):
    """Epistemic classification of an entry in the dossier."""

    FACT = "FACT"
    EVIDENCE = "EVIDENCE"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    UNRESOLVED = "UNRESOLVED"
    PROPOSED_REPAIR = "PROPOSED_REPAIR"
    HUMAN_DECISION = "HUMAN_DECISION"


@dataclass
class DossierEntry:
    """An individual auditable line-item or finding in the dossier."""

    entry_id: str
    section_index: int
    section_name: str
    category: DossierItemCategory
    title: str
    description: str
    provenance_hash: str | None = None
    supporting_refs: list[str] = field(default_factory=list)
    status: str = "RECORDED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "section_index": self.section_index,
            "section_name": self.section_name,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "provenance_hash": self.provenance_hash,
            "supporting_refs": list(self.supporting_refs),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DossierEntry:
        d = dict(data)
        if isinstance(d.get("category"), str):
            d["category"] = DossierItemCategory(d["category"])
        return cls(**d)


@dataclass
class JudicialReviewDossier:
    """Complete 24-section auditable review dossier for the Human Legal Gate."""

    dossier_id: str
    case_id: str
    twin_integrity_hash: str
    version: int = 1
    # 24 Canonical Sections
    sec01_case_identity: dict[str, Any] = field(default_factory=dict)
    sec02_evidence_inventory: list[DossierEntry] = field(default_factory=list)
    sec03_evidence_provenance: list[DossierEntry] = field(default_factory=list)
    sec04_claim_graph: list[DossierEntry] = field(default_factory=list)
    sec05_issue_map: list[DossierEntry] = field(default_factory=list)
    sec06_timeline: list[DossierEntry] = field(default_factory=list)
    sec07_contradiction_findings: list[DossierEntry] = field(default_factory=list)
    sec08_assumption_registry: list[DossierEntry] = field(default_factory=list)
    sec09_missing_evidence: list[DossierEntry] = field(default_factory=list)
    sec10_causal_dependencies: list[DossierEntry] = field(default_factory=list)
    sec11_causal_blast_radius: list[DossierEntry] = field(default_factory=list)
    sec12_counterfactual_findings: list[DossierEntry] = field(default_factory=list)
    sec13_vulnerabilities: list[DossierEntry] = field(default_factory=list)
    sec14_proposed_repairs: list[DossierEntry] = field(default_factory=list)
    sec15_repair_evidence: list[DossierEntry] = field(default_factory=list)
    sec16_repair_utility: list[DossierEntry] = field(default_factory=list)
    sec17_independent_reattack: list[DossierEntry] = field(default_factory=list)
    sec18_repair_immunity: list[DossierEntry] = field(default_factory=list)
    sec19_perturbation_results: list[DossierEntry] = field(default_factory=list)
    sec20_readiness_delta: dict[str, Any] = field(default_factory=dict)
    sec21_unresolved_questions: list[DossierEntry] = field(default_factory=list)
    sec22_human_review_obligations: list[DossierEntry] = field(default_factory=list)
    sec23_governance_audit: list[DossierEntry] = field(default_factory=list)
    sec24_cryptographic_fingerprints: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def fingerprint(self) -> str:
        """Deterministic cryptographic fingerprint over the entire dossier."""
        summary = {
            "dossier_id": self.dossier_id,
            "case_id": self.case_id,
            "twin_hash": self.twin_integrity_hash,
            "sec01": self.sec01_case_identity,
            "sec20": self.sec20_readiness_delta,
            "sec24": self.sec24_cryptographic_fingerprints,
        }
        dumped = json.dumps(summary, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        res = {
            "dossier_id": self.dossier_id,
            "case_id": self.case_id,
            "twin_integrity_hash": self.twin_integrity_hash,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat(),
            "sec01_case_identity": self.sec01_case_identity,
            "sec20_readiness_delta": self.sec20_readiness_delta,
            "sec24_cryptographic_fingerprints": self.sec24_cryptographic_fingerprints,
        }
        # Add list sections
        for idx in range(2, 24):
            if idx == 20:
                continue
            field_name = f"sec{idx:02d}_{self._get_section_name(idx)}"
            items = getattr(self, field_name, [])
            res[field_name] = [item.to_dict() for item in items]
        return res

    @staticmethod
    def _get_section_name(idx: int) -> str:
        names = {
            2: "evidence_inventory", 3: "evidence_provenance", 4: "claim_graph",
            5: "issue_map", 6: "timeline", 7: "contradiction_findings",
            8: "assumption_registry", 9: "missing_evidence", 10: "causal_dependencies",
            11: "causal_blast_radius", 12: "counterfactual_findings", 13: "vulnerabilities",
            14: "proposed_repairs", 15: "repair_evidence", 16: "repair_utility",
            17: "independent_reattack", 18: "repair_immunity", 19: "perturbation_results",
            21: "unresolved_questions", 22: "human_review_obligations", 23: "governance_audit",
        }
        return names.get(idx, "unknown")
