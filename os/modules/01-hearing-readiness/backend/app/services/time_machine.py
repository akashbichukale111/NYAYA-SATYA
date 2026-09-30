"""
Readiness Time Machine (section 15). Snapshots are immutable rows;
diff_versions() only reads, never mutates, so history can never be lost.
"""
from __future__ import annotations

from app.models.version import CaseVersion
from app.models.requirement import Requirement
from app.models.evidence import Evidence
from app.models.blocker import Blocker
from app.services.readiness_engine import build_readiness_snapshot
from app.models.hearing import Hearing


def _current_full_state(db, case_id: str) -> dict:
    reqs = [r.to_dict() for r in db.query(Requirement).filter(Requirement.case_id == case_id).all()]
    evid = [e.to_dict() for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()]
    blockers = [b.to_dict() for b in db.query(Blocker).filter(Blocker.case_id == case_id).all()]
    hearing = db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    hearing_uncertain = (hearing is None) or (hearing.purpose_status == "UNCERTAIN")
    readiness = build_readiness_snapshot(reqs, blockers, hearing_uncertain)
    return {"requirements": reqs, "evidence": evid, "blockers": blockers, "readiness": readiness}


def snapshot_version(db, case_id: str, trigger: str) -> CaseVersion:
    last = (
        db.query(CaseVersion)
        .filter(CaseVersion.case_id == case_id)
        .order_by(CaseVersion.version_number.desc())
        .first()
    )
    next_number = (last.version_number + 1) if last else 1
    snap = _current_full_state(db, case_id)
    version = CaseVersion(
        case_id=case_id, version_number=next_number, trigger=trigger, snapshot=snap,
    )
    db.add(version)
    db.flush()
    return version


def list_versions(db, case_id: str) -> list[dict]:
    versions = (
        db.query(CaseVersion)
        .filter(CaseVersion.case_id == case_id)
        .order_by(CaseVersion.version_number.asc())
        .all()
    )
    return [v.to_dict() for v in versions]


def diff_versions(db, case_id: str, from_version: int, to_version: int) -> dict:
    v1 = db.query(CaseVersion).filter(CaseVersion.case_id == case_id,
                                       CaseVersion.version_number == from_version).first()
    v2 = db.query(CaseVersion).filter(CaseVersion.case_id == case_id,
                                       CaseVersion.version_number == to_version).first()
    if not v1 or not v2:
        raise ValueError("One or both versions not found for this case.")

    s1, s2 = v1.snapshot, v2.snapshot

    def index_by_id(items):
        return {i["id"]: i for i in items}

    ev1, ev2 = index_by_id(s1["evidence"]), index_by_id(s2["evidence"])
    bl1, bl2 = index_by_id(s1["blockers"]), index_by_id(s2["blockers"])
    req1, req2 = index_by_id(s1["requirements"]), index_by_id(s2["requirements"])

    added_evidence = [v for k, v in ev2.items() if k not in ev1]
    removed_evidence = [v for k, v in ev1.items() if k not in ev2]

    resolved_blockers = [
        v for k, v in bl2.items()
        if k in bl1 and bl1[k]["status"] == "OPEN" and v["status"] != "OPEN"
    ]
    new_blockers = [
        v for k, v in bl2.items()
        if k not in bl1 or (bl1[k]["status"] != "OPEN" and v["status"] == "OPEN")
    ]

    changed_requirements = [
        {"id": k, "before": req1[k]["status"], "after": v["status"]}
        for k, v in req2.items() if k in req1 and req1[k]["status"] != v["status"]
    ]

    confidence_changes = [
        {"id": k, "before": req1[k]["confidence"], "after": v["confidence"]}
        for k, v in req2.items() if k in req1 and req1[k]["confidence"] != v["confidence"]
    ]

    return {
        "from_version": from_version,
        "to_version": to_version,
        "added_evidence": added_evidence,
        "removed_evidence": removed_evidence,
        "resolved_blockers": resolved_blockers,
        "new_blockers": new_blockers,
        "changed_requirements": changed_requirements,
        "confidence_changes": confidence_changes,
        "readiness_before": s1["readiness"],
        "readiness_after": s2["readiness"],
    }
