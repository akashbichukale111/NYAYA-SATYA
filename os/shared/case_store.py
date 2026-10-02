"""Global Case Store and Context Manager for NYAYA-SATYA OS.
Maintains state across all 13 application experiences, enforces simulation isolation,
and provides deeply structured Case Digital Twin representations.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from contracts.models import CaseContext, JurisdictionalDomain, ProceduralStage


# Initial demonstration cases reflecting realistic Indian & Global jurisdictional scenarios
DEFAULT_CASES: List[CaseContext] = [
    CaseContext(
        case_id="CASE-2024-DEL-0482",
        title="State (NCT of Delhi) v. Rajesh Kumar & Anr.",
        court="Tis Hazari District Court, Central Delhi",
        jurisdiction=JurisdictionalDomain.CRIMINAL,
        stage=ProceduralStage.BAIL_HEARING,
        statute="Bhartiya Nyaya Sanhita (BNS) §§ 303, 318 / CrPC § 437",
        filing_date="2023-11-20",
        next_hearing="2024-10-18",
        lead_counsel="Adv. Meenakshi Sundaram (Legal Aid Appointed)",
        undertrial_in_custody=True,
        custody_start_date="2023-08-10",
        human_authorized=False,
        summary="Accused in judicial custody for over 14 months without framing of charges. Multiple procedural defects in charge sheet service. Bail application pending under Section 479 BNSS / 436A CrPC.",
        tags=["Undertrial", "Sec 479 BNSS", "Defect in Service", "Bail Urgent"],
        parties=[
            {"role": "Prosecution", "name": "State (NCT of Delhi)", "counsel": "Alok Sharma (APP)"},
            {"role": "Accused No. 1", "name": "Rajesh Kumar", "custody_status": "Judicial Custody (Tihar Jail No. 4)", "counsel": "Adv. Meenakshi Sundaram"}
        ],
        documents=[
            {"doc_id": "DOC-01", "title": "FIR No. 412/2023", "filed_on": "2023-08-09", "pages": 4, "status": "VERIFIED"},
            {"doc_id": "DOC-02", "title": "Police Report u/s 173 CrPC", "filed_on": "2023-11-20", "pages": 142, "status": "DEFECTIVE_SERVICE"},
            {"doc_id": "DOC-03", "title": "Regular Bail Application u/s 479 BNSS", "filed_on": "2024-09-28", "pages": 18, "status": "PENDING_HEARING"}
        ],
        evidence=[
            {
                "id": "E-01",
                "label": "Seizure Panchnama of Stolen Article",
                "type": "DOCUMENTARY",
                "status": "CONTESTED",
                "materiality": "STRUCTURALLY_MATERIAL",
                "notes": "Both independent panch witnesses have submitted affidavits alleging signatures obtained under duress at police station."
            },
            {
                "id": "E-02",
                "label": "CCTV Footage CD (Market Entrance)",
                "type": "ELECTRONIC",
                "status": "FRAGILE",
                "materiality": "STRUCTURALLY_MATERIAL",
                "notes": "Lacks mandatory Section 63 BSA / 65B Indian Evidence Act certificate from system administrator."
            },
            {
                "id": "E-03",
                "label": "Call Detail Records (CDR) of Mobile No. 9811XXXXXX",
                "type": "ELECTRONIC",
                "status": "EXCULPATORY",
                "materiality": "STRUCTURALLY_MATERIAL",
                "notes": "Cell tower radius pinpoints device at Pitampura (14 km from alleged scene of occurrence at 21:30)."
            },
            {
                "id": "E-04",
                "label": "Arrest Memo & Medical Examination",
                "type": "PROCEDURAL",
                "status": "VERIFIED",
                "materiality": "STRUCTURALLY_MINOR",
                "notes": "Recorded 2023-08-10 03:30 AM at Daryaganj PS."
            }
        ],
        claims=[
            {
                "claim_id": "CLM-01",
                "statement": "Accused was physically present at Chandni Chowk incident site at 21:30 hrs.",
                "status": "CONTRADICTED",
                "supporting_evidence": ["E-01"],
                "contradicting_evidence": ["E-03"]
            },
            {
                "claim_id": "CLM-02",
                "statement": "Recovery of stolen currency from personal search of accused.",
                "status": "CONTESTED",
                "supporting_evidence": ["E-01"],
                "contradicting_evidence": []
            },
            {
                "claim_id": "CLM-03",
                "statement": "Accused has undergone > 1/3rd maximum statutory term as a first-time undertrial.",
                "status": "SUPPORTED",
                "supporting_evidence": ["E-04"],
                "contradicting_evidence": []
            }
        ],
        issues=[
            {"issue_id": "ISS-01", "text": "Whether seizure is vitiated by tainted panchnama procedures?", "status": "ACTIVE"},
            {"issue_id": "ISS-02", "text": "Whether electronic evidence is inadmissible without Section 63 BSA certificate?", "status": "ACTIVE"},
            {"issue_id": "ISS-03", "text": "Whether accused is entitled to statutory release on bail under Section 479 BNSS?", "status": "URGENT_HEARING"}
        ],
        events=[
            {"event_id": "EVT-01", "date": "2023-08-09", "label": "Alleged incident at Chandni Chowk"},
            {"event_id": "EVT-02", "date": "2023-08-10", "label": "Formal arrest of Rajesh Kumar"},
            {"event_id": "EVT-03", "date": "2023-11-20", "label": "Charge sheet filed by Investigating Officer"},
            {"event_id": "EVT-04", "date": "2024-08-10", "label": "One year custody milestone reached (1/3rd threshold crossed)"}
        ],
        timeline=[
            {"time": "2023-08-10", "title": "Arrest & Remand", "detail": "Sent to judicial custody (Tihar Jail)"},
            {"time": "2023-11-20", "title": "Charge Sheet Filed", "detail": "Scrutiny marked defective in service"},
            {"time": "2024-08-10", "title": "Statutory Bail Threshold", "detail": "Surpassed 12 months in pre-trial detention"}
        ],
        hearings=[
            {"hearing_id": "HRG-01", "date": "2024-10-18", "court_room": "Court No. 12, Tis Hazari", "purpose": "Arguments on Section 479 BNSS Bail Application", "status": "SCHEDULED"}
        ],
        orders=[
            {"order_id": "ORD-01", "date": "2024-09-12", "judge": "Sh. R.K. Yadav, ASJ", "text": "Notice issued on bail application. Investigating officer directed to file status report by 18-10-2024."}
        ],
        obligations=[
            {
                "obligation_id": "OBL-01",
                "statutory_ref": "Bhartiya Nagarik Suraksha Sanhita (BNSS) § 230 / CrPC § 207",
                "who": "Investigating Officer / Prosecution",
                "what": "Supply complete copies of police report and electronic records to accused without cost",
                "loss": "Proceedings vitiated; framing of charges cannot commence",
                "sign": "Verified endorsement on court order sheet",
                "status": "PARTIALLY_SATISFIED"
            }
        ],
        deadlines=[
            {"deadline_id": "D-01", "due_date": "2024-10-15", "description": "Prosecution status report on custody certificate", "status": "PENDING"},
            {"deadline_id": "D-02", "due_date": "2024-10-17", "description": "Submission of Section 63 BSA certificate compliance", "status": "URGENT"}
        ],
        dependencies=[
            {"source": "OBL-01", "target": "ISS-01", "type": "PREREQUISITE", "description": "Supply of documents must precede framing of charges"}
        ],
        contradictions=[
            {
                "id": "CONTR-01",
                "severity": "CRITICAL",
                "title": "Alibi Contradiction in Prosecution Narrative",
                "description": "Seizure memo (E-01) alleges personal recovery at Chandni Chowk at 21:30 hrs, whereas official CDR cell-tower metadata (E-03) places accused at Pitampura 14 km away."
            }
        ],
        bottlenecks=[
            {
                "id": "BTN-01",
                "type": "FORENSIC_DELAY",
                "description": "FSL report on electronic storage device pending for 11 months",
                "impact": "Blocks framing of charges and final argument scheduling"
            }
        ],
        registry_defects=[
            {
                "defect_id": "DEF-01",
                "category": "SERVICE_DEFECT",
                "description": "Legible copies of Annexures 4 & 7 not furnished to Legal Aid counsel",
                "is_curable": True
            }
        ],
        liberty_events=[
            {
                "type": "CUSTODY_THRESHOLD",
                "days_in_custody": 428,
                "maximum_sentence_days": 1095,
                "fraction_served": 0.39,
                "eligible_under_sec_479": True,
                "notes": "Accused has served 39% of maximum sentence without trial commencing; qualifies for mandatory bail under Sec 479(1) First Proviso BNSS."
            }
        ],
        workflows=[
            {"name": "Undertrial Bail Fast-Track", "stage": "Pleading Complete", "status": "Awaiting Arguments"}
        ],
        actions=[
            {"id": "ACT-01", "title": "File Formal Memo for Sec 479 Bail Release", "status": "PENDING_HUMAN_GATE", "requires_signoff": True}
        ],
        reviews=[
            {"review_id": "REV-01", "engine": "TARKA-VYUH", "fragility_score": "78% (HIGH)", "achilles_heel": "Electronic Evidence CD admissibility (Missing 63 BSA / 65B cert)"}
        ],
        approvals=[
            {"approval_id": "APP-01", "action_id": "ACT-01", "status": "PENDING_COUNSEL", "approver": "Adv. Meenakshi Sundaram"}
        ],
        verification_state={"integrity_status": "INTACT", "twin_version": 4, "last_cross_check": "2024-10-01T20:00:00Z"},
        simulations=[
            {"sim_id": "SIM-01", "type": "COUNTERFACTUAL_ISOLATED", "target": "E-01", "impact": "Claim CLM-01 collapses; Prosecution case collapses by 72%"}
        ],
        provenance=[
            {"entity": "E-01", "sha256": "3fa85f647f3b4d27e2838b25f2563077", "chain_of_custody": "PS Daryaganj Malkhana -> Court Nazarat"}
        ],
        audit_records=[
            {"timestamp": "2024-10-01T12:00:00Z", "action": "CASE_INGESTION", "actor": "SYSTEM_CORE"}
        ],
        governance_state={"status": "GOVERNANCE_ACTIVE", "gate_open": False, "required_roles": ["LEAD_COUNSEL"]}
    ),
    CaseContext(
        case_id="CASE-2023-BOM-1109",
        title="Apex Infrastructures Ltd. v. Mumbai Port Trust",
        court="Bombay High Court (Commercial Division)",
        jurisdiction=JurisdictionalDomain.COMMERCIAL,
        stage=ProceduralStage.ARGUMENTS,
        statute="Commercial Courts Act 2015 / Arbitration & Conciliation Act § 34",
        filing_date="2023-04-12",
        next_hearing="2024-11-05",
        lead_counsel="Senior Adv. Fali V. Nariman Chambers",
        undertrial_in_custody=False,
        custody_start_date=None,
        human_authorized=True,
        summary="Challenge to arbitral award regarding port expansion works. Critical evidentiary bottleneck on force majeure certificate admissibility and computation of liquidated damages.",
        tags=["Commercial", "Arbitration § 34", "High Stake", "Evidence Heavy"],
        parties=[
            {"role": "Petitioner", "name": "Apex Infrastructures Ltd.", "counsel": "Senior Adv. Chambers"},
            {"role": "Respondent", "name": "Board of Trustees of Mumbai Port Trust", "counsel": "Solicitor General Office"}
        ],
        documents=[
            {"doc_id": "DOC-10", "title": "Petition under Section 34 Arbitration Act", "pages": 84, "status": "VERIFIED"},
            {"doc_id": "DOC-11", "title": "Arbitral Award by 3-Member Tribunal", "pages": 240, "status": "IMPUGNED"}
        ],
        evidence=[
            {"id": "E-10", "label": "Arbitral Award dated 2023-01-15", "type": "DOCUMENTARY", "status": "VERIFIED", "materiality": "STRUCTURALLY_MATERIAL"},
            {"id": "E-11", "label": "Meteorological Department Monsoon Surge Bulletin", "type": "DOCUMENTARY", "status": "VERIFIED", "materiality": "STRUCTURALLY_MATERIAL"},
            {"id": "E-12", "label": "Independent Engineer Delay Audit Report", "type": "EXPERT_REPORT", "status": "CONTESTED", "materiality": "STRUCTURALLY_MATERIAL"}
        ],
        claims=[
            {"claim_id": "CLM-10", "statement": "Arbitral award suffers from patent illegality on the face of the award.", "status": "CONTESTED"},
            {"claim_id": "CLM-11", "statement": "Liquidated damages awarded without proof of actual loss contrary to Kailash Nath precedent.", "status": "SUPPORTED"}
        ],
        issues=[
            {"issue_id": "ISS-10", "text": "Whether patent illegality ground is made out within limits of Ssangyong Engineering?", "status": "ACTIVE"},
            {"issue_id": "ISS-11", "text": "Whether liquidated damages were pre-estimated genuine loss?", "status": "ACTIVE"}
        ],
        events=[
            {"event_id": "EVT-10", "date": "2023-01-15", "label": "Arbitral Award rendered"},
            {"event_id": "EVT-11", "date": "2023-04-12", "label": "Section 34 Petition instituted in High Court"}
        ],
        timeline=[
            {"time": "2023-01-15", "title": "Tribunal Award", "detail": "Awarded ₹48.2 Cr damages against Petitioner"},
            {"time": "2023-04-12", "title": "Commercial Petition", "detail": "Stay granted subject to 50% deposit"}
        ],
        hearings=[
            {"hearing_id": "HRG-10", "date": "2024-11-05", "court_room": "Court Room 37, Bombay HC", "purpose": "Final Oral Arguments", "status": "SCHEDULED"}
        ],
        orders=[
            {"order_id": "ORD-10", "date": "2023-05-18", "judge": "G.S. Patel J.", "text": "Ad-interim stay granted upon deposit of ₹24.1 Cr in registry."}
        ],
        obligations=[],
        deadlines=[
            {"deadline_id": "D-10", "due_date": "2024-11-01", "description": "Filing of convenience compilation & written submissions", "status": "PENDING"}
        ],
        dependencies=[],
        contradictions=[],
        bottlenecks=[
            {"id": "BTN-10", "type": "VOLUMINOUS_RECORD", "description": "Record comprises 4,200 pages across 12 volumes lacking cross-referenced digital bookmarks"}
        ],
        registry_defects=[],
        liberty_events=[],
        workflows=[],
        actions=[],
        reviews=[
            {"review_id": "REV-10", "engine": "TARKA-VYUH", "fragility_score": "34% (MODERATE)", "achilles_heel": "Contractual limitation clause interpretation"}
        ],
        approvals=[],
        verification_state={"integrity_status": "INTACT", "twin_version": 2},
        simulations=[],
        provenance=[],
        audit_records=[],
        governance_state={"status": "GOVERNANCE_ACTIVE", "gate_open": True}
    ),
    CaseContext(
        case_id="CASE-2024-KA-0077",
        title="Kaveri Farmers Welfare Trust v. State of Karnataka",
        court="High Court of Karnataka, Bengaluru",
        jurisdiction=JurisdictionalDomain.CONSTITUTIONAL,
        stage=ProceduralStage.FILING_DEFECT_SCRUTINY,
        statute="Constitution of India Art. 226 / Land Acquisition Act 2013",
        filing_date="2024-09-02",
        next_hearing="2024-10-25",
        lead_counsel="Adv. Roopa Shankar",
        undertrial_in_custody=False,
        custody_start_date=None,
        human_authorized=False,
        summary="Writ petition challenging fast-track environmental clearance. Registry scrutiny raised 4 curable defects regarding translated annexures and verification affidavits.",
        tags=["Writ Art. 226", "Registry Defect", "Limitation Risk"],
        parties=[
            {"role": "Petitioner", "name": "Kaveri Farmers Welfare Trust", "counsel": "Adv. Roopa Shankar"},
            {"role": "Respondent No. 1", "name": "State of Karnataka (Revenue Dept)", "counsel": "Government Advocate"}
        ],
        documents=[
            {"doc_id": "DOC-20", "title": "Writ Petition under Art. 226", "pages": 42, "status": "DEFECTS_RAISED"}
        ],
        evidence=[
            {"id": "E-20", "label": "State Gazette Notification (Kannada)", "type": "DOCUMENTARY", "status": "DEFECTIVE", "materiality": "STRUCTURALLY_MATERIAL", "notes": "Requires certified English translation as per HC Rules."}
        ],
        claims=[
            {"claim_id": "CLM-20", "statement": "Prior public consultation was bypassed in violation of Sec 41 RFCTLARR Act 2013.", "status": "SUPPORTED"}
        ],
        issues=[
            {"issue_id": "ISS-20", "text": "Whether environmental clearance is void ab initio for want of public notice?", "status": "PENDING_REGISTRATION"}
        ],
        events=[
            {"event_id": "EVT-20", "date": "2024-09-02", "label": "Petition e-filed through Karnataka HC portal"},
            {"event_id": "EVT-21", "date": "2024-09-06", "label": "Registry scrutiny checklist returned with 4 defects"}
        ],
        timeline=[
            {"time": "2024-09-02", "title": "E-Filing", "detail": "Assigned Diary No. 18921/2024"},
            {"time": "2024-09-06", "title": "Defects Notified", "detail": "7 days statutory cure window opened"}
        ],
        hearings=[],
        orders=[],
        obligations=[],
        deadlines=[
            {"deadline_id": "D-20", "due_date": "2024-10-20", "description": "Cure registry defects and re-file within limitation", "status": "CRITICAL_LIMITATION"}
        ],
        dependencies=[],
        contradictions=[],
        bottlenecks=[
            {"id": "BTN-20", "type": "REGISTRY_SCRUTINY_HOLD", "description": "Listing withheld by scrutiny branch pending translation filing"}
        ],
        registry_defects=[
            {"defect_id": "DEF-20", "rule": "Rule 14(b) HC Writ Rules", "description": "Vernacular Kannada notification lacks certified English translation", "is_curable": True},
            {"defect_id": "DEF-21", "rule": "Court Fees Act Sch. II", "description": "Deficit court fee of ₹20 on Vakalatnama", "is_curable": True},
            {"defect_id": "DEF-22", "rule": "Verification Affidavit", "description": "Deponent identification seal blurred", "is_curable": True}
        ],
        liberty_events=[],
        workflows=[],
        actions=[
            {"id": "ACT-20", "title": "Upload Certified Translation & File Re-submission Memo", "status": "PENDING_CURE"}
        ],
        reviews=[],
        approvals=[],
        verification_state={"integrity_status": "INTACT", "twin_version": 1},
        simulations=[],
        provenance=[],
        audit_records=[],
        governance_state={"status": "SCRUTINY_STAGE", "gate_open": False}
    )
]


class CaseStore:
    def __init__(self):
        self._cases: Dict[str, CaseContext] = {c.case_id: c for c in DEFAULT_CASES}
        self._active_case_id: str = "CASE-2024-DEL-0482"

    def list_cases(self) -> List[CaseContext]:
        return list(self._cases.values())

    def get_case(self, case_id: str) -> Optional[CaseContext]:
        return self._cases.get(case_id)

    def get_active_case(self) -> CaseContext:
        if self._active_case_id in self._cases:
            return self._cases[self._active_case_id]
        if self._cases:
            return next(iter(self._cases.values()))
        raise RuntimeError("No cases available in store")

    def set_active_case(self, case_id: str) -> CaseContext:
        if case_id not in self._cases:
            raise KeyError(f"Case '{case_id}' does not exist")
        self._active_case_id = case_id
        return self._cases[case_id]

    def create_or_update_case(self, case: CaseContext) -> CaseContext:
        self._cases[case.case_id] = case
        return case

    def authorize_active_case(self, case_id: str, approver_name: str) -> CaseContext:
        case = self._cases.get(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found")
        case.human_authorized = True
        case.approvals.append({
            "approved_by": approver_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "APPROVED",
            "scope": "ALL_CONSEQUENTIAL_ACTIONS"
        })
        return case


# Global Singleton Instance
case_store = CaseStore()
