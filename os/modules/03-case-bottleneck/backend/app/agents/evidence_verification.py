"""
Evidence Verification Agent — checks that cited evidence actually exists as a
stored, traceable artifact, and flags quarantined (suspected prompt-injection)
documents so they are never silently treated as reliable case facts
(Sections 39, 41, 42).
"""
from __future__ import annotations

from sqlmodel import Session, select

from ..models import CaseDocument


class EvidenceVerificationAgent:
    name = "evidence-verification-agent"

    def check(self, session: Session, case_id: str, evidence_refs: list[str]) -> dict:
        docs = {d.id: d for d in session.exec(select(CaseDocument).where(CaseDocument.case_id == case_id)).all()}
        traceable, missing, quarantined = [], [], []
        for ref in evidence_refs:
            doc = docs.get(ref)
            if doc is None:
                missing.append(ref)
            elif doc.quarantined:
                quarantined.append(ref)
            else:
                traceable.append(ref)
        return {
            "traceable": traceable,
            "missing_source": missing,
            "quarantined_and_excluded": quarantined,
            "fully_traceable": not missing and not quarantined and bool(evidence_refs),
        }
