"""
Mutation Engine.

Applies simulated mutations ONLY to an isolated in-memory SimGraph clone.
Never touches the ORM / production database. Each mutation type maps to a
deterministic status change on the target node; the resulting status then
seeds the propagation engine (app/graph/traversal.py).
"""

from app.graph.graph_model import SimGraph
from app.enums import MutationType, NodeStatus

# Deterministic mapping: mutation type -> resulting node status on the TARGET node.
# This is intentionally simple and rule-based (no LLM authority over state).
_MUTATION_STATUS_MAP: dict[str, str] = {
    MutationType.REMOVE_EVIDENCE.value: NodeStatus.MISSING.value,
    MutationType.EXCLUDE_EVIDENCE.value: NodeStatus.EXCLUDED.value,
    MutationType.MARK_EVIDENCE_UNVERIFIED.value: NodeStatus.UNVERIFIED.value,
    MutationType.INVALIDATE_PROVENANCE.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.CONTRADICT_EVIDENCE.value: NodeStatus.CONFLICTING.value,
    MutationType.SUPERSEDE_EVIDENCE.value: NodeStatus.SUPERSEDED.value,

    MutationType.REMOVE_DOCUMENT.value: NodeStatus.MISSING.value,
    MutationType.CORRUPT_DOCUMENT.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.SUPERSEDE_DOCUMENT.value: NodeStatus.SUPERSEDED.value,
    MutationType.REPLACE_DOCUMENT_VERSION.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.MAKE_DOCUMENT_UNAVAILABLE.value: NodeStatus.MISSING.value,

    MutationType.REMOVE_CLAIM.value: NodeStatus.MISSING.value,
    MutationType.CONTRADICT_CLAIM.value: NodeStatus.CONFLICTING.value,
    MutationType.MARK_CLAIM_UNVERIFIED.value: NodeStatus.UNVERIFIED.value,
    MutationType.BREAK_CLAIM_DEPENDENCY.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,

    MutationType.REMOVE_ISSUE_SUPPORT.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.CREATE_ISSUE_CONFLICT.value: NodeStatus.CONFLICTING.value,
    MutationType.MARK_ISSUE_UNKNOWN.value: NodeStatus.UNKNOWN.value,

    MutationType.BLOCK_OBLIGATION.value: NodeStatus.BLOCKED.value,
    MutationType.REMOVE_OBLIGATION_EVIDENCE.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.MARK_OBLIGATION_UNVERIFIED.value: NodeStatus.UNVERIFIED.value,
    MutationType.SUPERSEDE_OBLIGATION.value: NodeStatus.SUPERSEDED.value,
    MutationType.CREATE_OBLIGATION_CONFLICT.value: NodeStatus.CONFLICTING.value,

    MutationType.REMOVE_TRACKED_DATE.value: NodeStatus.MISSING.value,
    MutationType.CHANGE_USER_ENTERED_DATE.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.MARK_DATE_UNKNOWN.value: NodeStatus.UNKNOWN.value,
    MutationType.CREATE_DATE_CONFLICT.value: NodeStatus.CONFLICTING.value,

    MutationType.REMOVE_HEARING_RESULT.value: NodeStatus.MISSING.value,
    MutationType.MARK_HEARING_UNVERIFIED.value: NodeStatus.UNVERIFIED.value,
    MutationType.CHANGE_SOURCE_STATED_HEARING_DATE.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.REMOVE_HEARING_DOCUMENT.value: NodeStatus.MISSING.value,

    MutationType.SUPERSEDE_ORDER.value: NodeStatus.SUPERSEDED.value,
    MutationType.REMOVE_ORDER_SOURCE.value: NodeStatus.MISSING.value,
    MutationType.MARK_ORDER_UNVERIFIED.value: NodeStatus.UNVERIFIED.value,
    MutationType.CREATE_ORDER_CONFLICT.value: NodeStatus.CONFLICTING.value,

    MutationType.INTRODUCE_DEFECT.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.REMOVE_REQUIRED_DOCUMENT.value: NodeStatus.MISSING.value,
    MutationType.CREATE_METADATA_CONFLICT.value: NodeStatus.CONFLICTING.value,
    MutationType.CREATE_MISSING_REFERENCE.value: NodeStatus.MISSING.value,
    MutationType.LEAVE_OBJECTION_UNRESOLVED.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,

    MutationType.MARK_CUSTODY_EVENT_UNVERIFIED.value: NodeStatus.UNVERIFIED.value,
    MutationType.CREATE_CUSTODY_CONFLICT.value: NodeStatus.CONFLICTING.value,
    MutationType.REMOVE_CUSTODY_DOCUMENT.value: NodeStatus.MISSING.value,
    MutationType.REMOVE_RELEASE_EVENT_SOURCE.value: NodeStatus.MISSING.value,

    MutationType.BLOCK_ACTION.value: NodeStatus.BLOCKED.value,
    MutationType.REMOVE_ACTION_DEPENDENCY.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.ACTION_FAILURE.value: NodeStatus.BLOCKED.value,
    MutationType.VERIFICATION_FAILURE.value: NodeStatus.UNVERIFIED.value,
    MutationType.APPROVAL_MISSING.value: NodeStatus.BLOCKED.value,

    MutationType.INVALIDATE_SOURCE.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
    MutationType.REMOVE_SOURCE_REFERENCE.value: NodeStatus.MISSING.value,
    MutationType.BREAK_PROVENANCE_CHAIN.value: NodeStatus.REQUIRES_HUMAN_REVIEW.value,
}


class MutationError(ValueError):
    pass


def apply_mutation(graph: SimGraph, mutation_type: str, target_node_id: str) -> dict:
    """
    Apply one mutation to the given (already-cloned) SimGraph.
    Returns a small record of what changed, for audit/diff purposes.
    Raises MutationError if the mutation type or target is invalid — this is
    intentional: an unrecognized mutation must never silently no-op.
    """
    if mutation_type not in _MUTATION_STATUS_MAP:
        raise MutationError(f"Unknown or unsupported mutation type: {mutation_type}")

    node = graph.nodes.get(target_node_id)
    if node is None:
        raise MutationError(f"Target node not found in graph: {target_node_id}")

    previous_status = node.status
    new_status = _MUTATION_STATUS_MAP[mutation_type]
    node.status = new_status

    return {
        "mutation_type": mutation_type,
        "target_node_id": target_node_id,
        "target_node_label": node.label,
        "previous_status": previous_status,
        "new_status": new_status,
    }


def apply_mutations(graph: SimGraph, mutations: list[dict]) -> list[dict]:
    """Apply an ordered list of {mutation_type, target_node_id} mutations."""
    records = []
    for m in mutations:
        records.append(apply_mutation(graph, m["mutation_type"], m["target_node_id"]))
    return records
