"""Dossier builder for NYAYA-SATYA Judicial Review Dossier.

Compiles the comprehensive 24-section auditable review dossier across all subsystems.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.result import AdversarialGauntletReport
from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_dossier.dossier_model import (
    DossierEntry,
    DossierItemCategory,
    JudicialReviewDossier,
)
from nyaya_perturbation.stability_analyzer import StabilityReport
from nyaya_readiness.readiness_delta import CaseReadinessDelta
from nyaya_reattack.repair_immunity import RepairImmunityAssessment
from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.contracts.repair_result import SimulatedRepairReport
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class DossierBuilder:
    """Builds the 24-section auditable judicial review dossier."""

    def build_dossier(
        self,
        twin: CaseDigitalTwin,
        *,
        gauntlet_report: AdversarialGauntletReport | None = None,
        blast_report: BlastRadiusReport | None = None,
        repair: RepairCandidate | None = None,
        sim_report: SimulatedRepairReport | None = None,
        immunity: RepairImmunityAssessment | None = None,
        stability: StabilityReport | None = None,
        readiness_delta: CaseReadinessDelta | None = None,
    ) -> JudicialReviewDossier:
        """Compile a fully referenced dossier for Human Legal Gate review."""
        case_id = twin.case_id
        dossier_id = f"DOSSIER_{uuid.uuid4().hex[:10]}"

        dossier = JudicialReviewDossier(
            dossier_id=dossier_id,
            case_id=case_id,
            twin_integrity_hash=twin.integrity_hash,
            version=twin.version,
        )

        # 1. Case Identity
        dossier.sec01_case_identity = {
            "case_id": case_id,
            "twin_id": twin.twin_id,
            "version": twin.version,
            "created_at": twin.created_at.isoformat(),
            "integrity_hash": twin.integrity_hash,
        }

        # 2. Evidence Inventory
        for eid, ev in twin.evidence_refs.items():
            dossier.sec02_evidence_inventory.append(
                DossierEntry(
                    entry_id=f"EV_INV_{eid}",
                    section_index=2,
                    section_name="evidence_inventory",
                    category=DossierItemCategory.EVIDENCE,
                    title=f"Evidence {eid}",
                    description=getattr(ev, "sanitized_text", f"Evidence record {eid}")[:200],
                    provenance_hash=getattr(ev, "content_hash", None),
                )
            )

        # 3. Evidence Provenance
        for eid, ev in twin.evidence_refs.items():
            prov_refs = getattr(ev, "provenance_refs", ())
            for p in prov_refs:
                dossier.sec03_evidence_provenance.append(
                    DossierEntry(
                        entry_id=f"PROV_{p.ref_id}",
                        section_index=3,
                        section_name="evidence_provenance",
                        category=DossierItemCategory.EVIDENCE,
                        title=f"Lineage: {p.source_id}",
                        description=f"Type {p.source_type}, hash {p.content_hash[:16]}...",
                        provenance_hash=p.content_hash,
                    )
                )

        # 4. Claim Graph
        for cid, claim in twin.claims.items():
            dossier.sec04_claim_graph.append(
                DossierEntry(
                    entry_id=f"CLM_{cid}",
                    section_index=4,
                    section_name="claim_graph",
                    category=DossierItemCategory.FACT if claim.supporting_evidence_ids else DossierItemCategory.INFERENCE,
                    title=f"Claim {cid} ({claim.claim_type.value})",
                    description=claim.statement,
                    supporting_refs=list(claim.supporting_evidence_ids),
                    status=claim.status.value,
                )
            )

        # 5. Issue Map
        for iid, issue in twin.issues.items():
            dossier.sec05_issue_map.append(
                DossierEntry(
                    entry_id=f"ISS_{iid}",
                    section_index=5,
                    section_name="issue_map",
                    category=DossierItemCategory.UNRESOLVED if issue.status.value != "READY_FOR_REVIEW" else DossierItemCategory.INFERENCE,
                    title=issue.title,
                    description=issue.description or issue.title,
                    supporting_refs=list(issue.related_claim_ids),
                    status=issue.status.value,
                )
            )

        # 6. Timeline
        for eid, event in twin.events.items():
            dossier.sec06_timeline.append(
                DossierEntry(
                    entry_id=f"EVT_{eid}",
                    section_index=6,
                    section_name="timeline",
                    category=DossierItemCategory.FACT if event.event_time else DossierItemCategory.INFERENCE,
                    title=event.title,
                    description=f"Time: {event.event_time} (Precision: {event.time_precision.value})",
                    supporting_refs=list(event.source_evidence_ids),
                    status=event.temporal_status.value,
                )
            )

        # 7. Contradiction Findings
        for c in twin.contradictions:
            dossier.sec07_contradiction_findings.append(
                DossierEntry(
                    entry_id=f"CONTRA_{c.candidate_id if hasattr(c, 'candidate_id') else uuid.uuid4().hex[:6]}",
                    section_index=7,
                    section_name="contradiction_findings",
                    category=DossierItemCategory.UNRESOLVED,
                    title="Evidence Contradiction",
                    description=str(getattr(c, "explanation", c)),
                )
            )

        # 13. Vulnerabilities
        if gauntlet_report:
            for f in gauntlet_report.findings:
                dossier.sec13_vulnerabilities.append(
                    DossierEntry(
                        entry_id=f.finding_id,
                        section_index=13,
                        section_name="vulnerabilities",
                        category=DossierItemCategory.UNRESOLVED,
                        title=f"{f.finding_type.value} on {f.target_id}",
                        description=f.explanation,
                        status=f.severity.value,
                    )
                )

        # 14. Proposed Repairs
        if repair:
            dossier.sec14_proposed_repairs.append(
                DossierEntry(
                    entry_id=repair.repair_id,
                    section_index=14,
                    section_name="proposed_repairs",
                    category=DossierItemCategory.PROPOSED_REPAIR,
                    title=f"Repair: {repair.change_type.value}",
                    description=repair.rationale,
                    supporting_refs=list(repair.evidence_refs),
                    provenance_hash=repair.fingerprint,
                    status=repair.status.value,
                )
            )

        # 16. Repair Utility
        if sim_report:
            uv = sim_report.utility_vector
            dossier.sec16_repair_utility.append(
                DossierEntry(
                    entry_id=f"UTIL_{sim_report.report_id}",
                    section_index=16,
                    section_name="repair_utility",
                    category=DossierItemCategory.INFERENCE,
                    title="Multi-Dimensional Repair Utility Vector",
                    description=(
                        f"EvidenceSupport={uv.evidence_support}, LegalGrounding={uv.legal_grounding}, "
                        f"FragilityReduction={uv.fragility_reduction}, CollateralImpact={uv.collateral_impact}, "
                        f"NewVulnerabilities={uv.new_vulnerabilities}, MeetsHardConstraints={uv.satisfies_hard_constraints}"
                    ),
                    status="ACCEPTABLE" if sim_report.is_acceptable else "UNACCEPTABLE",
                )
            )

        # 18. Repair Immunity
        if immunity:
            dossier.sec18_repair_immunity.append(
                DossierEntry(
                    entry_id=f"IMM_{immunity.repair_id}",
                    section_index=18,
                    section_name="repair_immunity",
                    category=DossierItemCategory.INFERENCE,
                    title=f"Immunity Status: {immunity.status.value}",
                    description=immunity.explanation,
                    status=immunity.status.value,
                )
            )

        # 19. Perturbation Results
        if stability:
            dossier.sec19_perturbation_results.append(
                DossierEntry(
                    entry_id=f"STAB_{case_id}",
                    section_index=19,
                    section_name="perturbation_results",
                    category=DossierItemCategory.INFERENCE,
                    title="Perturbation Stability Evaluation",
                    description=stability.summary,
                    status="RESILIENT" if stability.is_resilient else "STABILITY_DEFECT_DETECTED",
                )
            )

        # 20. Case Readiness Delta
        if readiness_delta:
            dossier.sec20_readiness_delta = readiness_delta.to_dict()

        # 22. Human Review Obligations
        unsupported_claims = [cid for cid, c in twin.claims.items() if not c.supporting_evidence_ids]
        for cid in unsupported_claims:
            dossier.sec22_human_review_obligations.append(
                DossierEntry(
                    entry_id=f"OBLIG_{cid}",
                    section_index=22,
                    section_name="human_review_obligations",
                    category=DossierItemCategory.HUMAN_DECISION,
                    title=f"Review unsupported claim {cid}",
                    description=f"Human jurist review required for claim {cid} lacking evidentiary proof",
                )
            )

        # 24. Cryptographic Fingerprints
        dossier.sec24_cryptographic_fingerprints = {
            "twin_integrity_hash": twin.integrity_hash,
            "dossier_fingerprint": dossier.fingerprint,
        }

        return dossier
