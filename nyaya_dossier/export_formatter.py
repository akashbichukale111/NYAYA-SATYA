"""Export formatters for NYAYA-SATYA Judicial Review Dossier.

Renders dossiers into clean Markdown or JSON for human legal reviewers.
"""

from __future__ import annotations

import json
from typing import Any

from nyaya_dossier.dossier_model import JudicialReviewDossier


class DossierFormatter:
    """Formats JudicialReviewDossier instances into export representations."""

    @staticmethod
    def to_json(dossier: JudicialReviewDossier, indent: int = 2) -> str:
        """Export dossier as formatted JSON."""
        return json.dumps(dossier.to_dict(), indent=indent, sort_keys=True)

    @staticmethod
    def to_markdown(dossier: JudicialReviewDossier) -> str:
        """Export dossier as an auditable, human-readable Markdown report."""
        lines: list[str] = [
            f"# JUDICIAL REVIEW DOSSIER: {dossier.case_id}",
            f"**Dossier ID**: `{dossier.dossier_id}`",
            f"**Case Digital Twin Hash**: `{dossier.twin_integrity_hash}`",
            f"**Dossier Fingerprint**: `{dossier.fingerprint}`",
            f"**Generated**: {dossier.created_at.isoformat()}",
            "",
            "> **LEGAL GOVERNANCE NOTICE**: This dossier is a structural analytical package",
            "> compiled by TARKA-VYUH under UNWIND Core governance. It does NOT predict verdicts,",
            "> determine liability, or act as an autonomous legal authority.",
            "> Final decision authority resides exclusively in the Human Legal Gate.",
            "",
            "---",
            "",
            "## 1. Case Identity",
            f"- **Case ID**: {dossier.sec01_case_identity.get('case_id')}",
            f"- **Twin ID**: {dossier.sec01_case_identity.get('twin_id')}",
            f"- **Version**: {dossier.sec01_case_identity.get('version')}",
            "",
            "## 2. Evidence Inventory",
        ]

        if dossier.sec02_evidence_inventory:
            for item in dossier.sec02_evidence_inventory:
                lines.append(f"- **[{item.category.value}]** {item.title}: {item.description}")
        else:
            lines.append("*(No evidence registered)*")

        lines.extend([
            "",
            "## 4. Claim Graph",
        ])
        if dossier.sec04_claim_graph:
            for item in dossier.sec04_claim_graph:
                lines.append(f"- **[{item.category.value}]** `{item.entry_id}`: {item.description} *(Status: {item.status})*")
        else:
            lines.append("*(No claims registered)*")

        lines.extend([
            "",
            "## 13. Vulnerabilities & Stress Points",
        ])
        if dossier.sec13_vulnerabilities:
            for item in dossier.sec13_vulnerabilities:
                lines.append(f"- **[{item.status}]** {item.title}: {item.description}")
        else:
            lines.append("*(No open structural vulnerabilities)*")

        lines.extend([
            "",
            "## 14. Proposed Repairs",
        ])
        if dossier.sec14_proposed_repairs:
            for item in dossier.sec14_proposed_repairs:
                lines.append(f"- **[{item.category.value}]** `{item.entry_id}`: {item.title} — {item.description}")
        else:
            lines.append("*(No proposed repairs)*")

        lines.extend([
            "",
            "## 18. Repair Immunity",
        ])
        if dossier.sec18_repair_immunity:
            for item in dossier.sec18_repair_immunity:
                lines.append(f"- **[{item.status}]** {item.title}: {item.description}")
        else:
            lines.append("*(No immunity assessments recorded)*")

        lines.extend([
            "",
            "## 20. Case Readiness Delta",
        ])
        rd = dossier.sec20_readiness_delta
        if rd:
            lines.append(f"- **Evidence Coverage Delta**: {rd.get('evidence_coverage_delta')}")
            lines.append(f"- **Contradictions Delta**: {rd.get('contradictions_delta')}")
            lines.append(f"- **Unsupported Claims Delta**: {rd.get('unsupported_claims_delta')}")
            lines.append(f"- **Regressions**: {rd.get('regressions_count')}")
            lines.append(f"- **Net Structural Progress**: {rd.get('net_structural_progress')}")
        else:
            lines.append("*(No readiness delta recorded)*")

        lines.extend([
            "",
            "## 22. Human Review Obligations",
        ])
        if dossier.sec22_human_review_obligations:
            for item in dossier.sec22_human_review_obligations:
                lines.append(f"- **[ACTION REQUIRED]** {item.title}: {item.description}")
        else:
            lines.append("*(Zero pending human review obligations)*")

        lines.extend([
            "",
            "---",
            "### Cryptographic Fingerprint Verification",
            f"- **Twin Integrity Hash**: `{dossier.sec24_cryptographic_fingerprints.get('twin_integrity_hash', '')}`",
            f"- **Dossier SHA-256 Fingerprint**: `{dossier.fingerprint}`",
        ])

        return "\n".join(lines)

    @staticmethod
    def format_checklist_markdown(checklist: Any) -> str:
        """Format HumanReviewChecklist into human-readable Markdown."""
        lines = [
            f"# HUMAN REVIEW CHECKLIST: Case {checklist.case_id}",
            f"**Dossier**: `{checklist.dossier_id}`",
            f"**Total Review Items**: {checklist.total_count} (Pending: {checklist.pending_count}, Critical: {checklist.critical_count})",
            "",
            "> **LEGAL NOTICE**: All items below require independent human advocate/judge review.",
            "",
        ]
        for item in checklist.items:
            lines.extend([
                f"### [{item.severity.value}] {item.review_id} ({item.status.value})",
                f"- **Source**: {item.source}",
                f"- **Explanation**: {item.explanation}",
                f"- **Recommended Action**: {item.recommended_action}",
            ])
            if item.evidence_refs:
                lines.append(f"- **Evidence References**: {', '.join(item.evidence_refs)}")
            if item.resolution_notes:
                lines.append(f"- **Resolution Notes**: {item.resolution_notes} *(by {item.assigned_to})*")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_diff_markdown(diff: Any) -> str:
        """Format DossierDiff into human-readable Markdown."""
        lines = [
            f"# DOSSIER STRUCTURAL DIFF: Case {diff.case_id}",
            f"**Comparing**: `{diff.dossier_a_id}` (v{diff.version_a}) vs `{diff.dossier_b_id}` (v{diff.version_b})",
            f"**Summary**: {diff.summary}",
            "",
            "| Section | Added | Removed | Changed | Unchanged |",
            "|---|---|---|---|---|",
        ]
        for sec_name, sdiff in diff.section_diffs.items():
            lines.append(
                f"| {sec_name} | {len(sdiff.added_ids)} | {len(sdiff.removed_ids)} | {len(sdiff.changed_ids)} | {len(sdiff.unchanged_ids)} |"
            )
        return "\n".join(lines)
