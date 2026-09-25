"""Achilles-Heel Detection Engine for NYAYA-SATYA.

Identifies evidence and claim nodes with high dependency centrality coupled with
weak support, provenance gaps, or active contradiction exposure.
Strictly non-adjudicative: structural observation only, not verdict prediction.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.fragility import AchillesHeel, StructuralSeverity
from nyaya_adversarial.jenga.fragility_engine import JengaFragilityEngine
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class AchillesHeelEngine:
    """Engine that detects Achilles-heel vulnerabilities in the case structure."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id
        self.fragility_engine = JengaFragilityEngine(twin)

    def detect_achilles_heels(self) -> list[AchillesHeel]:
        """Scans twin nodes to detect high-centrality, high-fragility nodes."""
        achilles_list: list[AchillesHeel] = []

        # Analyze evidence nodes
        for ev_id, ref in self.twin.evidence_refs.items():
            report = self.fragility_engine.analyze_evidence_fragility(ev_id)
            total_deps = len(report.direct_dependents) + len(report.indirect_dependents)

            # Centrality score based on proportion of total claims impacted
            total_case_claims = max(len(self.twin.claims), 1)
            centrality = min(round(total_deps / total_case_claims, 3), 1.0)
            fragility = report.structural_fragility.score

            reasons: list[str] = []
            if total_deps >= 2:
                reasons.append(f"Supports {total_deps} downstream claim(s)")
            if report.single_source_dependencies:
                reasons.append(f"Sole source for {len(report.single_source_dependencies)} claim(s)")
            if report.contradiction_count > 0:
                reasons.append(f"Faces {report.contradiction_count} direct contradiction(s)")
            if report.provenance_gaps > 0:
                reasons.append("Unresolved provenance or chain of custody gap")

            # Conflicting evidence items
            conflicting_ev = [
                c.evidence_b_id if c.evidence_a_id == ev_id else c.evidence_a_id
                for c in self.twin.contradictions
                if c.evidence_a_id == ev_id or c.evidence_b_id == ev_id
            ]

            # High centrality AND (fragility > 0.4 or single source or contradiction or prov gap)
            is_achilles = (total_deps >= 1 and (report.contradiction_count > 0 or report.provenance_gaps > 0 or len(report.single_source_dependencies) >= 1))

            if is_achilles:
                severity = StructuralSeverity.CRITICAL if (centrality >= 0.5 and (report.contradiction_count > 0 or report.provenance_gaps > 0)) else (
                    StructuralSeverity.HIGH if (total_deps >= 2 or report.contradiction_count > 0) else StructuralSeverity.MEDIUM
                )

                explanation = (
                    f"Potential Achilles Heel: Multiple downstream claims ({total_deps}) depend on {ev_id} "
                    f"while {'; '.join(reasons)}."
                )

                achilles_list.append(
                    AchillesHeel(
                        achilles_id=f"ach_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        target_node_id=ev_id,
                        target_type="EVIDENCE",
                        centrality_score=centrality,
                        fragility_score=fragility,
                        severity=severity,
                        reasons=reasons,
                        dependent_claims=report.direct_dependents + report.indirect_dependents,
                        conflicting_evidence_ids=conflicting_ev,
                        provenance_gaps=report.provenance_gaps,
                        explanation=explanation,
                    )
                )

        return sorted(achilles_list, key=lambda a: (a.centrality_score * a.fragility_score), reverse=True)
