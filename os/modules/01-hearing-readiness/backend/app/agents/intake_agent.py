"""Intake Agent -- OBSERVE. Confirms case + documents are loadable and
surfaces any injection-flagged documents for human awareness."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.services import case_twin


class IntakeAgent(Agent):
    name = "intake_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        full = case_twin.get_case_full(db, case_id)
        if full is None:
            return StepResult(step="OBSERVE", agent=self.name, status="FAILED",
                               detail={"error": "case not found"})
        flagged = [d for d in full["documents"] if d.get("injection_flag") == "true"]
        return StepResult(
            step="OBSERVE", agent=self.name, tool_calls=["document_reader"],
            status="OK",
            detail={
                "document_count": len(full["documents"]),
                "evidence_count": len(full["evidence"]),
                "injection_flagged_documents": [d["id"] for d in flagged],
            },
        )
