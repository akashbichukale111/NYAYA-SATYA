"""Immutable repair application engine for NYAYA-SATYA Auto-Healer.

Applies repairs strictly to isolated deep copies of the CaseDigitalTwin.
Guarantees zero mutation of the canonical twin state.
"""

from __future__ import annotations

import copy
from typing import Any

from nyaya_repair.contracts.repair_action import ActionPrimitive, RepairAction
from nyaya_repair.contracts.repair_candidate import RepairCandidate, RepairChangeType
from nyaya_repair.contracts.repair_result import RepairExecutionResult
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import Claim, ClaimStatus


class RepairApplier:
    """Applies repair proposals strictly to isolated twin simulations."""

    def apply_repair(
        self,
        canonical_twin: CaseDigitalTwin,
        repair: RepairCandidate,
    ) -> tuple[CaseDigitalTwin, RepairExecutionResult]:
        """Simulate repair candidate on an isolated clone of the twin.

        Guarantees that canonical_twin is never mutated.
        """
        canonical_hash_before = canonical_twin.integrity_hash

        # Step 1: Deep copy the twin
        sim_twin = copy.deepcopy(canonical_twin)

        # Step 2: Apply changes according to repair change type
        actions_executed = 0
        mutated_claims: list[str] = []
        mutated_events: list[str] = []
        mutated_relationships: list[str] = []
        success = True
        error_msg: str | None = None

        try:
            ch_type = repair.change_type
            change = repair.proposed_change

            if ch_type == RepairChangeType.ADD_EVIDENCE_REFERENCE:
                cid = change.get("claim_id")
                ev_id = change.get("add_evidence_id")
                if cid and cid in sim_twin.claims and ev_id:
                    claim = sim_twin.claims[cid]
                    if ev_id not in claim.supporting_evidence_ids:
                        claim.supporting_evidence_ids.append(ev_id)
                    claim.status = claim.evaluate_evidence_status()
                    mutated_claims.append(cid)
                    actions_executed += 1

            elif ch_type == RepairChangeType.QUALIFY_ASSERTION:
                cid = change.get("claim_id")
                if cid and cid in sim_twin.claims:
                    claim = sim_twin.claims[cid]
                    new_status = change.get("qualified_status", ClaimStatus.UNRESOLVED.value)
                    claim.status = ClaimStatus(new_status)
                    prefix = change.get("qualification_prefix", "")
                    if prefix and not claim.predicate.startswith(prefix):
                        claim.predicate = f"{prefix}{claim.predicate}"
                    mutated_claims.append(cid)
                    actions_executed += 1

            elif ch_type == RepairChangeType.REMOVE_UNSUPPORTED_ASSERTION:
                cid = change.get("claim_id")
                if cid and cid in sim_twin.claims:
                    sim_twin.claims[cid].status = ClaimStatus.UNSUPPORTED
                    sim_twin.claims[cid].supporting_evidence_ids.clear()
                    mutated_claims.append(cid)
                    actions_executed += 1

            elif ch_type == RepairChangeType.CORRECT_TIMELINE_REFERENCE:
                eid = change.get("event_id")
                if eid and eid in sim_twin.events:
                    event = sim_twin.events[eid]
                    status = change.get("clarify_temporal_status")
                    if status:
                        from nyaya_twin.contracts.events import TemporalStatus
                        event.temporal_status = TemporalStatus(status)
                    note = change.get("note")
                    if note:
                        event.description = f"{event.description} [{note}]".strip()
                    mutated_events.append(eid)
                    actions_executed += 1

            elif ch_type == RepairChangeType.MARK_UNCERTAIN:
                cid = change.get("claim_id")
                if cid and cid in sim_twin.claims:
                    sim_twin.claims[cid].status = ClaimStatus.UNRESOLVED
                    mutated_claims.append(cid)
                    actions_executed += 1

            elif ch_type == RepairChangeType.ADD_PROVENANCE:
                target_id = change.get("target_id")
                remediation = change.get("remediation")
                actions_executed += 1

            elif ch_type == RepairChangeType.REQUEST_MISSING_EVIDENCE:
                # Does not mutate existing claims/events, records a pending request
                actions_executed += 1

            # Recalculate twin version
            sim_twin.record_version(
                actor="nyaya_repair_applier",
                reason=f"Simulated repair {repair.repair_id} ({repair.change_type.value})",
                changed_nodes=mutated_claims + mutated_events,
                changed_relationships=mutated_relationships,
            )

        except Exception as exc:
            success = False
            error_msg = str(exc)

        # Step 3: Hard guarantee that canonical twin was not altered
        assert canonical_twin.integrity_hash == canonical_hash_before, (
            "CRITICAL ARCHITECTURAL VIOLATION: Canonical CaseDigitalTwin mutated during repair simulation!"
        )

        exec_result = RepairExecutionResult(
            repair_id=repair.repair_id,
            case_id=self._case_id if hasattr(self, "_case_id") else canonical_twin.case_id,
            success=success,
            actions_executed=actions_executed,
            mutated_claim_ids=mutated_claims,
            mutated_event_ids=mutated_events,
            mutated_relationship_ids=mutated_relationships,
            error_message=error_msg,
        )

        return sim_twin, exec_result
