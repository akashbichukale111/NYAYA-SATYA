"""
Privacy Engine — least-privilege field exposure per role.

DEMO NOTE: the ROLE_ACCESS matrix below is a static, in-code policy table
(section 33/34/62). It is NOT an admin-configurable rule engine yet —
that is tracked as NOT IMPLEMENTED in docs/LIMITATIONS.md. Every decision
this engine makes is explainable: call explain_access() to get the same
reason shown to a human reviewer, never a black-box allow/deny.
"""
from models import Sensitivity, Role

# What each recipient role may see, by sensitivity ceiling.
ROLE_CEILING = {
    Role.CITIZEN: Sensitivity.INTERNAL,
    Role.PARALEGAL: Sensitivity.SENSITIVE,
    Role.LEGAL_AID_WORKER: Sensitivity.SENSITIVE,
    Role.ADVOCATE: Sensitivity.HIGHLY_SENSITIVE,
    Role.ADMINISTRATOR: Sensitivity.HIGHLY_SENSITIVE,
    Role.REVIEWER: Sensitivity.HIGHLY_SENSITIVE,
}

SENSITIVITY_ORDER = [Sensitivity.PUBLIC, Sensitivity.INTERNAL, Sensitivity.SENSITIVE, Sensitivity.HIGHLY_SENSITIVE]


def is_allowed(sensitivity: Sensitivity, recipient_role: Role) -> bool:
    ceiling = ROLE_CEILING.get(recipient_role, Sensitivity.PUBLIC)
    return SENSITIVITY_ORDER.index(sensitivity) <= SENSITIVITY_ORDER.index(ceiling)


def explain_access(field_label: str, sensitivity: Sensitivity, recipient_role: Role) -> dict:
    allowed = is_allowed(sensitivity, recipient_role)
    return {
        "field": field_label,
        "sensitivity": sensitivity.value,
        "recipient": recipient_role.value,
        "permission": "ALLOWED" if allowed else "RESTRICTED",
        "reason": (
            f"{recipient_role.value} workflow permits up to {ROLE_CEILING[recipient_role].value}-level fields"
            if allowed else
            f"{recipient_role.value} workflow is capped at {ROLE_CEILING[recipient_role].value}; "
            f"this field is {sensitivity.value}, above that ceiling"
        ),
    }
