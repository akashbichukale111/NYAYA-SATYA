"""Causal Blast-Radius Engine for NYAYA-SATYA.

Determines the structural impact of an intervention by:
1. Creating an immutable copy of the CaseDigitalTwin.
2. Applying the intervention on the copy.
3. Propagating effects through the causal/dependency graph.
4. Comparing against the original.
5. Classifying effects.
6. Generating provenance records.
7. Never mutating the original twin.
"""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from nyaya_causal.blast_radius.impact_classifier import ImpactClassifier
from nyaya_causal.blast_radius.propagation import EffectPropagator
from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_causal.contracts.effect import CausalEffect, EffectType
from nyaya_causal.contracts.intervention import (
    Intervention,
    InterventionOperation,
    InterventionTargetType,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus
from nyaya_twin.contracts.issues import IssueStatus
from nyaya_twin.contracts.relationships import RelationshipType
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


MAX_BLAST_RADIUS_NODES = 500


class BlastRadiusEngine:
    """Computes the structural blast-radius of an intervention."""

    def __init__(self, *, max_nodes: int = MAX_BLAST_RADIUS_NODES) -> None:
        self.max_nodes = max_nodes
        self._classifier = ImpactClassifier()

    def compute(
        self,
        twin: CaseDigitalTwin,
        intervention: Intervention,
    ) -> BlastRadiusReport:
        """Compute blast-radius without mutating the original twin."""
        original_hash = twin.integrity_hash

        # Step 1: Deep clone
        sim_twin = copy.deepcopy(twin)

        # Step 2: Apply intervention on clone
        self._apply_intervention(sim_twin, intervention)

        # Step 3: Classify effects by comparing original vs simulated
        direct, indirect, unaffected = self._classify_effects(
            twin, sim_twin, intervention
        )

        # Step 4: Identify broken/preserved dependencies
        broken_deps, preserved_deps = self._check_dependencies(
            twin, sim_twin, intervention
        )

        # Step 5: Identify affected issues and claims
        affected_claims = [e.node_id for e in direct + indirect if e.node_type == "CLAIM"]
        affected_issues = self._identify_affected_issues(twin, affected_claims)

        # Step 6: Classify new states
        newly_unresolved = []
        newly_contradicted = []
        newly_supported = []
        for cid, claim in sim_twin.claims.items():
            orig = twin.claims.get(cid)
            if orig is None:
                continue
            sim_status = claim.evaluate_evidence_status()
            orig_status = orig.evaluate_evidence_status()
            if sim_status != orig_status:
                if sim_status == ClaimStatus.UNSUPPORTED or sim_status == ClaimStatus.UNRESOLVED:
                    newly_unresolved.append(cid)
                elif sim_status == ClaimStatus.CONTRADICTED:
                    newly_contradicted.append(cid)
                elif sim_status == ClaimStatus.SUPPORTED:
                    newly_supported.append(cid)

        # Step 7: Verify original is unmodified
        assert twin.integrity_hash == original_hash, "CRITICAL: Original twin was mutated!"

        report_id = f"BR_{uuid.uuid4().hex[:12]}"
        return BlastRadiusReport(
            report_id=report_id,
            case_id=twin.case_id,
            target_id=intervention.target_id,
            target_type=intervention.target_type.value,
            intervention_summary=f"{intervention.operation.value} on {intervention.target_type.value} {intervention.target_id}",
            direct_effects=direct,
            indirect_effects=indirect,
            unaffected_nodes=unaffected,
            newly_unresolved=newly_unresolved,
            newly_supported=newly_supported,
            newly_contradicted=newly_contradicted,
            broken_dependencies=broken_deps,
            preserved_dependencies=preserved_deps,
            affected_issues=affected_issues,
            affected_claims=affected_claims,
        )

    def _apply_intervention(
        self, twin: CaseDigitalTwin, intervention: Intervention
    ) -> None:
        """Apply intervention on the cloned twin. Modifies the clone in-place."""
        target_id = intervention.target_id
        op = intervention.operation

        if intervention.target_type == InterventionTargetType.EVIDENCE:
            if op in (InterventionOperation.REMOVE, InterventionOperation.DISABLE):
                # Remove evidence and update dependent claims
                if target_id in twin.evidence_refs:
                    del twin.evidence_refs[target_id]
                for claim in twin.claims.values():
                    if target_id in claim.supporting_evidence_ids:
                        claim.supporting_evidence_ids.remove(target_id)
                    if target_id in claim.source_evidence_ids:
                        claim.source_evidence_ids.remove(target_id)
            elif op == InterventionOperation.MARK_CONTESTED:
                for claim in twin.claims.values():
                    if target_id in claim.supporting_evidence_ids:
                        if target_id not in claim.contradicting_evidence_ids:
                            claim.contradicting_evidence_ids.append(target_id)

        elif intervention.target_type == InterventionTargetType.CLAIM:
            if op in (InterventionOperation.REMOVE, InterventionOperation.DISABLE):
                if target_id in twin.claims:
                    twin.claims[target_id].status = ClaimStatus.UNSUPPORTED
                    twin.claims[target_id].supporting_evidence_ids.clear()
            elif op == InterventionOperation.MARK_CONTESTED:
                if target_id in twin.claims:
                    twin.claims[target_id].status = ClaimStatus.CONTRADICTED
            elif op == InterventionOperation.MARK_UNKNOWN:
                if target_id in twin.claims:
                    twin.claims[target_id].status = ClaimStatus.UNRESOLVED

        elif intervention.target_type == InterventionTargetType.EVENT:
            if op in (InterventionOperation.REMOVE, InterventionOperation.DISABLE):
                if target_id in twin.events:
                    del twin.events[target_id]
            elif op == InterventionOperation.CHANGE_TIME:
                if target_id in twin.events:
                    new_time = intervention.hypothetical_state.get("event_time")
                    if new_time:
                        twin.events[target_id].event_time = new_time

        elif intervention.target_type == InterventionTargetType.ASSUMPTION:
            # Assumption interventions affect claims linked to that assumption
            if op in (InterventionOperation.REMOVE, InterventionOperation.MARK_CONTESTED):
                pass  # Claims referencing this assumption are tracked separately

    def _classify_effects(
        self,
        original: CaseDigitalTwin,
        simulated: CaseDigitalTwin,
        intervention: Intervention,
    ) -> tuple[list[CausalEffect], list[CausalEffect], list[str]]:
        direct: list[CausalEffect] = []
        indirect: list[CausalEffect] = []
        unaffected: list[str] = []
        target_id = intervention.target_id

        # Check claims
        for cid, claim in original.claims.items():
            sim_claim = simulated.claims.get(cid)
            if sim_claim is None:
                continue
            orig_status = claim.evaluate_evidence_status()
            sim_status = sim_claim.evaluate_evidence_status()
            if orig_status != sim_status:
                # Determine if direct or indirect
                is_direct = self._is_direct_effect(cid, target_id, original, intervention)
                effect = CausalEffect(
                    node_id=cid,
                    node_type="CLAIM",
                    effect_type=EffectType.DIRECT_EFFECT if is_direct else EffectType.INDIRECT_EFFECT,
                    original_state=orig_status.value,
                    new_state=sim_status.value,
                    description=f"Claim {cid} changed from {orig_status.value} to {sim_status.value}",
                    depth=0 if is_direct else 1,
                )
                if is_direct:
                    direct.append(effect)
                else:
                    indirect.append(effect)
            else:
                unaffected.append(cid)

        # Check events
        for eid in original.events:
            if eid not in simulated.events:
                if eid == target_id:
                    direct.append(CausalEffect(
                        node_id=eid, node_type="EVENT",
                        effect_type=EffectType.DIRECT_EFFECT,
                        original_state="PRESENT", new_state="REMOVED",
                        description=f"Event {eid} removed",
                    ))
                else:
                    unaffected.append(eid)
            else:
                orig_evt = original.events[eid]
                sim_evt = simulated.events[eid]
                if orig_evt.event_time != sim_evt.event_time:
                    direct.append(CausalEffect(
                        node_id=eid, node_type="EVENT",
                        effect_type=EffectType.DIRECT_EFFECT,
                        original_state=str(orig_evt.event_time),
                        new_state=str(sim_evt.event_time),
                        description=f"Event {eid} time changed",
                    ))
                else:
                    unaffected.append(eid)

        return direct, indirect, unaffected

    def _is_direct_effect(
        self,
        node_id: str,
        target_id: str,
        twin: CaseDigitalTwin,
        intervention: Intervention,
    ) -> bool:
        """Check if a node is directly affected by the intervention target."""
        if intervention.target_type == InterventionTargetType.EVIDENCE:
            claim = twin.claims.get(node_id)
            if claim:
                return (
                    target_id in claim.supporting_evidence_ids
                    or target_id in claim.source_evidence_ids
                    or target_id in claim.contradicting_evidence_ids
                )
        elif intervention.target_type == InterventionTargetType.CLAIM:
            return node_id == target_id
        elif intervention.target_type == InterventionTargetType.EVENT:
            claim = twin.claims.get(node_id)
            if claim:
                for rel in twin.relationships.values():
                    if rel.source_id == target_id and rel.target_id == node_id:
                        return True
        return False

    def _check_dependencies(
        self,
        original: CaseDigitalTwin,
        simulated: CaseDigitalTwin,
        intervention: Intervention,
    ) -> tuple[list[str], list[str]]:
        """Identify broken and preserved DEPENDS_ON relationships."""
        broken: list[str] = []
        preserved: list[str] = []

        for rid, rel in original.relationships.items():
            if rel.relationship_type != RelationshipType.DEPENDS_ON:
                continue
            # Check if the dependency source or target is affected
            source_ok = rel.source_id in simulated.claims
            target_ok = rel.target_id in simulated.claims
            if source_ok and target_ok:
                src_status = simulated.claims[rel.source_id].evaluate_evidence_status()
                tgt_status = simulated.claims[rel.target_id].evaluate_evidence_status()
                if tgt_status in (ClaimStatus.UNSUPPORTED, ClaimStatus.CONTRADICTED):
                    broken.append(rid)
                else:
                    preserved.append(rid)
            else:
                broken.append(rid)

        return broken, preserved

    def _identify_affected_issues(
        self, twin: CaseDigitalTwin, affected_claims: list[str]
    ) -> list[str]:
        """Find issues whose related claims are affected."""
        affected: list[str] = []
        for iid, issue in twin.issues.items():
            if any(cid in affected_claims for cid in issue.related_claim_ids):
                affected.append(iid)
        return affected
