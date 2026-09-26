"""Deterministic Dossier Comparison Engine for NYAYA-SATYA Dossier 2.0.

Computes a structural delta between any two dossier checkpoints:
identifying ADDED, REMOVED, CHANGED, and UNCHANGED elements across all categories.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nyaya_dossier.dossier_model import DossierEntry, JudicialReviewDossier


@dataclass
class SectionDiff:
    """Structural difference within a specific dossier section."""

    section_name: str
    added_ids: list[str] = field(default_factory=list)
    removed_ids: list[str] = field(default_factory=list)
    changed_ids: list[str] = field(default_factory=list)
    unchanged_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_name": self.section_name,
            "added_ids": list(self.added_ids),
            "removed_ids": list(self.removed_ids),
            "changed_ids": list(self.changed_ids),
            "unchanged_ids": list(self.unchanged_ids),
            "net_change": len(self.added_ids) - len(self.removed_ids),
        }


@dataclass
class DossierDiff:
    """Comprehensive structural difference report between two JudicialReviewDossier instances."""

    case_id: str
    dossier_a_id: str
    dossier_b_id: str
    version_a: int
    version_b: int
    fingerprint_a: str
    fingerprint_b: str
    section_diffs: dict[str, SectionDiff] = field(default_factory=dict)
    total_added: int = 0
    total_removed: int = 0
    total_changed: int = 0
    total_unchanged: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "dossier_a_id": self.dossier_a_id,
            "dossier_b_id": self.dossier_b_id,
            "version_a": self.version_a,
            "version_b": self.version_b,
            "fingerprint_a": self.fingerprint_a,
            "fingerprint_b": self.fingerprint_b,
            "total_added": self.total_added,
            "total_removed": self.total_removed,
            "total_changed": self.total_changed,
            "total_unchanged": self.total_unchanged,
            "summary": self.summary,
            "section_diffs": {k: v.to_dict() for k, v in self.section_diffs.items()},
        }


class DossierComparator:
    """Compares two JudicialReviewDossier checkpoints deterministically."""

    _SECTIONS_TO_COMPARE = [
        "sec02_evidence_inventory",
        "sec04_claim_graph",
        "sec05_issue_map",
        "sec06_timeline",
        "sec07_contradiction_findings",
        "sec08_assumption_registry",
        "sec09_missing_evidence",
        "sec10_causal_dependencies",
        "sec13_vulnerabilities",
        "sec14_proposed_repairs",
        "sec17_independent_reattack",
        "sec18_repair_immunity",
        "sec22_human_review_obligations",
    ]

    @classmethod
    def compare(
        cls,
        dossier_a: JudicialReviewDossier,
        dossier_b: JudicialReviewDossier,
    ) -> DossierDiff:
        return cls().compare_dossiers(dossier_a, dossier_b)

    def compare_dossiers(
        self,
        dossier_a: JudicialReviewDossier,
        dossier_b: JudicialReviewDossier,
    ) -> DossierDiff:
        """Compute structural delta between Dossier A (base) and Dossier B (target)."""
        section_diffs: dict[str, SectionDiff] = {}
        total_added = 0
        total_removed = 0
        total_changed = 0
        total_unchanged = 0

        for sec_name in self._SECTIONS_TO_COMPARE:
            items_a: list[DossierEntry] = getattr(dossier_a, sec_name, [])
            items_b: list[DossierEntry] = getattr(dossier_b, sec_name, [])

            dict_a = {item.entry_id: item for item in items_a}
            dict_b = {item.entry_id: item for item in items_b}

            added: list[str] = []
            removed: list[str] = []
            changed: list[str] = []
            unchanged: list[str] = []

            for eid in dict_b:
                if eid not in dict_a:
                    added.append(eid)
                else:
                    item_a = dict_a[eid]
                    item_b = dict_b[eid]
                    if (
                        item_a.status != item_b.status
                        or item_a.category != item_b.category
                        or item_a.description != item_b.description
                    ):
                        changed.append(eid)
                    else:
                        unchanged.append(eid)

            for eid in dict_a:
                if eid not in dict_b:
                    removed.append(eid)

            diff = SectionDiff(
                section_name=sec_name,
                added_ids=added,
                removed_ids=removed,
                changed_ids=changed,
                unchanged_ids=unchanged,
            )
            section_diffs[sec_name] = diff

            total_added += len(added)
            total_removed += len(removed)
            total_changed += len(changed)
            total_unchanged += len(unchanged)

        summary = (
            f"Dossier delta (v{dossier_a.version} -> v{dossier_b.version}): "
            f"+{total_added} added, -{total_removed} removed, ~{total_changed} changed, ={total_unchanged} unchanged."
        )

        return DossierDiff(
            case_id=dossier_a.case_id,
            dossier_a_id=dossier_a.dossier_id,
            dossier_b_id=dossier_b.dossier_id,
            version_a=dossier_a.version,
            version_b=dossier_b.version,
            fingerprint_a=dossier_a.fingerprint,
            fingerprint_b=dossier_b.fingerprint,
            section_diffs=section_diffs,
            total_added=total_added,
            total_removed=total_removed,
            total_changed=total_changed,
            total_unchanged=total_unchanged,
            summary=summary,
        )
