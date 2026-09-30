"""Blocker Investigation Agent -- IDENTIFY BLOCKER. Blockers themselves are
synced as part of the readiness audit; this agent's job is to fetch and
report the current OPEN blocker set with explanations attached."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.models.blocker import Blocker
from app.models.requirement import Requirement
from app.models.evidence import Evidence
from app.services.explanation_engine import explain_blocker


class BlockerInvestigationAgent(Agent):
    name = "blocker_investigation_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        blockers = db.query(Blocker).filter(Blocker.case_id == case_id, Blocker.status == "OPEN").all()
        explanations = []
        for b in blockers:
            req = db.query(Requirement).filter(Requirement.id == b.requirement_id).first()
            evidence_items = []
            if req:
                evidence_items = [
                    db.query(Evidence).filter(Evidence.id == eid).first()
                    for eid in (req.evidence_refs or [])
                ]
                evidence_items = [e.to_dict() for e in evidence_items if e is not None]
            explanations.append({
                "blocker_id": b.id,
                **explain_blocker(b.to_dict(), req.to_dict() if req else {}, evidence_items),
            })
        return StepResult(
            step="IDENTIFY_BLOCKER", agent=self.name, tool_calls=["blocker_analysis"],
            status="OK", detail={"open_blockers": len(blockers), "explanations": explanations},
        )
