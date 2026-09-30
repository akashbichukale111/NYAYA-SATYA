"""Procedural Obligation Engine - FastAPI Service
Port / Mountable router implementing WHO / WHAT / LOSS / SIGN non-adjudicative statutory compliance.
"""

from fastapi import FastAPI, HTTPException
from typing import List, Dict
from datetime import datetime

try:
    from .models import (
        ObligationRecord,
        ObligationStatus,
        CounterpartyNotice,
        IrreversibleLossExposure,
        SignObligationRequest,
    )
except (ImportError, ValueError):
    import os, sys
    _app_dir = os.path.dirname(__file__)
    if _app_dir not in sys.path:
        sys.path.insert(0, _app_dir)
    from models import (
        ObligationRecord,
        ObligationStatus,
        CounterpartyNotice,
        IrreversibleLossExposure,
        SignObligationRequest,
    )

app = FastAPI(
    title="NYAYA-SATYA Procedural Obligation Engine",
    version="1.0.0",
    description="Statutory obligation tracking and irreversible exposure governance under Section 1."
)

# Seed database for demonstration cases
OBLIGATIONS_DB: Dict[str, ObligationRecord] = {
    "OBL-2024-001": ObligationRecord(
        obligation_id="OBL-2024-001",
        case_id="CASE-2024-DEL-0482",
        title="Notice of Procedural Defect in Chargesheet Supply",
        status=ObligationStatus.AWAITING_AUTHORISATION,
        counterparties=[
            CounterpartyNotice(
                counterparty="Chief Metropolitan Magistrate Court 03, Tis Hazari",
                told_claim="Accused No. 1 and No. 2 received full unredacted copies of witness statements under Sec 207 CrPC",
                told_at="2024-01-15T10:30:00Z",
                channel="Formal Filing Index",
                remedial_correction_required="Affidavit disclosing that Annexure D (CCTV Hash Log) was omitted in Accused No. 2's set"
            ),
            CounterpartyNotice(
                counterparty="Special Public Prosecutor, Delhi Police",
                told_claim="Defense acknowledged receipt of all forensic exhibits",
                told_at="2024-02-01T14:00:00Z",
                channel="Court Handover Memo",
                remedial_correction_required="Notice to provide legible forensic clone image within 7 days"
            )
        ],
        reversible_actions=[
            "File supplementary praecipe tendering omitted Annexure D",
            "Serve notice of discrepancy on Prosecution Branch",
            "Request urgent mentioning for dasti service before 2024-10-18"
        ],
        irreversible_loss=IrreversibleLossExposure(
            min_exposure_inr=0.0,
            max_exposure_inr=50000.0,
            unstated_assumptions=[
                "Court may refuse adjournment if defect is not cured before cause list publication",
                "Witness summons may lapse if fresh summons not dispatched"
            ],
            qualitative_impact="Loss of one hearing date causing an estimated 45-day cycle delay in custody."
        ),
        ruling_basis="CrPC Section 207 mandatory document supply mandate & Delhi HC Rules Ch. IV"
    ),
    "OBL-2024-098": ObligationRecord(
        obligation_id="OBL-2024-098",
        case_id="CASE-2024-KA-0077",
        title="Curative Re-Affirmation for High Court Writ Scrutiny",
        status=ObligationStatus.AWAITING_AUTHORISATION,
        counterparties=[
            CounterpartyNotice(
                counterparty="Registrar (Judicial), High Court of Karnataka",
                told_claim="Kannada translated notifications certified by official translator",
                told_at="2024-09-02T16:00:00Z",
                channel="E-Filing Portal Upload",
                remedial_correction_required="Submit advocate certificate of translation under Karnataka HC Writ Rules"
            )
        ],
        reversible_actions=[
            "Upload advocate-certified true copy of Annexure P-4",
            "Sign electronic curative compliance memo"
        ],
        irreversible_loss=IrreversibleLossExposure(
            min_exposure_inr=15000.0,
            max_exposure_inr=15000.0,
            unstated_assumptions=["Re-filing delay could cause expiry of the 30-day statutory scrutiny cure window"],
            qualitative_impact="Petition may be dismissed for default by Registry Master without hearing."
        ),
        ruling_basis="Karnataka High Court Rules 1959, Part IV Rule 5"
    )
}


