"""Module Registry for NYAYA-SATYA OS.
Registers and tracks the 12 integrated engines, their health, routes, and features.
"""

from typing import List, Dict, Optional
from contracts.models import ModuleMetadata, ModuleCategory, ModuleHealthStatus

REGISTRY: List[ModuleMetadata] = [
    ModuleMetadata(
        module_id="mod-01-hearing-readiness",
        number=1,
        name="Hearing Readiness Engine",
        slug="hearing-readiness",
        category=ModuleCategory.CASE_ACCELERATION,
        tagline="Pre-hearing sufficiency audit, checklist verification, and action approvals",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python backend with FastAPI and React/ReactFlow interactive readiness graph.",
        api_prefix="/api/modules/hearing-readiness",
        ui_route="/modules/hearing-readiness",
        has_custom_frontend=True,
        features=[
            "Stage-specific readiness score calculation",
            "Missing document / unserved notice detection",
            "Human action approval workflow",
            "Hearing docket compiler"
        ]
    ),
    ModuleMetadata(
        module_id="mod-02-case-continuity",
        number=2,
        name="Case Continuity Engine",
        slug="case-continuity",
        category=ModuleCategory.PROCEDURAL_GOVERNANCE,
        tagline="Multi-counsel handoff resilience, timeline conflicts, and institutional memory ledger",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full backend verified. Python FastAPI engine with conflict resolution and health score metrics.",
        api_prefix="/api/modules/case-continuity",
        ui_route="/modules/case-continuity",
        has_custom_frontend=False,
        features=[
            "Handoff integrity analysis",
            "Timeline discrepancy and conflict detection",
            "Order vs pleading discrepancy auditor",
            "Continuity health index"
        ]
    ),
    ModuleMetadata(
        module_id="mod-03-case-bottleneck",
        number=3,
        name="Case Bottleneck Engine",
        slug="case-bottleneck",
        category=ModuleCategory.CASE_ACCELERATION,
        tagline="Root-cause delay diagnosis, systemic blockage isolation, and remedial action tracking",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python FastAPI backend with React dashboard.",
        api_prefix="/api/modules/case-bottleneck",
        ui_route="/modules/case-bottleneck",
        has_custom_frontend=True,
        features=[
            "Procedural stage duration benchmarking",
            "Service-of-summons delay identification",
            "Root-cause diagnostic classification",
            "Remedial action plan generation"
        ]
    ),
    ModuleMetadata(
        module_id="mod-04-legal-aid-handoff",
        number=4,
        name="Legal-Aid Handoff Engine",
        slug="legal-aid-handoff",
        category=ModuleCategory.RIGHTS_PROTECTION,
        tagline="Seamless case transfer to legal aid counsel with fact matrix and briefing briefs",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full backend verified. Python FastAPI engine with command center and document intake.",
        api_prefix="/api/modules/legal-aid-handoff",
        ui_route="/modules/legal-aid-handoff",
        has_custom_frontend=False,
        features=[
            "Standardized legal-aid intake dossier",
            "Extracted fact matrix and timeline",
            "Document indexation with admissibility tags",
            "Pro-bono counsel transition briefing"
        ]
    ),
    ModuleMetadata(
        module_id="mod-05-procedural-obligation",
        number=5,
        name="Procedural Obligation Engine",
        slug="procedural-obligation",
        category=ModuleCategory.PROCEDURAL_GOVERNANCE,
        tagline="Strict WHO/WHAT/LOSS/SIGN statutory compliance & irreversible exposure triage",
        status=ModuleHealthStatus.PARTIAL,
        notes="PARTIAL / SECTION 1 PRESENT. Grounded in authoritative UNWIND settle/obligation engine and procedural contracts.",
        api_prefix="/api/modules/procedural-obligation",
        ui_route="/modules/procedural-obligation",
        has_custom_frontend=False,
        features=[
            "WHO: Counterparties told invalidated claims",
            "WHAT: Reversible remedial actions list",
            "LOSS: Irreversible exposure range analysis",
            "SIGN: Human legal gate approver requirement"
        ]
    ),
    ModuleMetadata(
        module_id="mod-06-evidence-dependency",
        number=6,
        name="Evidence Dependency Engine",
        slug="evidence-dependency",
        category=ModuleCategory.EVIDENCE_REASONING,
        tagline="Directed acyclic graph (DAG) of claims, evidence linkages, proof chains, and vulnerability nodes",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python backend with React/ReactFlow visual graph and coverage analysis.",
        api_prefix="/api/modules/evidence-dependency",
        ui_route="/modules/evidence-dependency",
        has_custom_frontend=True,
        features=[
            "Bipartite Claim-Evidence DAG visualization",
            "Critical single-point-of-failure claim detector",
            "Uncorroborated assertion radar",
            "Document evidentiary weight score"
        ]
    ),
    ModuleMetadata(
        module_id="mod-07-undertrial-liberty",
        number=7,
        name="Undertrial Liberty Sentinel",
        slug="undertrial-liberty",
        category=ModuleCategory.RIGHTS_PROTECTION,
        tagline="Statutory detention monitoring under Section 479 BNSS / 436A CrPC and bail eligibility audits",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python FastAPI backend with React/ReactFlow bail review queue.",
        api_prefix="/api/modules/undertrial-liberty",
        ui_route="/modules/undertrial-liberty",
        has_custom_frontend=True,
        features=[
            "Detention duration vs maximum sentence calculation",
            "First-time offender 1/3rd detention threshold alert",
            "Mandatory statutory bail entitlement tracker",
            "Bail application draft packet generator"
        ]
    ),
    ModuleMetadata(
        module_id="mod-08-registry-defect",
        number=8,
        name="Registry Defect Engine",
        slug="registry-defect",
        category=ModuleCategory.PROCEDURAL_GOVERNANCE,
        tagline="Automated scrutiny defect detection, court rule validation, and curative suggestion generation",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python backend with React/xyflow visual defect tree.",
        api_prefix="/api/modules/registry-defect",
        ui_route="/modules/registry-defect",
        has_custom_frontend=True,
        features=[
            "High Court & District Court registry rules check",
            "Defect impact blast radius calculation",
            "Suggested curative refiling steps",
            "Defect refiling time-window monitor"
        ]
    ),
    ModuleMetadata(
        module_id="mod-09-case-crash-test",
        number=9,
        name="Case Crash Test / Resilience Lab",
        slug="case-crash-test",
        category=ModuleCategory.EVIDENCE_REASONING,
        tagline="Adversarial stress-testing of legal arguments, witness cross-examination vulnerabilities, and structural collapse simulation",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python FastAPI backend with React/ReactFlow interactive stress-test sandbox.",
        api_prefix="/api/modules/case-crash-test",
        ui_route="/modules/case-crash-test",
        has_custom_frontend=True,
        features=[
            "Adversarial counter-argument simulator",
            "Witness testimony contradiction detector",
            "Cascading claim failure simulation",
            "Resilience index score"
        ]
    ),
    ModuleMetadata(
        module_id="mod-10-spark-personal-os",
        number=10,
        name="Spark Personal OS",
        slug="spark-personal-os",
        category=ModuleCategory.PRACTICE_AUTOMATION,
        tagline="Personal legal dashboard: daily briefing digests, custom saved views, change notifications, and triage queue",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full stack verified. Python FastAPI backend with React/Tailwind personal view manager (Section 1 verified).",
        api_prefix="/api/modules/spark-personal-os",
        ui_route="/modules/spark-personal-os",
        has_custom_frontend=True,
        features=[
            "Personalized case morning digest",
            "Cross-case attention & notification feed",
            "Custom query saved-views",
            "Audit trail and change ledger"
        ]
    ),
    ModuleMetadata(
        module_id="mod-11-spark-deadline-guardian",
        number=11,
        name="Spark Deadline Guardian",
        slug="spark-deadline-guardian",
        category=ModuleCategory.PROCEDURAL_GOVERNANCE,
        tagline="Statutory limitation calculator, court holiday calendar reconciliation, and critical deadline escalation alerts",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full backend verified. Python FastAPI engine with limitation rules and text ingestion (Section 1 verified).",
        api_prefix="/api/modules/spark-deadline-guardian",
        ui_route="/modules/spark-deadline-guardian",
        has_custom_frontend=False,
        features=[
            "Limitation Act statutory period calculator",
            "Filing deadline countdown & threshold triggers",
            "Multi-channel escalation alerts",
            "Court calendar and vacation adjustments"
        ]
    ),
    ModuleMetadata(
        module_id="mod-12-spark-workflow-autopilot",
        number=12,
        name="Spark Workflow Autopilot",
        slug="spark-workflow-autopilot",
        category=ModuleCategory.PRACTICE_AUTOMATION,
        tagline="Procedural standard operating procedure (SOP) runner, multi-stage task automation, and human sign-off gates",
        status=ModuleHealthStatus.HEALTHY,
        notes="Full backend verified. Python FastAPI engine with workflow templates and task execution.",
        api_prefix="/api/modules/spark-workflow-autopilot",
        ui_route="/modules/spark-workflow-autopilot",
        has_custom_frontend=False,
        features=[
            "Automated procedural SOP templates",
            "Multi-stage task dependency coordinator",
            "UNWIND human authorization gate",
            "Workflow execution audit logging"
        ]
    )
]


class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, ModuleMetadata] = {m.module_id: m for m in REGISTRY}

    def list_all(self) -> List[ModuleMetadata]:
        return list(self._modules.values())

    def get_by_id(self, module_id: str) -> Optional[ModuleMetadata]:
        return self._modules.get(module_id)

    def get_by_slug(self, slug: str) -> Optional[ModuleMetadata]:
        for m in self._modules.values():
            if m.slug == slug:
                return m
        return None

    def get_by_number(self, num: int) -> Optional[ModuleMetadata]:
        for m in self._modules.values():
            if m.number == num:
                return m
        return None


module_registry = ModuleRegistry()
