"""
Simulation engine (sections 23-24).

CRITICAL RULES:
  - Simulations operate on an in-memory CLONE of a snapshot. They never
    write to Deadline/Obligation/Order/Hearing/Action tables, never create
    real Events, and never change `Case.current_version_number`.
  - Every result is labeled "SIMULATION ONLY".
  - This module never predicts judicial outcomes (verdicts, guilt, sentence).
    It only projects generic WORKFLOW state transitions (e.g. "an order
    typically creates an obligation"), or removes/reverts a specific
    change for a counterfactual "what if this hadn't happened" view.
"""
import copy

from app.diff import diff_snapshots

# Generic, non-judicial workflow transition rules used for Future State Preview.
# These describe typical PROCEDURAL/ADMINISTRATIVE consequences, not case outcomes.
WORKFLOW_NEXT_STATES = {
    "order_received": ["obligation_created"],
    "obligation_created": ["action_pending"],
    "deadline_created": ["action_pending"],
    "hearing_occurred": ["order_received", "deadline_created"],
    "reply_received": ["obligation_satisfied"],
    "evidence_added": ["verification_event"],
}


def simulate_counterfactual_removal(base_snapshot: dict, *, collection: str, entity_id: str) -> dict:
    """
    "What if this event had not happened?" - removes one entity from a
    cloned snapshot and returns a diff against the real snapshot.
    """
    clone = copy.deepcopy(base_snapshot)
    removed = clone.get(collection, {}).pop(entity_id, None)
    result_diff = diff_snapshots(base_snapshot, clone)
    return {
        "label": "SIMULATION ONLY",
        "hypothesis": f"What if {collection}/{entity_id} had not occurred?",
        "removed_item": removed,
        "simulated_snapshot": clone,
        "diff_vs_actual": result_diff,
    }


def simulate_field_change(base_snapshot: dict, *, collection: str, entity_id: str, field: str, new_value) -> dict:
    """
    "What if this field had a different value?" (e.g. deadline changed,
    order not received / superseded, evidence became unavailable).
    """
    clone = copy.deepcopy(base_snapshot)
    item = clone.get(collection, {}).get(entity_id)
    old_value = None
    if item is not None:
        old_value = item.get(field)
        item[field] = new_value
    result_diff = diff_snapshots(base_snapshot, clone)
    return {
        "label": "SIMULATION ONLY",
        "hypothesis": f"What if {collection}/{entity_id}.{field} were '{new_value}' instead of '{old_value}'?",
        "simulated_snapshot": clone,
        "diff_vs_actual": result_diff,
    }


def project_future_states(current_event_type: str) -> dict:
    """
    Future State Preview: purely a lookup over WORKFLOW_NEXT_STATES.
    Explicitly workflow/state simulation, never a judicial-outcome prediction.
    """
    next_states = WORKFLOW_NEXT_STATES.get(current_event_type, [])
    follow_up = []
    for n in next_states:
        follow_up.extend(WORKFLOW_NEXT_STATES.get(n, []))
    return {
        "label": "SIMULATION ONLY - workflow projection, not a legal outcome prediction",
        "current": current_event_type,
        "simulated_next_state": next_states,
        "simulated_follow_up": sorted(set(follow_up)),
    }
