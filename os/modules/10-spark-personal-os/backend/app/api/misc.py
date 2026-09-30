from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import (
    User, CaseChange, Notification, SavedView, SearchIndexRecord, AuditEvent,
    CaseAttentionItem, Task, Deadline, ReviewTask, ApprovalRequest, Handoff,
    Case, ActivityEvent,
)
from app.models.enums import AttentionStatus, TaskStatus, ReviewStatus, ApprovalStatus, HandoffStatus
from app.schemas.schemas import (
    CaseChangeOut, NotificationOut, SavedViewCreate, SavedViewOut,
    CaseDigestOut, WorkspaceSummaryOut,
)
from app.core.security import get_current_user
from app.services.access import authorized_case_ids, get_authorized_case

router = APIRouter(tags=["misc"])


# --- What Changed? ---

@router.get("/api/changes", response_model=list[CaseChangeOut])
def what_changed(case_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids:
        return []
    q = db.query(CaseChange).filter(CaseChange.case_id.in_(ids))
    if case_id:
        q = q.filter(CaseChange.case_id == case_id)
    return q.order_by(CaseChange.occurred_at.desc()).limit(200).all()


# --- Notifications ---

@router.get("/api/notifications", response_model=list[NotificationOut])
def my_notifications(unread_only: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.read_state == False)  # noqa: E712
    return q.order_by(Notification.created_at.desc()).all()


@router.post("/api/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.get(Notification, notification_id)
    if notif is None or notif.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read_state = True
    db.commit()
    db.refresh(notif)
    return notif


# --- Saved views ---

@router.get("/api/saved-views", response_model=list[SavedViewOut])
def list_saved_views(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SavedView).filter(SavedView.user_id == user.id).all()


@router.post("/api/saved-views", response_model=SavedViewOut, status_code=201)
def create_saved_view(payload: SavedViewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    view = SavedView(user_id=user.id, name=payload.name, filters_json=payload.filters_json)
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


@router.delete("/api/saved-views/{view_id}", status_code=204)
def delete_saved_view(view_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    view = db.get(SavedView, view_id)
    if view is None or view.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved view not found")
    db.delete(view)
    db.commit()


# --- Global search ---

@router.get("/api/search")
def global_search(q: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids or not q.strip():
        return {"query": q, "results": []}
    like = f"%{q.lower()}%"
    records = (
        db.query(SearchIndexRecord)
        .filter(SearchIndexRecord.case_id.in_(ids))
        .filter(SearchIndexRecord.keywords.ilike(like))
        .limit(50)
        .all()
    )
    return {
        "query": q,
        "results": [
            {
                "case_id": r.case_id,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "title": r.title,
                "snippet": r.snippet,
            }
            for r in records
        ],
    }


# --- Audit (admin/advocate visibility into their own actions; full trail is not user-editable) ---

@router.get("/api/audit")
def my_audit_trail(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.actor_user_id == user.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": e.id, "action": e.action, "target_type": e.target_type,
            "target_id": e.target_id, "created_at": e.created_at,
        }
        for e in events
    ]


# --- Case digest: generated purely from stored state, no hallucinated summary ---

@router.get("/api/cases/{case_id}/digest", response_model=CaseDigestOut)
def case_digest(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = get_authorized_case(db, case_id, user)

    changes = (
        db.query(CaseChange).filter(CaseChange.case_id == case_id)
        .order_by(CaseChange.occurred_at.desc()).limit(10).all()
    )
    attention = (
        db.query(CaseAttentionItem)
        .filter(CaseAttentionItem.case_id == case_id, CaseAttentionItem.status == AttentionStatus.OPEN)
        .all()
    )
    blocked_tasks = (
        db.query(Task).filter(Task.case_id == case_id, Task.status == TaskStatus.BLOCKED).all()
    )
    reviews = (
        db.query(ReviewTask).filter(ReviewTask.case_id == case_id, ReviewTask.status == ReviewStatus.PENDING).all()
    )

    unknown_items = [
        f"{d.label}: date source is UNKNOWN" for d in
        db.query(Deadline).filter(Deadline.case_id == case_id).all()
        if d.date_source_type.value == "UNKNOWN"
    ]

    return CaseDigestOut(
        case_id=case.id,
        current_state=case.current_state_summary or "No current-state summary has been recorded for this case.",
        what_changed=[f"{c.entity_type} {c.entity_id} changed via {c.source_engine.value}" for c in changes],
        needs_attention=[f"[{a.priority.value}] {a.reason}" for a in attention],
        blocked=[f"Task blocked: {t.title}" for t in blocked_tasks],
        unknown=unknown_items,
        needs_review=[f"[{r.kind.value}] {r.what}" for r in reviews],
        next_safe_actions=[a.recommended_safe_action for a in attention if a.recommended_safe_action],
        generated_at=datetime.utcnow(),
    )


# --- Workspace summary (My Workspace landing counts) ---

@router.get("/api/workspace/summary", response_model=WorkspaceSummaryOut)
def workspace_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids:
        return WorkspaceSummaryOut(
            my_cases_count=0, my_attention_count=0, my_tasks_open_count=0,
            my_deadlines_upcoming_count=0, my_reviews_pending_count=0,
            my_approvals_pending_count=0, my_handoffs_pending_count=0,
        )

    attention_count = db.query(CaseAttentionItem).filter(
        CaseAttentionItem.case_id.in_(ids), CaseAttentionItem.status == AttentionStatus.OPEN
    ).count()
    tasks_open = db.query(Task).filter(
        Task.case_id.in_(ids), Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
    ).count()
    upcoming_deadlines = db.query(Deadline).filter(
        Deadline.case_id.in_(ids), Deadline.tracked_date >= datetime.utcnow()
    ).count()
    reviews_pending = db.query(ReviewTask).filter(
        ReviewTask.case_id.in_(ids), ReviewTask.status == ReviewStatus.PENDING
    ).count()
    approvals_pending = db.query(ApprovalRequest).filter(
        ApprovalRequest.case_id.in_(ids), ApprovalRequest.status == ApprovalStatus.PENDING
    ).count()
    handoffs_pending = db.query(Handoff).filter(
        Handoff.case_id.in_(ids), Handoff.status == HandoffStatus.PENDING
    ).count()

    return WorkspaceSummaryOut(
        my_cases_count=len(ids),
        my_attention_count=attention_count,
        my_tasks_open_count=tasks_open,
        my_deadlines_upcoming_count=upcoming_deadlines,
        my_reviews_pending_count=reviews_pending,
        my_approvals_pending_count=approvals_pending,
        my_handoffs_pending_count=handoffs_pending,
    )
