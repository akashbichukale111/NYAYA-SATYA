"""Evidence Verification Agent -- checks evidence availability/verification
state consistency (e.g. flags evidence stuck UNVERIFIED for follow-up).
This is analysis only; it never silently marks something VERIFIED."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.models.evidence import Evidence


class EvidenceVerificationAgent(Agent):
    name = "evidence_verification_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        unverified = [e.id for e in items if e.verification_state == "UNVERIFIED"]
        disputed = [e.id for e in items if e.verification_state == "DISPUTED"]
        return StepResult(
            step="VERIFY", agent=self.name, tool_calls=["case_state_lookup"],
            status="OK",
            detail={"total_evidence": len(items), "unverified": unverified, "disputed": disputed},
        )
