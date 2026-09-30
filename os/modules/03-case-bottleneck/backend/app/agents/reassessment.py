"""
Reassessment Agent — closes the OBSERVE...UPDATE loop (Section 36).
On a passed verification, marks the underlying dependency satisfied, resolves
the bottleneck, and re-runs discovery so newly-exposed downstream bottlenecks
surface (Section 58's flagship demo moment).
"""
from __future__ import annotations

import uuid

from sqlmodel import Session, select

from ..models import Bottleneck, BottleneckStatus, BottleneckHistoryEntry, Dependency, ActionItem, utcnow
from .discovery import BottleneckDiscoveryAgent


class ReassessmentAgent:
    name = "reassessment-agent"

    def run(self, session: Session, action: ActionItem, verification_passed: bool) -> dict:
        bottleneck = session.get(Bottleneck, action.bottleneck_id)
        if bottleneck is None:
            return {"newly_visible_bottlenecks": []}

        if verification_passed:
            for dep_id in bottleneck.dependency_refs:
                dep = session.get(Dependency, dep_id)
                if dep:
                    dep.status = "SATISFIED"
                    session.add(dep)
            prev_status = bottleneck.status
            bottleneck.status = BottleneckStatus.RESOLVED
            bottleneck.resolved_at = utcnow()
            bottleneck.verification_state = "VERIFIED"
            session.add(bottleneck)
            session.add(BottleneckHistoryEntry(
                id=f"hist_{uuid.uuid4().hex[:10]}", bottleneck_id=bottleneck.id, case_id=bottleneck.case_id,
                from_status=prev_status.value, to_status=BottleneckStatus.RESOLVED.value,
                note="Verification passed; dependency marked satisfied.",
            ))
            session.commit()

            before_ids = {b.id for b in session.exec(
                select(Bottleneck).where(Bottleneck.case_id == bottleneck.case_id)
            ).all()}
            BottleneckDiscoveryAgent().run(session, bottleneck.case_id)
            after = session.exec(select(Bottleneck).where(Bottleneck.case_id == bottleneck.case_id)).all()
            newly_visible = [b.id for b in after if b.id not in before_ids]
            return {"newly_visible_bottlenecks": newly_visible}
        else:
            bottleneck.verification_state = "VERIFICATION_FAILED"
            bottleneck.status = BottleneckStatus.ACTIONABLE
            session.add(bottleneck)
            session.add(BottleneckHistoryEntry(
                id=f"hist_{uuid.uuid4().hex[:10]}", bottleneck_id=bottleneck.id, case_id=bottleneck.case_id,
                from_status=bottleneck.status.value, to_status=BottleneckStatus.ACTIONABLE.value,
                note="Verification failed; bottleneck remains open.",
            ))
            session.commit()
            return {"newly_visible_bottlenecks": []}