@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "module": "05-procedural-obligation",
        "status_note": "PARTIAL / SECTION 1 PRESENT - GROUNDED IN UNWIND OBLIGATION ENGINE",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/cases/{case_id}/obligations", response_model=List[ObligationRecord])
def list_obligations_for_case(case_id: str):
    return [ob for ob in OBLIGATIONS_DB.values() if ob.case_id == case_id]


@app.get("/api/obligations/{obligation_id}", response_model=ObligationRecord)
def get_obligation(obligation_id: str):
    if obligation_id not in OBLIGATIONS_DB:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return OBLIGATIONS_DB[obligation_id]


@app.post("/api/obligations/{obligation_id}/sign", response_model=ObligationRecord)
def sign_obligation(obligation_id: str, req: SignObligationRequest):
    """UNWIND Human Legal Gate signoff."""
    if obligation_id not in OBLIGATIONS_DB:
        raise HTTPException(status_code=404, detail="Obligation not found")
    ob = OBLIGATIONS_DB[obligation_id]
    ob.status = ObligationStatus.AUTHORISED
    ob.approver = f"{req.approver_name} ({req.bar_council_id})"
    ob.signed_at = datetime.utcnow()
    return ob


@app.get("/api/obligations/{obligation_id}/render")
def render_obligation_memo(obligation_id: str):
    """Renders formatted UNWIND legal correction obligation memo."""
    if obligation_id not in OBLIGATIONS_DB:
        raise HTTPException(status_code=404, detail="Obligation not found")
    ob = OBLIGATIONS_DB[obligation_id]
    
    lines = [
        "=" * 68,
        f"NYAYA-SATYA PROCEDURAL CORRECTION OBLIGATION: {ob.obligation_id}",
        "=" * 68,
        f"Case Scope       : {ob.case_id} - {ob.title}",
        f"Status           : {ob.status.value}",
        f"Must Be Signed By: {ob.approver or 'AWAITING HUMAN LAWYER SIGNATURE'}",
        f"Statutory Basis  : {ob.ruling_basis}",
        "",
        "-- WHO WAS TOLD SOMETHING THAT REQUIRES FORMAL CORRECTION " + "-" * 10,
    ]
    for cp in ob.counterparties:
        lines.append(f"  * Counterparty : {cp.counterparty}")
        lines.append(f"    Prior Record : {cp.told_claim}")
        lines.append(f"    Date / Via   : {cp.told_at} via {cp.channel}")
        lines.append(f"    Correction   : {cp.remedial_correction_required}")
        lines.append("")
    
    lines.append("-- REVERSIBLE ACTIONS (Can and must be executed) " + "-" * 18)
    for act in ob.reversible_actions:
        lines.append(f"  [ ] {act}")
    lines.append("")
    
    lines.append("-- IRREVERSIBLE EXPOSURE / PROCEDURAL LOSS (Range, not point) " + "-" * 7)
    lines.append(f"  Estimated Financial Impact : INR {ob.irreversible_loss.min_exposure_inr:,.2f} - INR {ob.irreversible_loss.max_exposure_inr:,.2f}")
    lines.append(f"  Qualitative Impact        : {ob.irreversible_loss.qualitative_impact}")
    for asmp in ob.irreversible_loss.unstated_assumptions:
        lines.append(f"    - Assumption: {asmp}")
    lines.append("")
    lines.append("=" * 68)
    lines.append("HUMAN AUTHORIZATION GATE: This obligation cannot be dispatched without licensed counsel approval.")
    
    return {"text": "\n".join(lines)}
