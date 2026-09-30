"""
Recovery Engine.

Generates SAFE, non-executing recovery proposals from a propagation result.
Every proposal is a suggestion requiring human approval — nothing here
executes anything against the real case graph. See enums for the recovery
action vocabulary; the mapping below is deterministic and rule-based.
"""

from app.enums import ImpactType, NodeStatus

_RECOVERY_BY_IMPACT = {
    ImpactType.SUPPORT_GAP.value: "REQUEST_MISSING_EVIDENCE",
    ImpactType.VERIFICATION_GAP.value: "VERIFY_SOURCE",
    ImpactType.NEW_CONFLICT.value: "REVIEW_CONFLICT",
    ImpactType.NEW_UNKNOWN.value: "VERIFY_DATE",
    ImpactType.NEWLY_BLOCKED.value: "REVERIFY_WORKFLOW_DEPENDENCY",
    ImpactType.REVIEW_REQUIRED.value: "REVIEW_ORDER",
}

_NODE_TYPE_HINT = {
    "DOCUMENT": "RESTORE_DOCUMENT",
    "EVIDENCE": "REQUEST_MISSING_EVIDENCE",
    "OBLIGATION": "VERIFY_OBLIGATION",
    "DEADLINE": "VERIFY_DATE",
    "ORDER": "REVIEW_ORDER",
    "REGISTRY_DEFECT": "RECHECK_REGISTRY_PACKAGE",
    "WORKFLOW": "REVERIFY_WORKFLOW_DEPENDENCY",
    "ACTION": "REVERIFY_WORKFLOW_DEPENDENCY",
}


def generate_recovery_options(propagation_affected: list, blast_radius: dict) -> list[dict]:
    """
    propagation_affected: list of AffectedNode-like dicts (already serialized).
    Produces one recovery option per distinct affected node, deduplicated by
    (node_id, recommended_action).
    """
    options = []
    seen = set()
    for a in propagation_affected:
        action = _NODE_TYPE_HINT.get(a.get("node_type"))
        if not action:
            for impact in a.get("impact_types", []):
                action = _RECOVERY_BY_IMPACT.get(impact)
                if action:
                    break
        if not action:
            action = "REVIEW_CONFLICT"

        key = (a["node_id"], action)
        if key in seen:
            continue
        seen.add(key)

        options.append({
            "action": action,
            "reason": f"{a.get('label', a['node_id'])} shows {', '.join(a.get('impact_types', []) or ['a structural gap'])} "
                      f"after the simulated change.",
            "affected_nodes": [a["node_id"]],
            "required_evidence": action in ("REQUEST_MISSING_EVIDENCE", "UPLOAD_CORRECT_VERSION"),
            "dependencies": a.get("path_from_root", []),
            "verification_required": True,
            "human_approval_required": True,
        })
    return options
