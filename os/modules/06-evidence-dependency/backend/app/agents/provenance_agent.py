"""
Provenance Agent.

Read-only structured check of provenance completeness for a case's
evidence: every item either has a known source location (page/section)
or is explicitly reported as SOURCE_LOCATION_UNKNOWN. Never fabricates
a location; never silently treats "unknown" as "fine".
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import EvidenceItem


def check_provenance(db: Session, case_id: str) -> Dict:
    items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    known: List[str] = []
    unknown: List[str] = []
    for e in items:
        if e.source_location_known and (e.page_number is not None or e.section is not None):
            known.append(e.id)
        else:
            unknown.append(e.id)
    return {
        "case_id": case_id,
        "total_evidence": len(items),
        "source_location_known": known,
        "source_location_unknown": unknown,
        "completeness_ratio": (len(known) / len(items)) if items else None,
    }
