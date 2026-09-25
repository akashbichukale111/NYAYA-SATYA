"""Missing-Evidence Detector for NYAYA-SATYA.

Identifies evidentiary vacuums, uncorroborated single-source claims,
and unresolved disputes where obtaining third-party records could reduce uncertainty.
STRICT NON-ADJUDICATION: Never asserts that missing evidence exists in reality.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from nyaya_adversarial.contracts.missing_evidence import MissingEvidenceCandidate
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.traversal.claim_dependencies import get_claim_descendants


class MissingEvidenceDetector:
    """Detects information gaps and potential evidence candidates across the case."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id

    def detect_missing_evidence(self) -> list[MissingEvidenceCandidate]:
        """Scans the twin for claims, disputes, and issues with information gaps."""
        candidates: list[MissingEvidenceCandidate] = []
        seen_questions: set[str] = set()

        # 1. Unsubstantiated claims (zero supporting evidence)
        for claim in self.twin.claims.values():
            if not claim.supporting_evidence_ids:
                q = f"What primary documentary record substantiates claim: '{claim.statement[:80]}...'?"
                if q not in seen_questions:
                    seen_questions.add(q)
                    candidates.append(
                        MissingEvidenceCandidate(
                            candidate_id=f"mcand_{uuid.uuid4().hex[:8]}",
                            case_id=self.case_id,
                            question=q,
                            related_claims=[claim.claim_id],
                            expected_evidence_type=self._guess_evidence_type(claim.statement),
                            current_uncertainty=0.9,
                            dependency=list(get_claim_descendants(self.twin, claim.claim_id)),
                            access_constraint="PARTY_DISCOVERY_REQUIRED",
                            estimated_information_value="HIGH" if get_claim_descendants(self.twin, claim.claim_id) else "MEDIUM",
                        )
                    )

        # 2. Contradiction tie-breakers (two records contradict each other)
        for cand in self.twin.contradictions:
            q = f"Is there an independent third-party record (e.g. banking, courier, registry) reconciling conflict between {cand.evidence_a_id} and {cand.evidence_b_id}?"
            if q not in seen_questions:
                seen_questions.add(q)
                affected = [
                    cid for cid, cl in self.twin.claims.items()
                    if cand.evidence_a_id in cl.supporting_evidence_ids or cand.evidence_b_id in cl.supporting_evidence_ids
                ]
                candidates.append(
                    MissingEvidenceCandidate(
                        candidate_id=f"mcand_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        question=q,
                        related_claims=affected,
                        expected_evidence_type="THIRD_PARTY_RECONCILIATION_RECORD",
                        current_uncertainty=0.8,
                        dependency=affected,
                        access_constraint="SUBPOENA_OR_THIRD_PARTY_REQUEST",
                        estimated_information_value="CRITICAL" if len(affected) >= 2 else "HIGH",
                    )
                )

        # 3. Unanchored timeline events (approximate or unknown timestamps)
        for event in self.twin.events.values():
            e_time = getattr(event, "event_time", None) or getattr(event, "timestamp", None)
            if event.temporal_status.value in ("APPROXIMATE", "UNANCHORED", "UNKNOWN") or not e_time:
                desc = getattr(event, "description", None) or getattr(event, "title", "Event")
                q = f"What timestamped record (metadata, email header, log) establishes the exact date/time of event: '{desc[:80]}...'?"
                if q not in seen_questions:
                    seen_questions.add(q)
                    candidates.append(
                        MissingEvidenceCandidate(
                            candidate_id=f"mcand_{uuid.uuid4().hex[:8]}",
                            case_id=self.case_id,
                            question=q,
                            related_claims=list(event.related_claim_ids),
                            expected_evidence_type="TIMESTAMPED_LOG_OR_RECEIPT",
                            current_uncertainty=0.7,
                            dependency=[],
                            access_constraint="TECHNICAL_AUDIT_LOG_REQUEST",
                            estimated_information_value="MEDIUM",
                        )
                    )

        # 4. Open issues lacking direct evidence
        for issue in self.twin.issues.values():
            if not issue.related_evidence_ids:
                q = f"What primary evidentiary material directly addresses open issue: '{issue.title}'?"
                if q not in seen_questions:
                    seen_questions.add(q)
                    candidates.append(
                        MissingEvidenceCandidate(
                            candidate_id=f"mcand_{uuid.uuid4().hex[:8]}",
                            case_id=self.case_id,
                            question=q,
                            related_claims=list(issue.related_claim_ids),
                            related_issue=issue.issue_id,
                            expected_evidence_type="PRIMARY_STATUTORY_OR_FACTUAL_RECORD",
                            current_uncertainty=0.85,
                            dependency=list(issue.related_claim_ids),
                            access_constraint="FORMAL_SUBMISSION",
                            estimated_information_value="CRITICAL",
                        )
                    )

        return candidates

    def _guess_evidence_type(self, statement: str) -> str:
        s = statement.lower()
        if any(w in s for w in ("pay", "paid", "amount", "bank", "account", "transfer")):
            return "BANK_STATEMENT_OR_TRANSFER_RECEIPT"
        if any(w in s for w in ("agree", "contract", "lease", "deed", "mou")):
            return "EXECUTED_CONTRACT_OR_AGREEMENT"
        if any(w in s for w in ("mail", "letter", "notice", "message", "whatsapp")):
            return "WRITTEN_COMMUNICATION_RECORD"
        if any(w in s for w in ("deliver", "ship", "received", "cargo")):
            return "DELIVERY_CHALLAN_OR_BILL_OF_LADING"
        return "PRIMARY_DOCUMENT"
