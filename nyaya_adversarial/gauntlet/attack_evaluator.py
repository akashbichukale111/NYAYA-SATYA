"""Attack Evaluator for NYAYA-SATYA Adversarial Gauntlet.

Translates execution observations into structured AdversarialFinding records.
Strictly non-adjudicative: explains structural severity without legal win probabilities.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.attack import AttackScenario, AttackType
from nyaya_adversarial.contracts.fragility import StructuralSeverity
from nyaya_adversarial.contracts.result import AdversarialFinding, FindingType
from nyaya_adversarial.gauntlet.attack_executor import ExecutionObservation


class AttackEvaluator:
    """Evaluates executed attack observations into standardized AdversarialFindings."""

    def evaluate(
        self,
        scenario: AttackScenario,
        observation: ExecutionObservation,
    ) -> AdversarialFinding | None:
        """Formulates an AdversarialFinding if the attack exposed a real structural vulnerability."""
        if not observation.is_vulnerable and observation.severity == StructuralSeverity.LOW:
            # No actionable vulnerability discovered
            return None

        finding_type = self._map_attack_to_finding_type(scenario.attack_type)
        fid = f"find_{uuid.uuid4().hex[:10]}"

        return AdversarialFinding(
            finding_id=fid,
            case_id=scenario.case_id,
            attack_id=scenario.attack_id,
            finding_type=finding_type,
            target_id=scenario.target_node_id,
            severity=observation.severity,
            structural_impact={
                "impacted_claims": observation.impacted_claims,
                "impacted_issues": observation.impacted_issues,
                "impacted_events": observation.impacted_events,
                "details": observation.details,
            },
            evidence_ids=list(scenario.required_evidence),
            claim_ids=list(observation.impacted_claims),
            issue_ids=list(observation.impacted_issues),
            assumptions=[],
            uncertainty=0.3 if observation.severity in (StructuralSeverity.HIGH, StructuralSeverity.CRITICAL) else 0.5,
            explanation=f"[{scenario.attack_type.value}] {observation.observation_summary} (Premise: {scenario.premise})",
            provenance_refs=list(scenario.provenance_refs),
            engine_version="4.0.0",
            status="PENDING_HUMAN_REVIEW",
        )

    def _map_attack_to_finding_type(self, attack_type: AttackType) -> FindingType:
        mapping = {
            AttackType.EVIDENCE_ATTACK: FindingType.SINGLE_SOURCE_DEPENDENCY,
            AttackType.CONTRADICTION_ATTACK: FindingType.CONFLICTING_EVIDENCE,
            AttackType.TIMELINE_ATTACK: FindingType.TIMELINE_CONFLICT,
            AttackType.DEPENDENCY_ATTACK: FindingType.DEPENDENCY_EXPOSURE,
            AttackType.SOURCE_ATTACK: FindingType.PROVENANCE_GAP,
            AttackType.IDENTITY_ATTACK: FindingType.UNRESOLVED,
            AttackType.ASSUMPTION_ATTACK: FindingType.ASSUMPTION_EXPOSED,
            AttackType.COMPLETENESS_ATTACK: FindingType.UNSUPPORTED_CLAIM,
            AttackType.PROCEDURAL_DEPENDENCY_ATTACK: FindingType.DEPENDENCY_EXPOSURE,
            AttackType.PROMPT_INJECTION_ATTACK: FindingType.UNRESOLVED,
        }
        return mapping.get(attack_type, FindingType.UNRESOLVED)
