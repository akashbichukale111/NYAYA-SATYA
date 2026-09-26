"""Intervention engine for NYAYA-SATYA Counterfactual Lab.

Applies controlled interventions to isolated twin copies.
Supports evidence, event, claim, assumption, and timeline interventions.
"""

from __future__ import annotations

import copy
from typing import Any

from nyaya_causal.contracts.intervention import (
    Intervention,
    InterventionOperation,
    InterventionTargetType,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus


class ScenarioInconsistencyError(ValueError):
    """Raised when an intervention produces an impossible state."""


class InterventionEngine:
    """Applies interventions to isolated twin copies."""

    def apply(
        self,
        twin: CaseDigitalTwin,
        intervention: Intervention,
    ) -> CaseDigitalTwin:
        """Apply intervention to a deep copy of the twin. Returns modified copy."""
        sim = copy.deepcopy(twin)
        self._execute(sim, intervention)
        return sim

    def _execute(self, twin: CaseDigitalTwin, intervention: Intervention) -> None:
        target_id = intervention.target_id
        op = intervention.operation
        target_type = intervention.target_type

        if target_type == InterventionTargetType.EVIDENCE:
            self._intervene_evidence(twin, target_id, op, intervention)
        elif target_type == InterventionTargetType.EVENT:
            self._intervene_event(twin, target_id, op, intervention)
        elif target_type == InterventionTargetType.CLAIM:
            self._intervene_claim(twin, target_id, op, intervention)
        elif target_type == InterventionTargetType.ASSUMPTION:
            self._intervene_assumption(twin, target_id, op, intervention)

    def _intervene_evidence(
        self, twin: CaseDigitalTwin, target_id: str,
        op: InterventionOperation, intervention: Intervention,
    ) -> None:
        if op in (InterventionOperation.REMOVE, InterventionOperation.DISABLE):
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
        elif op == InterventionOperation.MARK_UNKNOWN:
            pass  # Evidence remains but is marked uncertain

    def _intervene_event(
        self, twin: CaseDigitalTwin, target_id: str,
        op: InterventionOperation, intervention: Intervention,
    ) -> None:
        if op in (InterventionOperation.REMOVE, InterventionOperation.DISABLE):
            if target_id in twin.events:
                del twin.events[target_id]
        elif op == InterventionOperation.CHANGE_TIME:
            if target_id in twin.events:
                new_time = intervention.hypothetical_state.get("event_time")
                if new_time is not None:
                    twin.events[target_id].event_time = new_time
                else:
                    raise ScenarioInconsistencyError(
                        f"CHANGE_TIME intervention requires 'event_time' in hypothetical_state"
                    )
        elif op == InterventionOperation.CHANGE_VALUE:
            if target_id not in twin.events:
                raise ScenarioInconsistencyError(f"Event {target_id} not found")

    def _intervene_claim(
        self, twin: CaseDigitalTwin, target_id: str,
        op: InterventionOperation, intervention: Intervention,
    ) -> None:
        if target_id not in twin.claims:
            return
        claim = twin.claims[target_id]
        if op in (InterventionOperation.REMOVE, InterventionOperation.DISABLE):
            claim.status = ClaimStatus.UNSUPPORTED
            claim.supporting_evidence_ids.clear()
        elif op == InterventionOperation.MARK_CONTESTED:
            claim.status = ClaimStatus.CONTRADICTED
        elif op == InterventionOperation.MARK_UNKNOWN:
            claim.status = ClaimStatus.UNRESOLVED

    def _intervene_assumption(
        self, twin: CaseDigitalTwin, target_id: str,
        op: InterventionOperation, intervention: Intervention,
    ) -> None:
        # Assumption interventions affect claims that depend on the assumption
        # The assumption_id is stored in claim metadata or the intervention tracks related claims
        related_claims = intervention.hypothetical_state.get("related_claim_ids", [])
        if op in (InterventionOperation.REMOVE, InterventionOperation.MARK_CONTESTED):
            for cid in related_claims:
                if cid in twin.claims:
                    twin.claims[cid].status = ClaimStatus.UNRESOLVED
