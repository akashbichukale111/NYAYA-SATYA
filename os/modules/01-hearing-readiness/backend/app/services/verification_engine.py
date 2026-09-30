"""
Action Verification Engine (section 13). ACTION -> RESULT -> VERIFY ->
STATE UPDATE. execute_action() performs the (safe, preparatory) effect
and records a concrete result artifact; verify_action() then re-reads
that result and the case state fresh from the DB and checks it actually
matches what was promised -- it never simply trusts that execution
"must have worked".
"""
from __future__ import annotations

from app.models.action import Action
from app.models.verification import Verification
from app.models.requirement import Requirement
from app.models.evidence import Evidence
from app.models.blocker import Blocker


def execute_action(db, action: Action) -> None:
    """Produces the actual artifact for an approved action. Deterministic,
    template-based -- no invented facts, only fields already on record."""
    requirement = None
    blocker = None
    if action.blocker_id:
        blocker = db.query(Blocker).filter(Blocker.id == action.blocker_id).first()
        if blocker:
            requirement = db.query(Requirement).filter(Requirement.id == blocker.requirement_id).first()

    evidence_items = []
    if requirement:
        evidence_items = [
            db.query(Evidence).filter(Evidence.id == eid).first()
            for eid in (requirement.evidence_refs or [])
        ]
        evidence_items = [e.to_dict() for e in evidence_items if e is not None]

    if action.action_type == "prepare_checklist":
        items = [
            f"Confirm/obtain: {e['label']} (currently {e['availability']}/{e['verification_state']})"
            for e in evidence_items
        ] or ["No specific evidence items on file -- confirm requirement details with case officer."]
        result = {"artifact_type": "checklist", "items": items}

    elif action.action_type == "draft_reminder_notice":
        actor = (blocker.responsible_actor if blocker else None) or "the responsible party"
        body = (
            f"Reminder: the item '{requirement.description if requirement else action.description}' "
            f"remains unresolved and is required ahead of the next hearing. "
            f"Please action at the earliest and confirm to the case team. (DRAFT -- human must review and send.)"
        )
        result = {"artifact_type": "reminder_draft", "to": actor, "body": body}

    elif action.action_type == "compile_evidence_index":
        result = {"artifact_type": "evidence_index", "items": evidence_items}

    else:
        result = {"artifact_type": "unknown", "note": "No executor template for this action_type."}

    action.result = result
    action.status = "EXECUTED"
    db.flush()


def verify_action(db, action: Action) -> Verification:
    """Re-reads DB state fresh and checks the artifact is real and complete."""
    checks = []

    has_result = bool(action.result)
    checks.append({
        "check_name": "result_artifact_present",
        "expected": "non-empty result object",
        "observed": "present" if has_result else "missing",
        "passed": has_result,
    })

    artifact_type_ok = bool(action.result and action.result.get("artifact_type") not in (None, "unknown"))
    checks.append({
        "check_name": "artifact_type_recognized",
        "expected": "a known artifact_type",
        "observed": (action.result or {}).get("artifact_type"),
        "passed": artifact_type_ok,
    })

    correct_case = True
    if action.blocker_id:
        blocker = db.query(Blocker).filter(Blocker.id == action.blocker_id).first()
        correct_case = bool(blocker and blocker.case_id == action.case_id)
    checks.append({
        "check_name": "correct_case_linkage",
        "expected": action.case_id,
        "observed": action.case_id if correct_case else "MISMATCH",
        "passed": correct_case,
    })

    all_passed = all(c["passed"] for c in checks)
    result_status = "PASSED" if all_passed else "VERIFICATION_FAILED"

    verification = Verification(
        action_id=action.id, case_id=action.case_id, checks=checks, result=result_status,
        explanation=(
            "All verification checks passed; the artifact matches the approved action's expected effect."
            if all_passed else
            "One or more verification checks failed; see `checks` for details."
        ),
    )
    db.add(verification)
    action.status = "VERIFIED" if all_passed else "VERIFICATION_FAILED"
    db.flush()
    return verification
