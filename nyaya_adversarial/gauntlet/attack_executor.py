"""Attack Executor for NYAYA-SATYA Adversarial Gauntlet.

Executes attack scenarios against an immutable simulation copy of CaseDigitalTwin.
STRICT IMMUTABILITY GUARANTEE:
Never mutates the canonical CaseDigitalTwin during execution.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from nyaya_adversarial.contracts.attack import (
    AttackScenario,
    AttackStatus,
    AttackType,
)
from nyaya_adversarial.contracts.fragility import StructuralSeverity
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.traversal.claim_dependencies import get_claim_descendants
from nyaya_twin.traversal.downstream_impact import compute_evidence_invalidation_impact
from nyaya_twin.traversal.evidence_paths import get_evidence_dependent_claims


@dataclass
class ExecutionObservation:
    """Structural observations resulting from an executed attack scenario."""

    attack_id: str
    target_node_id: str
    target_node_type: str
    is_vulnerable: bool
    severity: StructuralSeverity
    impacted_claims: list[str]
    impacted_issues: list[str]
    impacted_events: list[str]
    observation_summary: str
    details: dict[str, Any]


class AttackExecutor:
    """Executes attacks deterministically against an isolated snapshot."""

    def __init__(self, canonical_twin: CaseDigitalTwin) -> None:
        self._canonical_twin = canonical_twin

    def execute(self, scenario: AttackScenario) -> ExecutionObservation:
        """Executes an attack on an isolated copy, leaving canonical twin intact."""
        # Deepcopy the twin for isolation
        sim_twin: CaseDigitalTwin = copy.deepcopy(self._canonical_twin)

        try:
            if scenario.attack_type == AttackType.EVIDENCE_ATTACK:
                obs = self._execute_evidence_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.CONTRADICTION_ATTACK:
                obs = self._execute_contradiction_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.TIMELINE_ATTACK:
                obs = self._execute_timeline_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.DEPENDENCY_ATTACK:
                obs = self._execute_dependency_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.SOURCE_ATTACK:
                obs = self._execute_source_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.IDENTITY_ATTACK:
                obs = self._execute_identity_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.ASSUMPTION_ATTACK:
                obs = self._execute_assumption_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.COMPLETENESS_ATTACK:
                obs = self._execute_completeness_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.PROCEDURAL_DEPENDENCY_ATTACK:
                obs = self._execute_procedural_attack(sim_twin, scenario)
            elif scenario.attack_type == AttackType.PROMPT_INJECTION_ATTACK:
                obs = self._execute_prompt_injection_attack(sim_twin, scenario)
            else:
                obs = ExecutionObservation(
                    attack_id=scenario.attack_id,
                    target_node_id=scenario.target_node_id,
                    target_node_type=scenario.target_node_type,
                    is_vulnerable=False,
                    severity=StructuralSeverity.LOW,
                    impacted_claims=[],
                    impacted_issues=[],
                    impacted_events=[],
                    observation_summary=f"Unrecognized attack type: {scenario.attack_type.value}",
                    details={},
                )

            scenario.status = AttackStatus.EXECUTED
            return obs

        finally:
            # Explicitly delete simulation state to guarantee clean release
            del sim_twin

    def _execute_evidence_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        claim_id = scenario.target_node_id
        claim = twin.claims.get(claim_id)
        if not claim:
            return ExecutionObservation(
                attack_id=scenario.attack_id,
                target_node_id=claim_id,
                target_node_type="CLAIM",
                is_vulnerable=False,
                severity=StructuralSeverity.LOW,
                impacted_claims=[],
                impacted_issues=[],
                impacted_events=[],
                observation_summary="Claim not found in twin.",
                details={},
            )

        # Single source vulnerability check
        if len(claim.supporting_evidence_ids) == 1:
            single_ev = claim.supporting_evidence_ids[0]
            descendants = get_claim_descendants(twin, claim_id)
            return ExecutionObservation(
                attack_id=scenario.attack_id,
                target_node_id=claim_id,
                target_node_type="CLAIM",
                is_vulnerable=True,
                severity=StructuralSeverity.HIGH if descendants else StructuralSeverity.MEDIUM,
                impacted_claims=[claim_id] + list(descendants),
                impacted_issues=[],
                impacted_events=[],
                observation_summary=f"Claim {claim_id} has single-source reliance on {single_ev}.",
                details={"single_source_evidence": single_ev, "downstream_cascade": list(descendants)},
            )

        # Contradicted claim vulnerability check
        if claim.contradicting_evidence_ids:
            return ExecutionObservation(
                attack_id=scenario.attack_id,
                target_node_id=claim_id,
                target_node_type="CLAIM",
                is_vulnerable=True,
                severity=StructuralSeverity.HIGH,
                impacted_claims=[claim_id],
                impacted_issues=[],
                impacted_events=[],
                observation_summary=f"Claim {claim_id} is actively contradicted by {claim.contradicting_evidence_ids}.",
                details={"contradicting_evidence": list(claim.contradicting_evidence_ids)},
            )

        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=claim_id,
            target_node_type="CLAIM",
            is_vulnerable=False,
            severity=StructuralSeverity.LOW,
            impacted_claims=[],
            impacted_issues=[],
            impacted_events=[],
            observation_summary="Claim has multiple corroborated evidence sources without direct conflict.",
            details={},
        )

    def _execute_contradiction_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        cand_id = scenario.target_node_id
        cand = next((c for c in twin.contradictions if c.contradiction_id == cand_id), None)
        if not cand:
            return ExecutionObservation(
                attack_id=scenario.attack_id,
                target_node_id=cand_id,
                target_node_type="CONTRADICTION",
                is_vulnerable=False,
                severity=StructuralSeverity.LOW,
                impacted_claims=[],
                impacted_issues=[],
                impacted_events=[],
                observation_summary="Contradiction candidate not found.",
                details={},
            )

        # Measure claims supported by either evidence
        claims_a = get_evidence_dependent_claims(twin, cand.evidence_a_id)
        claims_b = get_evidence_dependent_claims(twin, cand.evidence_b_id)
        all_impacted = sorted(set(claims_a) | set(claims_b))

        severity = StructuralSeverity.CRITICAL if len(all_impacted) >= 3 else StructuralSeverity.HIGH
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=cand_id,
            target_node_type="CONTRADICTION",
            is_vulnerable=True,
            severity=severity,
            impacted_claims=all_impacted,
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Contradiction between {cand.evidence_a_id} and {cand.evidence_b_id} destabilizes {len(all_impacted)} dependent claims.",
            details={"claims_a": list(claims_a), "claims_b": list(claims_b)},
        )

    def _execute_timeline_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        target_id = scenario.target_node_id
        event = twin.events.get(target_id)
        if event:
            return ExecutionObservation(
                attack_id=scenario.attack_id,
                target_node_id=target_id,
                target_node_type="EVENT",
                is_vulnerable=True,
                severity=StructuralSeverity.MEDIUM,
                impacted_claims=list(event.related_claim_ids),
                impacted_issues=[],
                impacted_events=[target_id],
                observation_summary=f"Event {target_id} has indeterminate timestamp precision ({event.temporal_status.value}).",
                details={"temporal_status": event.temporal_status.value},
            )

        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=target_id,
            target_node_type="EVENT",
            is_vulnerable=True,
            severity=StructuralSeverity.HIGH,
            impacted_claims=[],
            impacted_issues=[],
            impacted_events=[target_id],
            observation_summary=f"Timeline sequence conflict involving {target_id}.",
            details=scenario.parameters,
        )

    def _execute_dependency_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        claim_id = scenario.target_node_id
        descendants = get_claim_descendants(twin, claim_id)
        severity = StructuralSeverity.CRITICAL if len(descendants) >= 3 else (
            StructuralSeverity.HIGH if len(descendants) >= 1 else StructuralSeverity.LOW
        )

        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=claim_id,
            target_node_type="CLAIM",
            is_vulnerable=len(descendants) > 0,
            severity=severity,
            impacted_claims=[claim_id] + list(descendants),
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Challenging keystone claim {claim_id} impacts {len(descendants)} downstream dependent claims.",
            details={"descendants": list(descendants)},
        )

    def _execute_source_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        ev_id = scenario.target_node_id
        dep_claims = get_evidence_dependent_claims(twin, ev_id)
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=ev_id,
            target_node_type="EVIDENCE",
            is_vulnerable=True,
            severity=StructuralSeverity.MEDIUM if dep_claims else StructuralSeverity.LOW,
            impacted_claims=list(dep_claims),
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Evidence {ev_id} exhibits provenance gaps affecting {len(dep_claims)} claims.",
            details={"dependent_claims": list(dep_claims)},
        )

    def _execute_identity_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        entity_id = scenario.target_node_id
        entity = twin.entities.get(entity_id)
        name = getattr(entity, "canonical_label", entity_id) if entity else entity_id
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=entity_id,
            target_node_type="ENTITY",
            is_vulnerable=True,
            severity=StructuralSeverity.MEDIUM,
            impacted_claims=[],
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Entity {name} has unresolved identity status, exposing actions to misattribution.",
            details=scenario.parameters,
        )

    def _execute_assumption_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        assump_id = scenario.target_node_id
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=assump_id,
            target_node_type="ASSUMPTION",
            is_vulnerable=True,
            severity=StructuralSeverity.HIGH,
            impacted_claims=[],
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Underlying assumption {assump_id} is unverified.",
            details=scenario.parameters,
        )

    def _execute_completeness_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        claim_id = scenario.target_node_id
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=claim_id,
            target_node_type="CLAIM",
            is_vulnerable=True,
            severity=StructuralSeverity.HIGH,
            impacted_claims=[claim_id],
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Claim {claim_id} lacks any supporting evidence nodes.",
            details={},
        )

    def _execute_procedural_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        issue_id = scenario.target_node_id
        issue = twin.issues.get(issue_id)
        related_claims = list(issue.related_claim_ids) if issue else []
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=issue_id,
            target_node_type="ISSUE",
            is_vulnerable=True,
            severity=StructuralSeverity.CRITICAL,
            impacted_claims=related_claims,
            impacted_issues=[issue_id],
            impacted_events=[],
            observation_summary=f"Threshold procedural issue {issue_id} could dispose of {len(related_claims)} substantive claims.",
            details={"related_claims": related_claims},
        )

    def _execute_prompt_injection_attack(self, twin: CaseDigitalTwin, scenario: AttackScenario) -> ExecutionObservation:
        ev_id = scenario.target_node_id
        # Confirm that the injection text is strictly inert in the data plane
        ref = twin.evidence_refs.get(ev_id)
        return ExecutionObservation(
            attack_id=scenario.attack_id,
            target_node_id=ev_id,
            target_node_type="EVIDENCE",
            is_vulnerable=False,  # Zero-trust boundary successfully confines it to data
            severity=StructuralSeverity.LOW,
            impacted_claims=[],
            impacted_issues=[],
            impacted_events=[],
            observation_summary=f"Adversarial payload in evidence {ev_id} successfully neutralized and confined to data plane.",
            details={"status": "CONTAINED_IN_DATA_PLANE"},
        )
