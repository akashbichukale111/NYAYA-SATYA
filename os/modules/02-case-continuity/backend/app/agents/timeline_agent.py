"""
Timeline Agent (section 25 #9).

Assembles the case's Events (plus derived Documents/Orders/Hearings/
Deadlines/Actions/Verifications) into one ordered, filterable timeline,
each node carrying provenance back to its source event.
"""
from sqlalchemy.orm import Session

from app.models import Event, Verification
from app.agents.base import run_agent


def build_timeline(db: Session, *, case_id: str, correlation_id: str) -> list[dict]:
    with run_agent(db, case_id=case_id, agent_name="TimelineAgent", correlation_id=correlation_id,
                    input_summary=f"case_id={case_id}") as result:
        events = db.query(Event).filter(Event.case_id == case_id).order_by(Event.timestamp).all()
        verifications_by_proposal = {
            v.change_proposal_id: v for v in db.query(Verification).filter(Verification.case_id == case_id).all()
        }
        nodes = []
        for ev in events:
            nodes.append({
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "timestamp": ev.timestamp.isoformat(),
                "actor": ev.actor,
                "description": ev.description,
                "confidence": ev.confidence,
                "provenance": ev.provenance,
                "correlation_id": ev.correlation_id,
            })
        result["output_summary"] = f"{len(nodes)} timeline node(s)"
        return nodes
