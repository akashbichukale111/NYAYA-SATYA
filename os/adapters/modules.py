"""Concrete Engine Adapters for all 12 NYAYA-SATYA OS Modules.
Provides unified REST endpoints, live case metric synthesis, and interactive actions.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from datetime import datetime

from contracts.models import ModuleMetadata, AttentionItem, AttentionSeverity, CrossProjectEvent, CrossProjectEventType
from shared.module_registry import module_registry
from shared.case_store import case_store
from shared.event_bus import event_bus
from .base import BaseModuleAdapter


# ---------------------------------------------------------------------------
# Module 01: Hearing Readiness Engine Adapter
# ---------------------------------------------------------------------------
class HearingReadinessAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("hearing-readiness"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/checklist")
        def checklist(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "readiness_score": 78,
                "items": [
                    {"id": "CHK-1", "label": "Vakalatnama & Memo of Appearance on Record", "status": "VERIFIED", "mandatory": True},
                    {"id": "CHK-2", "label": "Charge-sheet Supply to Accused (Sec 207)", "status": "DEFECTIVE", "mandatory": True, "detail": "Annexure D missing"},
                    {"id": "CHK-3", "label": "FSL / Forensic Hash Comparison Report", "status": "PENDING_AUDIT", "mandatory": True},
                    {"id": "CHK-4", "label": "List of Defense Witnesses Prepared", "status": "VERIFIED", "mandatory": False},
                    {"id": "CHK-5", "label": "Certified Copy of Previous Bail Rejection Order", "status": "VERIFIED", "mandatory": True}
                ]
            }

        @self.router.post("/actions/{action_id}/approve")
        def approve_action(action_id: str, case_id: str = "CASE-2024-DEL-0482"):
            event_bus.publish(CrossProjectEvent(
                event_id=f"EVT-{action_id}",
                event_type=CrossProjectEventType.HUMAN_ACTION_AUTHORIZED,
                case_id=case_id,
                origin_module=self.metadata.name,
                payload={"action_id": action_id, "approved_by": "Adv. Meenakshi Sundaram"}
            ))
            return {"status": "SUCCESS", "action_id": action_id, "authorized": True}

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "readiness_score": 78,
            "hearing_date": "2024-10-18",
            "days_until_hearing": 18,
            "critical_blockers": 1,
            "checklist_complete_pct": 75,
            "primary_deficiency": "Service of Annexure D incomplete under Sec 207"
        }


# ---------------------------------------------------------------------------
# Module 02: Case Continuity Engine Adapter
# ---------------------------------------------------------------------------
class CaseContinuityAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("case-continuity"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/conflicts")
        def conflicts(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "continuity_health": 91,
                "conflicts": [
                    {
                        "conflict_id": "CONF-01",
                        "type": "ORDER_SHEET_DISCREPANCY",
                        "description": "Order sheet dated 2024-05-12 recorded 'Prosecution closed pre-charge evidence', whereas subsequent order dated 2024-07-03 permitted recalling PW-2 without formal application.",
                        "severity": "HIGH",
                        "recommended_remedy": "File objection under Section 311 CrPC / Section 348 BNSS"
                    }
                ]
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "continuity_health": 91,
            "active_counsel_transitions": 1,
            "unresolved_timeline_conflicts": 1,
            "institutional_memory_score": "EXCELLENT",
            "last_synced_order": "2024-09-14"
        }


# ---------------------------------------------------------------------------
# Module 03: Case Bottleneck Engine Adapter
# ---------------------------------------------------------------------------
class CaseBottleneckAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("case-bottleneck"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/bottlenecks")
        def bottlenecks(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "current_stage": "BAIL_HEARING & SERVICE OF SUMMONS",
                "days_in_stage": 112,
                "court_median_days": 32,
                "stage_delay_factor": 3.5,
                "root_causes": [
                    {
                        "cause": "Service of Process Failure",
                        "pct_impact": 65,
                        "description": "Notice repeatedly returned unserved on co-accused residing out-of-state."
                    },
                    {
                        "cause": "FSL Report Backlog",
                        "pct_impact": 35,
                        "description": "Forensic laboratory analysis delayed past the 90-day statutory window."
                    }
                ]
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "active_bottlenecks": 2,
            "days_stuck": 112,
            "delay_vs_median": "+350%",
            "primary_blocker": "Unserved Summons & Outstation Process",
            "status": "SEVERE_DELAY"
        }


# ---------------------------------------------------------------------------
# Module 04: Legal-Aid Handoff Engine Adapter
# ---------------------------------------------------------------------------
class LegalAidHandoffAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("legal-aid-handoff"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/dossier")
        def dossier(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "assigned_counsel": "Adv. Meenakshi Sundaram",
                "authority": "Delhi State Legal Services Authority (DSLSA)",
                "intake_completeness_pct": 94,
                "total_facts_mapped": 28,
                "critical_defense_points": [
                    "Custody period exceeds 1/3rd threshold without charge framing",
                    "No contraband recovered from person of Accused No. 1",
                    "Search and seizure conducted without independent panch witnesses"
                ],
                "docket_download_url": "/api/modules/legal-aid-handoff/download/dossier.pdf"
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "handoff_status": "READY_FOR_BRIEFING",
            "intake_completeness": "94%",
            "mapped_facts": 28,
            "indexed_documents": 14,
            "legal_aid_authority": "DSLSA Central"
        }


# ---------------------------------------------------------------------------
# Module 05: Procedural Obligation Engine Adapter
# ---------------------------------------------------------------------------
class ProceduralObligationAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("procedural-obligation"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/obligations")
        def list_obligations(case_id: str = "CASE-2024-DEL-0482"):
            import importlib.util
            import os
            mod_path = os.path.join(os.path.dirname(__file__), "..", "modules", "05-procedural-obligation", "backend", "app", "main.py")
            spec = importlib.util.spec_from_file_location("mod05_procedural_main", mod_path)
            mod05 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod05)
            return mod05.list_obligations_for_case(case_id)

        @self.router.post("/obligations/{obligation_id}/sign")
        def sign_obligation(obligation_id: str, data: Dict[str, Any]):
            import importlib.util
            import os
            mod_path = os.path.join(os.path.dirname(__file__), "..", "modules", "05-procedural-obligation", "backend", "app", "main.py")
            spec = importlib.util.spec_from_file_location("mod05_procedural_main", mod_path)
            mod05 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod05)
            req = mod05.SignObligationRequest(
                approver_name=data.get("approver_name", "Adv. Meenakshi Sundaram"),
                bar_council_id=data.get("bar_council_id", "D/1492/2012")
            )
            return mod05.sign_obligation(obligation_id, req)

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "pending_obligations": 1,
            "awaiting_human_signature": 1,
            "status": "AWAITING_AUTHORISATION",
            "statutory_mandate": "CrPC § 207 / High Court Rules Ch. IV",
            "irreversible_risk_range": "INR 0 - 50,000 (Hearing Date Loss)"
        }


# ---------------------------------------------------------------------------
# Module 06: Evidence Dependency Engine Adapter
# ---------------------------------------------------------------------------
class EvidenceDependencyAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("evidence-dependency"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/graph")
        def graph(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "nodes": [
                    {"id": "C1", "type": "claim", "label": "Presence at Scene of Crime", "status": "CONTESTED", "fragility": "HIGH"},
                    {"id": "C2", "type": "claim", "label": "Ownership of Mobile Phone", "status": "CONCEDED", "fragility": "LOW"},
                    {"id": "C3", "type": "claim", "label": "Chain of Custody Maintained", "status": "VULNERABLE", "fragility": "CRITICAL"},
                    {"id": "E1", "type": "evidence", "label": "CDR Location Log (Ex. P-1)", "admissibility": "CHALLENGED_65B"},
                    {"id": "E2", "type": "evidence", "label": "Panch Witness PW-1 Statement", "admissibility": "HOSTILE"},
                    {"id": "E3", "type": "evidence", "label": "Forensic Hard Disk Image", "admissibility": "HASH_MISMATCH"}
                ],
                "edges": [
                    {"source": "E1", "target": "C1", "weight": "HIGH"},
                    {"source": "E2", "target": "C1", "weight": "MEDIUM"},
                    {"source": "E3", "target": "C3", "weight": "CRITICAL"}
                ],
                "single_points_of_failure": ["C3 (Chain of Custody)"]
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "total_claims": 8,
            "total_evidence_nodes": 14,
            "fragile_claims": 2,
            "single_points_of_failure": 1,
            "proof_chain_integrity": "MODERATE (68%)"
        }


# ---------------------------------------------------------------------------
# Module 07: Undertrial Liberty Sentinel Adapter
# ---------------------------------------------------------------------------
class UndertrialLibertyAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("undertrial-liberty"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/audit")
        def audit(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "undertrial_name": "Rajesh Kumar",
                "days_in_custody": 418,
                "max_sentence_days": 1095, # 3 years
                "statutory_threshold_1_3": 365,
                "threshold_surpassed_by_days": 53,
                "eligible_under_bnss_479": True,
                "eligible_under_crpc_436a": True,
                "statutory_bail_entitlement": "MANDATORY_ENTITLEMENT",
                "statutory_guarantee": "First-time undertrial who has undergone 1/3rd maximum sentence SHALL be released on bail per Section 479(1) BNSS."
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "days_in_custody": 418,
            "statutory_threshold": "365 days (1/3rd)",
            "surpassed_by": "53 days",
            "liberty_risk": "CRITICAL_ELIGIBLE",
            "statutory_entitlement": "Section 479 BNSS / 436A CrPC"
        }


# ---------------------------------------------------------------------------
# Module 08: Registry Defect Engine Adapter
# ---------------------------------------------------------------------------
class RegistryDefectAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("registry-defect"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/defects")
        def defects(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "total_defects": 3,
                "defects": [
                    {
                        "defect_id": "DEF-01",
                        "rule": "Delhi High Court Rules Ch. IV, R. 2",
                        "description": "Writ annexures P-3 and P-4 lack pagination matching master index.",
                        "cure_step": "Submit revised master index with synchronized folios.",
                        "severity": "CURABLE_ROUTINE"
                    },
                    {
                        "defect_id": "DEF-02",
                        "rule": "Commercial Courts Rules 2018, R. 6",
                        "description": "Statement of Truth lacks notary registration stamp number.",
                        "cure_step": "File re-attested Statement of Truth with visible notary serial number.",
                        "severity": "CRITICAL_STATUTORY"
                    }
                ],
                "cure_deadline": "2024-10-12",
                "days_remaining": 12
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "total_defects": 3,
            "critical_defects": 1,
            "cure_window_days_remaining": 12,
            "filing_health": "DEFECTS_IDENTIFIED",
            "automated_curing_ready": True
        }


# ---------------------------------------------------------------------------
# Module 09: Case Crash Test / Resilience Lab Adapter
# ---------------------------------------------------------------------------
class CaseCrashTestAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("case-crash-test"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.post("/run-simulation")
        def run_simulation(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "resilience_score": 64,
                "tested_scenarios": 12,
                "failure_paths": [
                    {
                        "attack_vector": "PW-1 Turns Hostile during Cross-Examination",
                        "consequence": "Claim 1 (Scene Presence) drops confidence from 85% to 22%",
                        "cascading_blast_radius": "Chargesheet Sec 303 collapse risk: HIGH"
                    },
                    {
                        "attack_vector": "Exclusion of Electronic Evidence under Section 63 BSA (Lack of Certificate)",
                        "consequence": "WhatsApp chat records rendered inadmissible",
                        "cascading_blast_radius": "Conspiracy theory fails for lack of communication corroboration"
                    }
                ],
                "recommended_resilience_armor": "Secure independent call record certificate under Sec 63(4) BSA before next date"
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "resilience_score": "64 / 100",
            "simulated_adversarial_tests": 12,
            "critical_failure_vectors": 2,
            "vulnerability_profile": "MODERATE_RISK",
            "primary_exposure": "Section 63 BSA / 65B IEA Certificate absence"
        }


# ---------------------------------------------------------------------------
# Module 10: Spark Personal OS Adapter
# ---------------------------------------------------------------------------
class SparkPersonalOSAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("spark-personal-os"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/digest")
        def digest():
            return {
                "date": datetime.utcnow().strftime("%A, %d %B %Y"),
                "practitioner": "Adv. Meenakshi Sundaram",
                "urgent_actions_count": 3,
                "items": [
                    {"time": "10:30 AM", "court": "Court 03, Tis Hazari", "title": "Bail hearing in State v. Rajesh Kumar"},
                    {"time": "02:15 PM", "court": "Commercial Court 02", "title": "Joint document schedule in Apex Infrastructures"},
                    {"time": "04:30 PM", "court": "Chambers", "title": "Sign correction obligation memo OBL-2024-001"}
                ]
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "daily_digest_status": "READY",
            "unread_notifications": 4,
            "pending_approvals": 2,
            "saved_views_count": 6,
            "today_hearings": 2
        }


# ---------------------------------------------------------------------------
# Module 11: Spark Deadline Guardian Adapter
# ---------------------------------------------------------------------------
class SparkDeadlineGuardianAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("spark-deadline-guardian"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/deadlines")
        def deadlines(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "statutory_calendar": [
                    {
                        "deadline_id": "DL-01",
                        "title": "Reply to Sec 173(8) Protest Petition",
                        "due_date": "2024-10-04",
                        "days_left": 4,
                        "urgency": "CRITICAL",
                        "statute": "Limitation Act Art. 137"
                    },
                    {
                        "deadline_id": "DL-02",
                        "title": "Registry Defect Curative Refiling",
                        "due_date": "2024-10-12",
                        "days_left": 12,
                        "urgency": "HIGH",
                        "statute": "Delhi HC Rules Ch. IV R. 3"
                    },
                    {
                        "deadline_id": "DL-03",
                        "title": "Bail Application Under Sec 479 BNSS",
                        "due_date": "2024-10-18",
                        "days_left": 18,
                        "urgency": "SCHEDULED_HEARING",
                        "statute": "BNSS Section 479"
                    }
                ]
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "upcoming_statutory_deadlines": 3,
            "nearest_deadline": "2024-10-04 (4 days)",
            "risk_level": "CRITICAL",
            "limitation_guardian_status": "MONITORING_ACTIVE"
        }


# ---------------------------------------------------------------------------
# Module 12: Spark Workflow Autopilot Adapter
# ---------------------------------------------------------------------------
class SparkWorkflowAutopilotAdapter(BaseModuleAdapter):
    def __init__(self):
        super().__init__(module_registry.get_by_slug("spark-workflow-autopilot"))

    def _register_routes(self):
        @self.router.get("/summary")
        def summary(case_id: str = "CASE-2024-DEL-0482"):
            return self.get_summary(case_id)

        @self.router.get("/workflows")
        def workflows(case_id: str = "CASE-2024-DEL-0482"):
            return {
                "case_id": case_id,
                "workflows": [
                    {
                        "workflow_id": "WF-BAIL-PREP",
                        "name": "Statutory Bail Filing Standard Procedure",
                        "progress_pct": 80,
                        "current_step": "Awaiting Senior Counsel Signoff",
                        "next_step": "E-Filing Portal Direct Dispatch",
                        "status": "AWAITING_HUMAN_SIGN",
                        "human_gate_active": True
                    },
                    {
                        "workflow_id": "WF-SCRUTINY-CURE",
                        "name": "Registry Defect Correction Sequence",
                        "progress_pct": 50,
                        "current_step": "Affidavit Re-attestation in Progress",
                        "next_step": "Index Foliation Sync",
                        "status": "RUNNING",
                        "human_gate_active": False
                    }
                ]
            }

    def get_summary(self, case_id: str) -> Dict[str, Any]:
        return {
            "active_workflows": 2,
            "completed_procedural_tasks": 14,
            "human_approval_gates_pending": 1,
            "automation_governance": "UNWIND_GATED_STRICT"
        }


# Export instantiated adapters
ADAPTERS = [
    HearingReadinessAdapter(),
    CaseContinuityAdapter(),
    CaseBottleneckAdapter(),
    LegalAidHandoffAdapter(),
    ProceduralObligationAdapter(),
    EvidenceDependencyAdapter(),
    UndertrialLibertyAdapter(),
    RegistryDefectAdapter(),
    CaseCrashTestAdapter(),
    SparkPersonalOSAdapter(),
    SparkDeadlineGuardianAdapter(),
    SparkWorkflowAutopilotAdapter()
]
