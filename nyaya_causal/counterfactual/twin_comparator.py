"""Twin comparison engine for before/after counterfactual analysis.

Produces structured CounterfactualComparison objects.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_causal.contracts.comparison import CounterfactualComparison
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus


class TwinComparator:
    """Compares two CaseDigitalTwin states (original vs counterfactual)."""

    def compare(
        self,
        base_twin: CaseDigitalTwin,
        counterfactual_twin: CaseDigitalTwin,
        *,
        base_scenario_id: str = "BASE",
        counterfactual_scenario_id: str = "COUNTERFACTUAL",
    ) -> CounterfactualComparison:
        changed_nodes: list[dict[str, Any]] = []
        unchanged_nodes: list[str] = []
        changed_claim_states: list[dict[str, Any]] = []
        changed_issue_states: list[dict[str, Any]] = []
        changed_timeline: list[dict[str, Any]] = []
        new_contradictions: list[dict[str, Any]] = []
        resolved_contradictions: list[dict[str, Any]] = []
        added_rels: list[str] = []
        removed_rels: list[str] = []

        # Compare claims
        for cid, orig in base_twin.claims.items():
            cf = counterfactual_twin.claims.get(cid)
            if cf is None:
                changed_nodes.append({"node_id": cid, "type": "CLAIM", "change": "REMOVED"})
                continue
            orig_status = orig.evaluate_evidence_status()
            cf_status = cf.evaluate_evidence_status()
            if orig_status != cf_status:
                changed_nodes.append({"node_id": cid, "type": "CLAIM", "change": f"{orig_status.value} -> {cf_status.value}"})
                changed_claim_states.append({
                    "claim_id": cid,
                    "original": orig_status.value,
                    "counterfactual": cf_status.value,
                })
                # Track contradiction changes
                if cf_status == ClaimStatus.CONTRADICTED and orig_status != ClaimStatus.CONTRADICTED:
                    new_contradictions.append({"claim_id": cid, "new_status": cf_status.value})
                elif orig_status == ClaimStatus.CONTRADICTED and cf_status != ClaimStatus.CONTRADICTED:
                    resolved_contradictions.append({"claim_id": cid, "resolved_to": cf_status.value})
            else:
                unchanged_nodes.append(cid)

        # Compare events
        for eid, orig in base_twin.events.items():
            cf = counterfactual_twin.events.get(eid)
            if cf is None:
                changed_nodes.append({"node_id": eid, "type": "EVENT", "change": "REMOVED"})
                continue
            if orig.event_time != cf.event_time:
                changed_nodes.append({"node_id": eid, "type": "EVENT", "change": f"time {orig.event_time} -> {cf.event_time}"})
                changed_timeline.append({
                    "event_id": eid,
                    "original_time": orig.event_time,
                    "counterfactual_time": cf.event_time,
                })
            else:
                unchanged_nodes.append(eid)

        # Compare issues
        for iid, orig in base_twin.issues.items():
            cf = counterfactual_twin.issues.get(iid)
            if cf is None:
                changed_nodes.append({"node_id": iid, "type": "ISSUE", "change": "REMOVED"})
                continue
            if orig.status != cf.status:
                changed_issue_states.append({
                    "issue_id": iid,
                    "original": orig.status.value,
                    "counterfactual": cf.status.value,
                })
            else:
                unchanged_nodes.append(iid)

        # Compare relationships
        for rid in base_twin.relationships:
            if rid not in counterfactual_twin.relationships:
                removed_rels.append(rid)
        for rid in counterfactual_twin.relationships:
            if rid not in base_twin.relationships:
                added_rels.append(rid)

        # Compare evidence
        for evid in base_twin.evidence_refs:
            if evid not in counterfactual_twin.evidence_refs:
                changed_nodes.append({"node_id": evid, "type": "EVIDENCE", "change": "REMOVED"})
            else:
                unchanged_nodes.append(evid)

        comparison_id = f"CMP_{uuid.uuid4().hex[:12]}"
        return CounterfactualComparison(
            comparison_id=comparison_id,
            base_scenario_id=base_scenario_id,
            counterfactual_scenario_id=counterfactual_scenario_id,
            changed_nodes=changed_nodes,
            unchanged_nodes=unchanged_nodes,
            added_relationships=added_rels,
            removed_relationships=removed_rels,
            changed_claim_states=changed_claim_states,
            changed_issue_states=changed_issue_states,
            changed_timeline_relations=changed_timeline,
            new_contradictions=new_contradictions,
            resolved_contradictions=resolved_contradictions,
        )
