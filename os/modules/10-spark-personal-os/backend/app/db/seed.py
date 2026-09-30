"""
Seeds DEMO data: fictional users and cases only, all flagged is_demo=True.
No real legal data. No real case names, numbers, or parties.

Run: python -m app.db.seed
"""
from datetime import datetime, timedelta

from app.db.session import Base, engine, SessionLocal
from app.models import models as m
from app.models.enums import (
    RoleName, MembershipRole, AttentionPriority, AttentionType, AttentionStatus,
    SourceEngine, TaskStatus, DateSourceType, ReviewKind, ReviewStatus,
    ApprovalActionType, ApprovalStatus,
)
from app.core.security import hash_password


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(m.User).filter(m.User.email == "demo.advocate@example.com").first()
        if existing:
            print("Demo data already present. Skipping seed.")
            return

        advocate = m.User(
            email="demo.advocate@example.com",
            hashed_password=hash_password("DemoPass123!"),
            full_name="Demo Advocate",
            role=RoleName.ADVOCATE,
        )
        legal_aid = m.User(
            email="demo.legalaid@example.com",
            hashed_password=hash_password("DemoPass123!"),
            full_name="Demo Legal Aid Worker",
            role=RoleName.LEGAL_AID,
        )
        admin = m.User(
            email="demo.admin@example.com",
            hashed_password=hash_password("DemoPass123!"),
            full_name="Demo Admin",
            role=RoleName.ADMIN,
        )
        db.add_all([advocate, legal_aid, admin])
        db.flush()

        for u in (advocate, legal_aid, admin):
            db.add(m.UserProfile(user_id=u.id))
            db.add(m.NotificationPreference(user_id=u.id))

        workspace = m.Workspace(owner_user_id=advocate.id, name="Demo Advocate's Workspace", is_demo=True)
        db.add(workspace)
        db.flush()

        case1 = m.Case(
            workspace_id=workspace.id,
            case_number="DEMO-2026-0001",
            title="[FICTIONAL DEMO CASE] State v. Sample Matter A",
            current_state_summary=(
                "Fictional demo case. Evidence intake is in progress; one "
                "procedural obligation is pending; a hearing date has been "
                "reported by a source engine and is approaching."
            ),
            is_demo=True,
        )
        case2 = m.Case(
            workspace_id=workspace.id,
            case_number="DEMO-2026-0002",
            title="[FICTIONAL DEMO CASE] Sample Matter B — Registry Review",
            current_state_summary=(
                "Fictional demo case. A registry defect was reported and is "
                "awaiting human review."
            ),
            is_demo=True,
        )
        db.add_all([case1, case2])
        db.flush()

        db.add(m.CaseMembership(case_id=case1.id, user_id=advocate.id, role=MembershipRole.OWNER, pinned=True))
        db.add(m.CaseMembership(case_id=case1.id, user_id=legal_aid.id, role=MembershipRole.COLLABORATOR))
        db.add(m.CaseMembership(case_id=case2.id, user_id=advocate.id, role=MembershipRole.OWNER))

        # --- Attention items (each retains source engine + provenance) ---
        att1 = m.CaseAttentionItem(
            case_id=case1.id,
            source_engine=SourceEngine.HEARING_READINESS,
            source_entity="hearing:DEMO-2026-0001:h1",
            type=AttentionType.TRACKED_DATE_APPROACHING,
            priority=AttentionPriority.HIGH_ATTENTION,
            reason="A source-stated hearing date is approaching and hearing-readiness checks are incomplete.",
            provenance_refs=["engine:hearing_readiness_engine#h1", "case:DEMO-2026-0001"],
            requires_human_review=False,
            recommended_safe_action="Review the hearing readiness checklist for this case.",
            what_changed="Hearing readiness engine reported an incomplete checklist item.",
        )
        att2 = m.CaseAttentionItem(
            case_id=case1.id,
            source_engine=SourceEngine.PROCEDURAL_OBLIGATION,
            source_entity="obligation:DEMO-2026-0001:o1",
            type=AttentionType.OBLIGATION_PENDING,
            priority=AttentionPriority.ATTENTION,
            reason="A procedural obligation reported by the Procedural Obligation Engine is still pending.",
            provenance_refs=["engine:procedural_obligation_engine#o1"],
            requires_human_review=False,
            recommended_safe_action="Open the obligation detail to see what is required.",
        )
        att3 = m.CaseAttentionItem(
            case_id=case2.id,
            source_engine=SourceEngine.REGISTRY_DEFECT,
            source_entity="defect:DEMO-2026-0002:d1",
            type=AttentionType.REGISTRY_DEFECT,
            priority=AttentionPriority.REQUIRES_HUMAN_REVIEW,
            reason="A registry defect was reported and requires human review before any correction is made.",
            provenance_refs=["engine:registry_defect_engine#d1"],
            requires_human_review=True,
            recommended_safe_action="Open the review queue to evaluate the reported defect.",
        )
        db.add_all([att1, att2, att3])

        # --- Deadlines (tracked dates, source-typed, never invented) ---
        db.add(m.Deadline(
            case_id=case1.id, label="Hearing (source-stated)",
            tracked_date=datetime.utcnow() + timedelta(days=6),
            date_source_type=DateSourceType.SOURCE_STATED,
            source_engine=SourceEngine.HEARING_READINESS,
            source_entity="hearing:DEMO-2026-0001:h1",
        ))
        db.add(m.Deadline(
            case_id=case1.id, label="Obligation response window (source-stated)",
            tracked_date=datetime.utcnow() + timedelta(days=2),
            date_source_type=DateSourceType.SOURCE_STATED,
            source_engine=SourceEngine.PROCEDURAL_OBLIGATION,
            source_entity="obligation:DEMO-2026-0001:o1",
        ))

        # --- Tasks with a dependency chain ---
        t1 = m.Task(
            case_id=case1.id, title="Request missing document from client",
            source_engine=SourceEngine.EVIDENCE_DEPENDENCY, source_entity="evidence:DEMO-2026-0001:e1",
            assignee_id=advocate.id, priority=AttentionPriority.ATTENTION, status=TaskStatus.IN_PROGRESS,
        )
        db.add(t1)
        db.flush()
        t2 = m.Task(
            case_id=case1.id, title="Verify received document",
            source_engine=SourceEngine.EVIDENCE_DEPENDENCY, source_entity="evidence:DEMO-2026-0001:e1",
            assignee_id=advocate.id, priority=AttentionPriority.ATTENTION, status=TaskStatus.BLOCKED,
            requires_verification=True,
        )
        db.add(t2)
        db.flush()
        db.add(m.TaskDependency(task_id=t2.id, depends_on_task_id=t1.id))

        # --- Review queue item ---
        db.add(m.ReviewTask(
            case_id=case2.id, kind=ReviewKind.REGISTRY_DEFECT_REVIEW,
            what="Registry defect reported on filing DEMO-2026-0002.",
            why="Registry Defect Engine flagged a mismatch requiring human confirmation before correction.",
            source_engine=SourceEngine.REGISTRY_DEFECT,
            evidence_refs=["engine:registry_defect_engine#d1"],
            current_state="Defect reported, uncorrected.",
            proposed_action="Confirm defect and route for correction.",
            status=ReviewStatus.PENDING,
        ))

        # --- Approval request ---
        db.add(m.ApprovalRequest(
            case_id=case2.id, action_type=ApprovalActionType.EVIDENCE_STATE_CHANGE,
            description="Approve marking evidence e2 as verified after manual review.",
            requested_by=legal_aid.id, status=ApprovalStatus.PENDING,
        ))

        # --- Case change history ---
        db.add(m.CaseChange(
            case_id=case1.id, source_engine=SourceEngine.CASE_CONTINUITY,
            entity_type="ObligationStatus", entity_id="o1",
            before_json={"status": "not_started"}, after_json={"status": "pending"},
            actor="case_continuity_engine",
        ))

        # --- Search index ---
        db.add(m.SearchIndexRecord(
            case_id=case1.id, entity_type="Case", entity_id=case1.id,
            title=case1.title, snippet="Fictional demo case for Spark Personal OS.",
            keywords=f"{case1.title} {case1.case_number} sample matter demo",
        ))
        db.add(m.SearchIndexRecord(
            case_id=case2.id, entity_type="Case", entity_id=case2.id,
            title=case2.title, snippet="Fictional demo case for Spark Personal OS.",
            keywords=f"{case2.title} {case2.case_number} registry review demo",
        ))

        # --- Engine connection stubs (all clearly DEMO stubs, not real integrations) ---
        for eng in SourceEngine:
            if eng == SourceEngine.SPARK:
                continue
            db.add(m.EngineConnection(engine=eng, status="demo_stub",
                                       notes="Not a live integration. DEMO mode stub only."))

        db.commit()
        print("Seed complete.")
        print("Demo users (password: DemoPass123!):")
        print("  demo.advocate@example.com  (advocate)")
        print("  demo.legalaid@example.com  (legal_aid)")
        print("  demo.admin@example.com     (admin)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
