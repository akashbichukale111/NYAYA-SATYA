"""
Agentic Action Planner (section 10/12). Every action this planner can
propose is deliberately "safe" by construction: preparatory artifacts
(checklists, reminder drafts, evidence indices) or non-destructive review
flags. Nothing here files a document, changes a legal position, or makes
a judicial-adjacent decision. All actions still require human approval
before "execution" (which itself just means: produce the artifact/flag).
"""
from __future__ import annotations

from app.models.action import Action
from app.models.blocker import Blocker
from app.services.security import enforce_legal_safety_firewall

ACTION_TEMPLATES = {
    "prepare_checklist": {
        "description": "Prepare a review checklist listing the specific unresolved items for this blocker.",
        "expected_effect": "A checklist artifact is generated listing the unresolved requirement(s) and their evidence gaps.",
        "risk": "LOW",
    },
    "draft_reminder_notice": {
        "description": "Draft a reminder notice addressed to the responsible actor about the pending item.",
        "expected_effect": "A draft reminder text is generated for human review and sending; nothing is sent automatically.",
        "risk": "LOW",
    },
    "compile_evidence_index": {
        "description": "Compile an index of all evidence currently linked to this requirement, with verification state.",
        "expected_effect": "An evidence index artifact is generated summarizing availability/verification per item.",
        "risk": "LOW",
    },
}


def propose_action(db, blocker: Blocker) -> Action:
    template_key = blocker.suggested_safe_action or "prepare_checklist"
    template = ACTION_TEMPLATES.get(template_key, ACTION_TEMPLATES["prepare_checklist"])

    reason = f"Blocker '{blocker.description}' is OPEN with severity {blocker.severity}: {blocker.downstream_impact}"
    enforce_legal_safety_firewall(reason)
    enforce_legal_safety_firewall(template["description"])

    unknowns = []
    if blocker.confidence in ("LOW", "UNKNOWN"):
        unknowns.append("Underlying confidence for this blocker's evidence is low.")

    action = Action(
        case_id=blocker.case_id,
        blocker_id=blocker.id,
        action_type=template_key,
        description=template["description"],
        reason=reason,
        evidence_refs=blocker.evidence_refs or [],
        risk=template["risk"],
        affected_case_state=[{"type": "BLOCKER", "id": blocker.id}],
        expected_effect=template["expected_effect"],
        unknowns=unknowns,
        status="PENDING_APPROVAL",
    )
    db.add(action)
    db.flush()
    return action
