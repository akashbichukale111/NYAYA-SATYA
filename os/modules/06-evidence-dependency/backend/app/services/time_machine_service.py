"""
Time Machine.

Every meaningful mutation to an EvidenceItem writes an append-only
EvidenceVersion row (never updated, never deleted). This module turns
those rows into: current state, previous state, a snapshot at any past
timestamp, a diff between two versions, and a whole-case historical
reconstruction. Nothing here is faked -- every value returned comes
from a real, previously-written EvidenceVersion row or the live table.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.orm import EvidenceVersion, EvidenceItem, ClaimVersion, Claim, Case

SNAPSHOT_FIELDS = [
    "label", "source_text", "page_number", "section", "source_location_known",
    "extraction_method", "state", "verification_status", "document_id",
    "event_date", "discovery_date", "valid_from", "valid_until",
    "supersession_date", "superseded_by_evidence_id",
]

CLAIM_SNAPSHOT_FIELDS = [
    "text", "source", "verification_status", "temporal_validity",
    "superseded_by_claim_id", "review_state",
]


def _serialize(item: EvidenceItem) -> Dict:
    out = {}
    for f in SNAPSHOT_FIELDS:
        v = getattr(item, f)
        if isinstance(v, datetime):
            v = v.isoformat()
        out[f] = v
    return out


def snapshot_evidence(db: Session, item: EvidenceItem, reason: str = "") -> EvidenceVersion:
    """Write the next append-only version row for this evidence item."""
    last = (
        db.query(EvidenceVersion)
        .filter(EvidenceVersion.evidence_id == item.id)
        .order_by(EvidenceVersion.version_number.desc())
        .first()
    )
    next_version = 1 if last is None else last.version_number + 1
    version = EvidenceVersion(
        id=str(uuid.uuid4()),
        case_id=item.case_id,
        evidence_id=item.id,
        version_number=next_version,
        snapshot=_serialize(item),
        reason=reason,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    return version


def get_history(db: Session, evidence_id: str) -> List[EvidenceVersion]:
    return (
        db.query(EvidenceVersion)
        .filter(EvidenceVersion.evidence_id == evidence_id)
        .order_by(EvidenceVersion.version_number.asc())
        .all()
    )


def get_version(db: Session, evidence_id: str, version_number: int) -> Optional[EvidenceVersion]:
    return (
        db.query(EvidenceVersion)
        .filter(EvidenceVersion.evidence_id == evidence_id, EvidenceVersion.version_number == version_number)
        .first()
    )


def diff_versions(v1: EvidenceVersion, v2: EvidenceVersion) -> Dict:
    """Field-level diff between two real snapshots. Only changed fields are returned."""
    changes = {}
    for field in SNAPSHOT_FIELDS:
        old_val = v1.snapshot.get(field)
        new_val = v2.snapshot.get(field)
        if old_val != new_val:
            changes[field] = {"from": old_val, "to": new_val}
    return {
        "evidence_id": v1.evidence_id,
        "from_version": v1.version_number,
        "to_version": v2.version_number,
        "changed_fields": changes,
    }


def evidence_state_at(db: Session, evidence_id: str, at: datetime) -> Optional[Dict]:
    """The most recent real snapshot of one evidence item at or before `at`."""
    version = (
        db.query(EvidenceVersion)
        .filter(EvidenceVersion.evidence_id == evidence_id, EvidenceVersion.created_at <= at)
        .order_by(EvidenceVersion.version_number.desc())
        .first()
    )
    if not version:
        return None
    return {
        "evidence_id": evidence_id,
        "version_number": version.version_number,
        "as_of": version.created_at.isoformat(),
        "reason": version.reason,
        "snapshot": version.snapshot,
    }


def case_state_at(db: Session, case_id: str, at: datetime) -> Dict:
    """
    Historical reconstruction: for every evidence item AND claim that
    existed in this case by time `at` (i.e. has at least one version
    at/before `at`), return its real reconstructed state at that moment.
    Items with no version at or before `at` did not exist yet from the
    system's point of view and are omitted -- never fabricated.
    """
    evidence_ids = [
        row[0] for row in
        db.query(EvidenceVersion.evidence_id).filter(EvidenceVersion.case_id == case_id).distinct().all()
    ]
    reconstructed_evidence = []
    for eid in evidence_ids:
        state = evidence_state_at(db, eid, at)
        if state:
            reconstructed_evidence.append(state)

    claim_ids = [
        row[0] for row in
        db.query(ClaimVersion.claim_id).filter(ClaimVersion.case_id == case_id).distinct().all()
    ]
    reconstructed_claims = []
    for cid in claim_ids:
        state = claim_state_at(db, cid, at)
        if state:
            reconstructed_claims.append(state)

    return {
        "case_id": case_id,
        "as_of": at.isoformat(),
        "evidence_states": reconstructed_evidence,
        "claim_states": reconstructed_claims,
        "note": "Reconstructed from real EvidenceVersion/ClaimVersion snapshots only. "
                "Items with no version at or before this time are omitted, not fabricated.",
    }


def current_vs_previous(db: Session, evidence_id: str) -> Dict:
    history = get_history(db, evidence_id)
    if not history:
        return {"evidence_id": evidence_id, "current": None, "previous": None, "diff": None}
    current = history[-1]
    previous = history[-2] if len(history) >= 2 else None
    return {
        "evidence_id": evidence_id,
        "current": {"version_number": current.version_number, "as_of": current.created_at.isoformat(),
                     "reason": current.reason, "snapshot": current.snapshot},
        "previous": (
            {"version_number": previous.version_number, "as_of": previous.created_at.isoformat(),
             "reason": previous.reason, "snapshot": previous.snapshot}
            if previous else None
        ),
        "diff": diff_versions(previous, current) if previous else None,
    }


# ---------------------------------------------------------------------------
# Claim Time Machine -- identical pattern to the Evidence functions above,
# kept as separate functions (rather than a generic dispatcher) so each
# stays simple and the field lists don't need to be threaded through every
# call site.
# ---------------------------------------------------------------------------

def _serialize_claim(claim: Claim) -> Dict:
    out = {}
    for f in CLAIM_SNAPSHOT_FIELDS:
        v = getattr(claim, f)
        if isinstance(v, datetime):
            v = v.isoformat()
        out[f] = v
    return out


def snapshot_claim(db: Session, claim: Claim, reason: str = "") -> ClaimVersion:
    """Write the next append-only version row for this claim."""
    last = (
        db.query(ClaimVersion)
        .filter(ClaimVersion.claim_id == claim.id)
        .order_by(ClaimVersion.version_number.desc())
        .first()
    )
    next_version = 1 if last is None else last.version_number + 1
    version = ClaimVersion(
        id=str(uuid.uuid4()),
        case_id=claim.case_id,
        claim_id=claim.id,
        version_number=next_version,
        snapshot=_serialize_claim(claim),
        reason=reason,
        created_at=datetime.utcnow(),
    )
    db.add(version)
    return version


def get_claim_history(db: Session, claim_id: str) -> List[ClaimVersion]:
    return (
        db.query(ClaimVersion)
        .filter(ClaimVersion.claim_id == claim_id)
        .order_by(ClaimVersion.version_number.asc())
        .all()
    )


def get_claim_version(db: Session, claim_id: str, version_number: int) -> Optional[ClaimVersion]:
    return (
        db.query(ClaimVersion)
        .filter(ClaimVersion.claim_id == claim_id, ClaimVersion.version_number == version_number)
        .first()
    )


def diff_claim_versions(v1: ClaimVersion, v2: ClaimVersion) -> Dict:
    changes = {}
    for field in CLAIM_SNAPSHOT_FIELDS:
        old_val = v1.snapshot.get(field)
        new_val = v2.snapshot.get(field)
        if old_val != new_val:
            changes[field] = {"from": old_val, "to": new_val}
    return {
        "claim_id": v1.claim_id,
        "from_version": v1.version_number,
        "to_version": v2.version_number,
        "changed_fields": changes,
    }


def claim_state_at(db: Session, claim_id: str, at: datetime) -> Optional[Dict]:
    version = (
        db.query(ClaimVersion)
        .filter(ClaimVersion.claim_id == claim_id, ClaimVersion.created_at <= at)
        .order_by(ClaimVersion.version_number.desc())
        .first()
    )
    if not version:
        return None
    return {
        "claim_id": claim_id,
        "version_number": version.version_number,
        "as_of": version.created_at.isoformat(),
        "reason": version.reason,
        "snapshot": version.snapshot,
    }


def claim_current_vs_previous(db: Session, claim_id: str) -> Dict:
    history = get_claim_history(db, claim_id)
    if not history:
        return {"claim_id": claim_id, "current": None, "previous": None, "diff": None}
    current = history[-1]
    previous = history[-2] if len(history) >= 2 else None
    return {
        "claim_id": claim_id,
        "current": {"version_number": current.version_number, "as_of": current.created_at.isoformat(),
                     "reason": current.reason, "snapshot": current.snapshot},
        "previous": (
            {"version_number": previous.version_number, "as_of": previous.created_at.isoformat(),
             "reason": previous.reason, "snapshot": previous.snapshot}
            if previous else None
        ),
        "diff": diff_claim_versions(previous, current) if previous else None,
    }
