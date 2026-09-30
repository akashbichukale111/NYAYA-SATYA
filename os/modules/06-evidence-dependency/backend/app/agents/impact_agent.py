"""Impact Agent -- read-only structured wrapper around impact_service."""
from typing import Dict

from sqlalchemy.orm import Session

from app.services.impact_service import compute_impact


def report(db: Session, case_id: str, node_type: str, node_id: str) -> Dict:
    return compute_impact(db, case_id, node_type, node_id)
