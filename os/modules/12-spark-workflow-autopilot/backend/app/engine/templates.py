"""
Workflow templates: declarative task graphs.

Each template is data, not code. It says which tasks a workflow of a given
type generates, in what order, with what dependencies, and which tasks
require human approval / verification. No legal rule (deadlines, evidentiary
requirements, court procedure) is hard-coded here — only *operational*
sequencing of generic actions like "request", "verify", "review".
"""
from app.core.enums import RiskLevel

# Each task dict: key -> {title, task_type, owner_role, depends_on: [keys],
#                          approval_required, verification_required, risk_level}

TEMPLATES = {
    "evidence_gap": {
        "title": "Evidence Gap Resolution",
        "description": "Resolve a missing-evidence signal through request, receipt and verification.",
        "tasks": {
            "identify_missing": {
                "title": "Identify missing evidence",
                "task_type": "analysis",
                "owner_role": "PARALEGAL",
                "depends_on": [],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.SAFE_REVERSIBLE,
            },
            "request_evidence": {
                "title": "Request missing evidence",
                "task_type": "action",
                "owner_role": "PARALEGAL",
                "depends_on": ["identify_missing"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "receive_evidence": {
                "title": "Record evidence as received",
                "task_type": "intake",
                "owner_role": "PARALEGAL",
                "depends_on": ["request_evidence"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.SAFE_REVERSIBLE,
            },
            "validate_evidence": {
                "title": "Validate evidence completeness",
                "task_type": "validation",
                "owner_role": "ADVOCATE",
                "depends_on": ["receive_evidence"],
                "approval_required": False,
                "verification_required": True,
                "risk_level": RiskLevel.REVIEW_REQUIRED,
            },
            "attach_to_record": {
                "title": "Attach evidence to case record",
                "task_type": "action",
                "owner_role": "PARALEGAL",
                "depends_on": ["validate_evidence"],
                "approval_required": True,
                "verification_required": True,
                "risk_level": RiskLevel.APPROVAL_REQUIRED,
            },
        },
    },
    "deadline_preparation": {
        "title": "Deadline Preparation",
        "description": "Prepare for an approaching consequential date.",
        "tasks": {
            "inspect_source": {
                "title": "Inspect source of tracked date",
                "task_type": "analysis",
                "owner_role": "PARALEGAL",
                "depends_on": [],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.SAFE_REVERSIBLE,
            },
            "identify_prep_tasks": {
                "title": "Identify preparation tasks",
                "task_type": "planning",
                "owner_role": "ADVOCATE",
                "depends_on": ["inspect_source"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "assign_tasks": {
                "title": "Assign preparation tasks",
                "task_type": "action",
                "owner_role": "PARALEGAL",
                "depends_on": ["identify_prep_tasks"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "review_readiness": {
                "title": "Review readiness",
                "task_type": "review",
                "owner_role": "ADVOCATE",
                "depends_on": ["assign_tasks"],
                "approval_required": False,
                "verification_required": True,
                "risk_level": RiskLevel.REVIEW_REQUIRED,
            },
            "execute_approved_action": {
                "title": "Execute approved preparation action",
                "task_type": "action",
                "owner_role": "ADVOCATE",
                "depends_on": ["review_readiness"],
                "approval_required": True,
                "verification_required": True,
                "risk_level": RiskLevel.CONSEQUENTIAL,
            },
        },
    },
    "registry_defect": {
        "title": "Registry Defect Correction",
        "description": "Correct a detected registry defect.",
        "tasks": {
            "inspect_defect": {
                "title": "Inspect defect",
                "task_type": "analysis",
                "owner_role": "PARALEGAL",
                "depends_on": [],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.SAFE_REVERSIBLE,
            },
            "identify_corrective_material": {
                "title": "Identify missing/corrective material",
                "task_type": "analysis",
                "owner_role": "PARALEGAL",
                "depends_on": ["inspect_defect"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "prepare_correction": {
                "title": "Prepare correction task",
                "task_type": "action",
                "owner_role": "PARALEGAL",
                "depends_on": ["identify_corrective_material"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "human_review": {
                "title": "Human review of correction",
                "task_type": "review",
                "owner_role": "ADVOCATE",
                "depends_on": ["prepare_correction"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.REVIEW_REQUIRED,
            },
            "correction_execution": {
                "title": "Execute correction",
                "task_type": "action",
                "owner_role": "ADVOCATE",
                "depends_on": ["human_review"],
                "approval_required": True,
                "verification_required": True,
                "risk_level": RiskLevel.CONSEQUENTIAL,
            },
        },
    },
    "hearing_readiness": {
        "title": "Hearing Readiness Check",
        "description": "Resolve hearing readiness blockers.",
        "tasks": {
            "inspect_blockers": {
                "title": "Inspect readiness blockers",
                "task_type": "analysis",
                "owner_role": "PARALEGAL",
                "depends_on": [],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.SAFE_REVERSIBLE,
            },
            "create_tasks": {
                "title": "Create dependency-resolution tasks",
                "task_type": "planning",
                "owner_role": "PARALEGAL",
                "depends_on": ["inspect_blockers"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "verify_evidence": {
                "title": "Verify evidence readiness",
                "task_type": "verification",
                "owner_role": "ADVOCATE",
                "depends_on": ["create_tasks"],
                "approval_required": False,
                "verification_required": True,
                "risk_level": RiskLevel.REVIEW_REQUIRED,
            },
            "verify_documents": {
                "title": "Verify document readiness",
                "task_type": "verification",
                "owner_role": "ADVOCATE",
                "depends_on": ["create_tasks"],
                "approval_required": False,
                "verification_required": True,
                "risk_level": RiskLevel.REVIEW_REQUIRED,
            },
            "readiness_update": {
                "title": "Update case readiness state",
                "task_type": "action",
                "owner_role": "ADVOCATE",
                "depends_on": ["verify_evidence", "verify_documents"],
                "approval_required": True,
                "verification_required": True,
                "risk_level": RiskLevel.APPROVAL_REQUIRED,
            },
        },
    },
    "legal_aid_handoff": {
        "title": "Legal-Aid Handoff",
        "description": "Transfer case context to a new handler.",
        "tasks": {
            "inspect_missing_context": {
                "title": "Inspect missing context",
                "task_type": "analysis",
                "owner_role": "LEGAL_AID",
                "depends_on": [],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.SAFE_REVERSIBLE,
            },
            "gather_missing_info": {
                "title": "Gather missing information",
                "task_type": "action",
                "owner_role": "LEGAL_AID",
                "depends_on": ["inspect_missing_context"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "generate_handoff_packet": {
                "title": "Generate handoff packet",
                "task_type": "action",
                "owner_role": "LEGAL_AID",
                "depends_on": ["gather_missing_info"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.LOW_RISK,
            },
            "review": {
                "title": "Review handoff packet",
                "task_type": "review",
                "owner_role": "ADVOCATE",
                "depends_on": ["generate_handoff_packet"],
                "approval_required": False,
                "verification_required": False,
                "risk_level": RiskLevel.REVIEW_REQUIRED,
            },
            "recipient_ack": {
                "title": "Recipient acknowledgement",
                "task_type": "action",
                "owner_role": "LEGAL_AID",
                "depends_on": ["review"],
                "approval_required": True,
                "verification_required": True,
                "risk_level": RiskLevel.APPROVAL_REQUIRED,
            },
        },
    },
}


def get_template(workflow_type: str) -> dict:
    if workflow_type not in TEMPLATES:
        raise ValueError(f"Unknown workflow template: {workflow_type}")
    return TEMPLATES[workflow_type]


def list_templates() -> list:
    return [
        {"workflow_type": k, "title": v["title"], "description": v["description"], "task_count": len(v["tasks"])}
        for k, v in TEMPLATES.items()
    ]
