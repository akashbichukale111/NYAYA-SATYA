"""Evidence Conflict Arena for NYAYA-SATYA.

Grounded in CaseDigitalTwin and Phase 2 safe evidence references.
Detects, normalizes, and categorizes evidentiary, numeric, temporal,
identity, and document conflicts across the case.
Strictly non-adjudicative: does not declare guilt, fraud, or perjury.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from nyaya_adversarial.contracts.conflict import (
    ConflictSeverity,
    ConflictSet,
    ConflictType,
    EvidenceConflict,
)
from nyaya_evidence.contradiction.engine import ContradictionType as Phase2ContradictionType
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.relationships import RelationshipType
from tarka_vyuh.contracts.provenance import ProvenanceRef


class ConflictArena:
    """Core engine for identifying and aggregating evidentiary conflicts in a case."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id

    def detect_conflicts(self) -> ConflictSet:
        """Discovers all conflicts across twin contradictions, graphs, and timelines."""
        conflicts: list[EvidenceConflict] = []
        seen_pairs: set[tuple[str, str, str]] = set()

        # 1. Ingest existing twin contradictions (from Phase 2 ContradictionAnalysisEngine)
        for cand in self.twin.contradictions:
            pair_key = tuple(sorted([cand.evidence_a_id, cand.evidence_b_id])) + (cand.contradiction_type.value,)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Map Phase 2 ContradictionType to ConflictType
            ctype = self._map_phase2_type(cand.contradiction_type)
            conflicts.append(
                EvidenceConflict(
                    conflict_id=f"conf_{cand.contradiction_id}",
                    case_id=self.case_id,
                    conflict_type=ctype,
                    subject=f"Conflict between {cand.evidence_a_id} and {cand.evidence_b_id}",
                    evidence_a_id=cand.evidence_a_id,
                    evidence_b_id=cand.evidence_b_id,
                    claim_ids=self._find_claims_for_evidence_pair(cand.evidence_a_id, cand.evidence_b_id),
                    description=f"{cand.claim_a} VS {cand.claim_b}",
                    supporting_text_refs=list(cand.supporting_spans),
                    provenance_refs=list(cand.provenance_refs),
                    severity=ConflictSeverity.HIGH if ctype == ConflictType.DIRECT_CONTRADICTION else ConflictSeverity.MEDIUM,
                    uncertainty=cand.uncertainty,
                    status="OPEN_FOR_REVIEW",
                    detected_at=cand.detected_at,
                )
            )

        # 2. Ingest graph relationships with RelationshipType.CONTRADICTS
        for rel in self.twin.relationships.values():
            if rel.relationship_type == RelationshipType.CONTRADICTS:
                pair_key = tuple(sorted([rel.source_id, rel.target_id])) + ("GRAPH_CONTRADICTS",)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                conflicts.append(
                    EvidenceConflict(
                        conflict_id=f"conf_rel_{rel.relationship_id}",
                        case_id=self.case_id,
                        conflict_type=ConflictType.DIRECT_CONTRADICTION,
                        subject=f"Graph contradiction: {rel.source_id} vs {rel.target_id}",
                        evidence_a_id=rel.source_id,
                        evidence_b_id=rel.target_id,
                        claim_ids=self._find_claims_for_evidence_pair(rel.source_id, rel.target_id),
                        description=getattr(rel, "description", None) or rel.metadata.get("description", "") or f"Direct contradiction declared in case graph between {rel.source_id} and {rel.target_id}",
                        provenance_refs=list(rel.provenance_refs),
                        severity=ConflictSeverity.HIGH,
                        uncertainty=1.0 - rel.weight if rel.weight else 0.3,
                        status="OPEN_FOR_REVIEW",
                    )
                )

        # 3. Ingest temporal conflicts from twin.temporal_conflicts
        for idx, tc in enumerate(self.twin.temporal_conflicts):
            ev_a = tc.get("event_a", f"event_unknown_{idx}")
            ev_b = tc.get("event_b", f"event_unknown_{idx}")
            conflicts.append(
                EvidenceConflict(
                    conflict_id=f"conf_temp_{uuid.uuid4().hex[:8]}",
                    case_id=self.case_id,
                    conflict_type=ConflictType.TEMPORAL_CONFLICT,
                    subject=f"Temporal inconsistency between {ev_a} and {ev_b}",
                    evidence_a_id=ev_a,
                    evidence_b_id=ev_b,
                    claim_ids=list(tc.get("related_claim_ids", [])),
                    description=tc.get("reason", "Chronological sequence conflict detected"),
                    severity=ConflictSeverity.MEDIUM,
                    uncertainty=0.4,
                    status="OPEN_FOR_REVIEW",
                )
            )

        # 4. Text and numeric inspection between SafeEvidenceRefs
        refs = list(self.twin.evidence_refs.values())
        for i in range(len(refs)):
            for j in range(i + 1, len(refs)):
                ref_a = refs[i]
                ref_b = refs[j]
                pair_key = tuple(sorted([ref_a.evidence_id, ref_b.evidence_id]))
                if any(k[:2] == pair_key for k in seen_pairs):
                    continue

                text_conflicts = self._analyze_text_pair(ref_a, ref_b)
                for tc in text_conflicts:
                    seen_pairs.add(pair_key + (tc.conflict_type.value,))
                    conflicts.append(tc)

        return ConflictSet(case_id=self.case_id, conflicts=conflicts)

    def _map_phase2_type(self, p2_type: Phase2ContradictionType) -> ConflictType:
        mapping = {
            Phase2ContradictionType.DIRECT_CONTRADICTION: ConflictType.DIRECT_CONTRADICTION,
            Phase2ContradictionType.NUMERIC_CONFLICT: ConflictType.NUMERIC_CONFLICT,
            Phase2ContradictionType.TEMPORAL_CONFLICT: ConflictType.TEMPORAL_CONFLICT,
            Phase2ContradictionType.IDENTITY_CONFLICT: ConflictType.IDENTITY_CONFLICT,
            Phase2ContradictionType.LOCATION_CONFLICT: ConflictType.LOCATION_CONFLICT,
            Phase2ContradictionType.POSSIBLE_CONTRADICTION: ConflictType.POSSIBLE_CONTRADICTION,
            Phase2ContradictionType.UNRESOLVED: ConflictType.UNRESOLVED,
        }
        return mapping.get(p2_type, ConflictType.UNRESOLVED)

    def _find_claims_for_evidence_pair(self, id_a: str, id_b: str) -> list[str]:
        claims: set[str] = set()
        for claim in self.twin.claims.values():
            if id_a in claim.supporting_evidence_ids or id_a in claim.contradicting_evidence_ids:
                claims.add(claim.claim_id)
            if id_b in claim.supporting_evidence_ids or id_b in claim.contradicting_evidence_ids:
                claims.add(claim.claim_id)
        return sorted(claims)

    def _analyze_text_pair(self, ref_a: Any, ref_b: Any) -> list[EvidenceConflict]:
        results: list[EvidenceConflict] = []
        text_a = getattr(ref_a, "sanitized_text", "")
        text_b = getattr(ref_b, "sanitized_text", "")
        if not text_a or not text_b:
            return results

        # Simple numeric conflict detection on amounts/dates
        amt_pattern = re.compile(r"(\$|INR|Rs\.?|USD)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(INR|USD|dollars|rupees)?", re.IGNORECASE)
        amts_a = {m.group(0).strip() for m in amt_pattern.finditer(text_a) if len(m.group(0).strip()) > 2}
        amts_b = {m.group(0).strip() for m in amt_pattern.finditer(text_b) if len(m.group(0).strip()) > 2}

        # If both mention amounts but have zero overlap and high textual topic similarity
        if amts_a and amts_b and not (amts_a & amts_b):
            # Check for keyword overlap like "settlement", "payment", "salary", "consideration"
            keywords = {"settlement", "payment", "fee", "penalty", "damage", "rent", "loan"}
            overlap = (set(text_a.lower().split()) & set(text_b.lower().split())) & keywords
            if overlap:
                results.append(
                    EvidenceConflict(
                        conflict_id=f"conf_num_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        conflict_type=ConflictType.NUMERIC_CONFLICT,
                        subject=f"Numeric disparity regarding {', '.join(sorted(overlap))}",
                        evidence_a_id=ref_a.evidence_id,
                        evidence_b_id=ref_b.evidence_id,
                        claim_ids=self._find_claims_for_evidence_pair(ref_a.evidence_id, ref_b.evidence_id),
                        description=f"Evidence {ref_a.evidence_id} mentions {list(amts_a)[:3]} while {ref_b.evidence_id} mentions {list(amts_b)[:3]} regarding {list(overlap)[0]}",
                        supporting_text_refs=[f"[{ref_a.evidence_id}] {list(amts_a)[:2]}", f"[{ref_b.evidence_id}] {list(amts_b)[:2]}"],
                        severity=ConflictSeverity.MEDIUM,
                        uncertainty=0.3,
                        status="OPEN_FOR_REVIEW",
                    )
                )

        return results
