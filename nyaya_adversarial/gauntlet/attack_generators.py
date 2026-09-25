"""Attack Scenario Generators for NYAYA-SATYA Adversarial Gauntlet.

Generates structured, reproducible AttackScenarios across 10 distinct attack classes:
1. EVIDENCE ATTACK
2. CONTRADICTION ATTACK
3. TIMELINE ATTACK
4. DEPENDENCY ATTACK
5. SOURCE ATTACK
6. IDENTITY ATTACK
7. ASSUMPTION ATTACK
8. COMPLETENESS ATTACK
9. PROCEDURAL DEPENDENCY ATTACK
10. PROMPT INJECTION / TRUST BOUNDARY ATTACK
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from nyaya_adversarial.contracts.assumption import AssumptionRegistry
from nyaya_adversarial.contracts.attack import AttackScenario, AttackStatus, AttackType
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus
from nyaya_twin.contracts.issues import Issue, IssueStatus
from nyaya_twin.contracts.relationships import RelationshipType
from nyaya_twin.traversal.claim_dependencies import get_claim_descendants
from nyaya_twin.traversal.evidence_paths import get_evidence_dependent_claims


class AttackGeneratorSuite:
    """Deterministic generator producing 10 attack classes against a CaseDigitalTwin."""

    def __init__(
        self,
        twin: CaseDigitalTwin,
        assumption_registry: AssumptionRegistry | None = None,
    ) -> None:
        self.twin = twin
        self.case_id = twin.case_id
        self.assumptions = assumption_registry or AssumptionRegistry(case_id=twin.case_id)

    def generate_all_attacks(self) -> list[AttackScenario]:
        """Generates all applicable attack scenarios across the 10 attack classes."""
        attacks: list[AttackScenario] = []
        attacks.extend(self.generate_evidence_attacks())
        attacks.extend(self.generate_contradiction_attacks())
        attacks.extend(self.generate_timeline_attacks())
        attacks.extend(self.generate_dependency_attacks())
        attacks.extend(self.generate_source_attacks())
        attacks.extend(self.generate_identity_attacks())
        attacks.extend(self.generate_assumption_attacks())
        attacks.extend(self.generate_completeness_attacks())
        attacks.extend(self.generate_procedural_attacks())
        attacks.extend(self.generate_prompt_injection_attacks())
        return attacks

    # 1. EVIDENCE ATTACK
    def generate_evidence_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for claim in self.twin.claims.values():
            if not claim.supporting_evidence_ids:
                continue

            # Vector: single-source reliance or extraction uncertainty
            if len(claim.supporting_evidence_ids) == 1:
                ev_id = claim.supporting_evidence_ids[0]
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_ev_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.EVIDENCE_ATTACK,
                        target_node_id=claim.claim_id,
                        target_node_type="CLAIM",
                        premise=f"Claim {claim.claim_id} depends entirely on single evidence source {ev_id}.",
                        attack_question=f"What evidence would make claim {claim.claim_id} unreliable if {ev_id} is challenged or discredited?",
                        required_evidence=[ev_id],
                        expected_observation="Claim becomes completely unsupported if sole source fails.",
                        parameters={"single_source_evidence": ev_id},
                    )
                )

            # Vector: stale or conflicting document
            if claim.contradicting_evidence_ids:
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_ev_conf_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.EVIDENCE_ATTACK,
                        target_node_id=claim.claim_id,
                        target_node_type="CLAIM",
                        premise=f"Claim {claim.claim_id} faces {len(claim.contradicting_evidence_ids)} directly contradicting evidence reference(s).",
                        attack_question=f"How can claim {claim.claim_id} withstand contrary evidence {claim.contradicting_evidence_ids}?",
                        required_evidence=list(claim.contradicting_evidence_ids),
                        expected_observation="Claim is contested and may require independent corroboration.",
                        parameters={"contradicting_ids": list(claim.contradicting_evidence_ids)},
                    )
                )

        return attacks

    # 2. CONTRADICTION ATTACK
    def generate_contradiction_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for cand in self.twin.contradictions:
            attacks.append(
                AttackScenario(
                    attack_id=f"atk_contra_{cand.contradiction_id}",
                    case_id=self.case_id,
                    attack_type=AttackType.CONTRADICTION_ATTACK,
                    target_node_id=cand.contradiction_id,
                    target_node_type="CONTRADICTION",
                    premise=f"Direct conflict exists between {cand.evidence_a_id} and {cand.evidence_b_id}.",
                    attack_question=f"Does the contradiction between {cand.evidence_a_id} and {cand.evidence_b_id} fatally undermine claims resting on either source?",
                    required_evidence=[cand.evidence_a_id, cand.evidence_b_id],
                    expected_observation="Mutual contradiction forces reliance on external unaligned corroboration.",
                    provenance_refs=list(cand.provenance_refs),
                    parameters={"type": cand.contradiction_type.value},
                )
            )
        return attacks

    # 3. TIMELINE ATTACK
    def generate_timeline_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        events_list = sorted(
            self.twin.events.values(),
            key=lambda e: (e.temporal_status.value, getattr(e, "event_time", None) or getattr(e, "timestamp", "") or ""),
        )

        for event in events_list:
            e_time = getattr(event, "event_time", None) or getattr(event, "timestamp", None)
            # Check for unanchored or approximate precision
            if not e_time or event.temporal_status.value in ("APPROXIMATE", "UNANCHORED", "UNKNOWN"):
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_time_prec_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.TIMELINE_ATTACK,
                        target_node_id=event.event_id,
                        target_node_type="EVENT",
                        premise=f"Event {event.event_id} has uncertain temporal grounding (status={event.temporal_status.value}).",
                        attack_question=f"Can the sequence of events be legally or factually proven if event {event.event_id} timestamp is indeterminate?",
                        required_evidence=list(event.source_evidence_ids),
                        expected_observation="Event ordering may permit alternative chronological reconstructions.",
                        parameters={"temporal_status": event.temporal_status.value},
                    )
                )

        # Check for sequence conflicts in twin.temporal_conflicts
        for tc in self.twin.temporal_conflicts:
            ev_a = tc.get("event_a", "event_A")
            ev_b = tc.get("event_b", "event_B")
            attacks.append(
                AttackScenario(
                    attack_id=f"atk_time_seq_{uuid.uuid4().hex[:8]}",
                    case_id=self.case_id,
                    attack_type=AttackType.TIMELINE_ATTACK,
                    target_node_id=f"{ev_a}_{ev_b}",
                    target_node_type="EVENT_PAIR",
                    premise=f"Temporal sequence conflict detected between {ev_a} and {ev_b}.",
                    attack_question=f"Could event {ev_b} have occurred prior to or independently of {ev_a}?",
                    expected_observation="Chronological sequence invalidates strict causal dependency.",
                    parameters=tc,
                )
            )

        return attacks

    # 4. DEPENDENCY ATTACK
    def generate_dependency_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for claim in self.twin.claims.values():
            descendants = get_claim_descendants(self.twin, claim.claim_id)
            if len(descendants) >= 1:
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_dep_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.DEPENDENCY_ATTACK,
                        target_node_id=claim.claim_id,
                        target_node_type="CLAIM",
                        premise=f"Claim {claim.claim_id} is a keystone with {len(descendants)} downstream dependent claim(s).",
                        attack_question=f"If claim {claim.claim_id} is refuted, how many downstream claims immediately lose their foundation?",
                        expected_observation=f"Downstream cascade will destabilize {len(descendants)} claims: {descendants[:3]}.",
                        parameters={"descendants": descendants, "count": len(descendants)},
                    )
                )
        return attacks

    # 5. SOURCE ATTACK
    def generate_source_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for ref_id, ref in self.twin.evidence_refs.items():
            provs = getattr(ref, "provenance_refs", [])
            if not provs:
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_src_prov_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.SOURCE_ATTACK,
                        target_node_id=ref_id,
                        target_node_type="EVIDENCE",
                        premise=f"Evidence {ref_id} has no attached unbroken provenance chain.",
                        attack_question=f"Can the authenticity and chain of custody of {ref_id} be challenged under evidentiary standards?",
                        expected_observation="Evidence is vulnerable to admissibility exclusion due to provenance gap.",
                        parameters={"evidence_id": ref_id},
                    )
                )
        return attacks

    # 6. IDENTITY ATTACK
    def generate_identity_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for entity in self.twin.entities.values():
            if entity.status.value in ("UNRESOLVED", "POSSIBLE_MATCH", "ALIAS"):
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_ident_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.IDENTITY_ATTACK,
                        target_node_id=entity.entity_id,
                        target_node_type="ENTITY",
                        premise=f"Entity {getattr(entity, 'canonical_label', entity.entity_id)} (id={entity.entity_id}) status is {entity.status.value}.",
                        attack_question=f"Could actions attributed to {getattr(entity, 'canonical_label', entity.entity_id)} actually have been performed by a distinct legal person?",
                        expected_observation="Identity ambiguity creates defense of mistaken identity or lack of authority.",
                        parameters={"entity_status": entity.status.value},
                    )
                )
        return attacks

    # 7. ASSUMPTION ATTACK
    def generate_assumption_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for assump in self.assumptions.list_all():
            attacks.append(
                AttackScenario(
                    attack_id=f"atk_assump_{uuid.uuid4().hex[:8]}",
                    case_id=self.case_id,
                    attack_type=AttackType.ASSUMPTION_ATTACK,
                    target_node_id=assump.assumption_id,
                    target_node_type="ASSUMPTION",
                    premise=f"Case relies on assumption: '{assump.description}' (status={assump.support_status.value}).",
                    attack_question=f"What happens to dependent claims {assump.related_claim_ids} if assumption '{assump.description}' is false?",
                    expected_observation="Unverified assumption exposes argument to threshold dismissal.",
                    parameters={"assumption_id": assump.assumption_id, "status": assump.support_status.value},
                )
            )
        return attacks

    # 8. COMPLETENESS ATTACK
    def generate_completeness_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        for claim in self.twin.claims.values():
            if not claim.supporting_evidence_ids:
                attacks.append(
                    AttackScenario(
                        attack_id=f"atk_comp_{uuid.uuid4().hex[:8]}",
                        case_id=self.case_id,
                        attack_type=AttackType.COMPLETENESS_ATTACK,
                        target_node_id=claim.claim_id,
                        target_node_type="CLAIM",
                        premise=f"Claim {claim.claim_id} ('{claim.statement[:60]}...') has zero supporting evidence nodes.",
                        attack_question=f"Is claim {claim.claim_id} legally sustainable without any evidentiary substantiation?",
                        expected_observation="Claim is bare assertion and liable to be struck for lack of prima facie evidence.",
                    )
                )
        return attacks

    # 9. PROCEDURAL DEPENDENCY ATTACK
    def generate_procedural_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        # Find threshold issues (e.g. limitation, jurisdiction, maintainability)
        threshold_issues = [
            iss for iss in self.twin.issues.values()
            if any(term in iss.issue_id.upper() or term in iss.title.upper() or term in str(iss.metadata).upper()
                   for term in ("THRESHOLD", "LIMITATION", "JURISDICTION", "MAINTAINABILITY", "PROCEDURAL"))
        ]

        for issue in threshold_issues:
            attacks.append(
                AttackScenario(
                    attack_id=f"atk_proc_{uuid.uuid4().hex[:8]}",
                    case_id=self.case_id,
                    attack_type=AttackType.PROCEDURAL_DEPENDENCY_ATTACK,
                    target_node_id=issue.issue_id,
                    target_node_type="ISSUE",
                    premise=f"Issue {issue.issue_id} is a threshold procedural/jurisdictional gate.",
                    attack_question=f"If threshold issue {issue.issue_id} fails, do all substantive claims collapse regardless of merit?",
                    expected_observation="Adverse threshold ruling disposes of the proceedings prior to merits.",
                    parameters={"issue_id": issue.issue_id},
                )
            )
        return attacks

    # 10. PROMPT INJECTION / TRUST BOUNDARY ATTACK
    def generate_prompt_injection_attacks(self) -> list[AttackScenario]:
        attacks: list[AttackScenario] = []
        # Scan evidence texts for adversarial injection patterns
        injection_patterns = [
            re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
            re.compile(r"system\s*:\s*override", re.IGNORECASE),
            re.compile(r"rule\s+in\s+favor\s+of", re.IGNORECASE),
            re.compile(r"verdict\s*:\s*guilty|liable", re.IGNORECASE),
            re.compile(r"<script.*?>", re.IGNORECASE),
        ]

        for ref_id, ref in self.twin.evidence_refs.items():
            text = getattr(ref, "sanitized_text", "")
            for pat in injection_patterns:
                match = pat.search(text)
                if match:
                    attacks.append(
                        AttackScenario(
                            attack_id=f"atk_inj_{uuid.uuid4().hex[:8]}",
                            case_id=self.case_id,
                            attack_type=AttackType.PROMPT_INJECTION_ATTACK,
                            target_node_id=ref_id,
                            target_node_type="EVIDENCE",
                            premise=f"Adversarial payload detected in evidence {ref_id}: '{match.group(0)}'.",
                            attack_question=f"Can the adversarial string in {ref_id} alter reasoning behavior or escape the data plane?",
                            required_evidence=[ref_id],
                            expected_observation="Adversarial text must remain treated as inert evidentiary data and never executed.",
                            parameters={"matched_pattern": match.group(0)},
                        )
                    )
                    break
        return attacks
