"""Global Case Store and Context Manager for NYAYA-SATYA OS.
Maintains state across all 12 engines and ensures consistent case isolation.
"""

from typing import Dict, List, Optional
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
        tags=["Undertrial", "Sec 479 BNSS", "Defect in Service", "Bail Urgent"]
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
        tags=["Commercial", "Arbitration § 34", "High Stake", "Evidence Heavy"]
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
        tags=["Writ Art. 226", "Registry Defect", "Limitation Risk"]
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
        return case


# Global Singleton Instance
case_store = CaseStore()
