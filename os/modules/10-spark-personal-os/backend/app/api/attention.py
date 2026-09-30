from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, CaseAttentionItem
from app.models.enums import AttentionStatus
from app.schemas.schemas import AttentionItemOut
from app.core.security import get_current_user
from app.services.access import authorized_case_ids

router = APIRouter(prefix="/api/attention", tags=["attention"])


@router.get("", response_model=list[AttentionItemOut])
def my_attention(
    priority: str | None = None,
    status_filter: str | None = None,
    case_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated attention items across every case the user is authorized to see."""
    ids = authorized_case_ids(db, user)
    if not ids:
        return []
    q = db.query(CaseAttentionItem).filter(CaseAttentionItem.case_id.in_(ids))
    if case_id:
        q = q.filter(CaseAttentionItem.case_id == case_id)
    if priority:
        q = q.filter(CaseAttentionItem.priority == priority)
    if status_filter:
        q = q.filter(CaseAttentionItem.status == status_filter)
    else:
        q = q.filter(CaseAttentionItem.status != AttentionStatus.DISMISSED)
    return q.order_by(CaseAttentionItem.created_at.desc()).all()


@router.get("/{attention_id}", response_model=AttentionItemOut)
def attention_detail(attention_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Explainability panel: source, what changed, provenance, dependencies, safe next action."""
    item = db.get(CaseAttentionItem, attention_id)
    ids = authorized_case_ids(db, user)
    if item is None or item.case_id not in ids:
        raise HTTPException(status_code=404, detail="Attention item not found")
    return item


@router.post("/{attention_id}/acknowledge", response_model=AttentionItemOut)
def acknowledge(attention_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(CaseAttentionItem, attention_id)
    ids = authorized_case_ids(db, user)
    if item is None or item.case_id not in ids:
        raise HTTPException(status_code=404, detail="Attention item not found")
    item.status = AttentionStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(item)
    return item


@router.post("/{attention_id}/dismiss", response_model=AttentionItemOut)
def dismiss(attention_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(CaseAttentionItem, attention_id)
    ids = authorized_case_ids(db, user)
    if item is None or item.case_id not in ids:
        raise HTTPException(status_code=404, detail="Attention item not found")
    if item.requires_human_review:
        raise HTTPException(status_code=400, detail="Items requiring human review cannot be silently dismissed")
    item.status = AttentionStatus.DISMISSED
    db.commit()
    db.refresh(item)
    return item
