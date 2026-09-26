"""Independent attacker for NYAYA-SATYA Re-Attack Engine.

Generates adversarial attack probes targeting the post-repair CaseDigitalTwin state.
Operates completely independent of the repair generator.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.attack import AttackScenario, AttackStatus, AttackType
from nyaya_reattack.attack_profile import AttackProfile, ReAttackStrategy
from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus


class IndependentAttacker:
    """Generates rigorous attack scenarios against repaired twin states."""

    def __init__(self, profile: AttackProfile | None = None) -> None:
        self.profile = profile or AttackProfile(profile_id="default_reattack_profile")

    def generate_reattacks(
        self,
        repaired_twin: CaseDigitalTwin,
        repair: RepairCandidate,
    ) -> list[AttackScenario]:
        """Generate targeted re-attack scenarios against the post-repair state."""
        scenarios: list[AttackScenario] = []
        case_id = repaired_twin.case_id

        # 1. Target verification probe: attack the exact repair target to verify if the vulnerability persists
        target_claim_id = repair.target_claim_id
        if target_claim_id and target_claim_id in repaired_twin.claims:
            claim = repaired_twin.claims[target_claim_id]
            scenarios.append(
                AttackScenario(
                    attack_id=f"ATK_VERIF_{uuid.uuid4().hex[:8]}",
                    case_id=case_id,
                    attack_type=AttackType.EVIDENCE_ATTACK,
                    target_node_id=target_claim_id,
                    target_node_type="CLAIM",
                    premise=f"Challenging target claim {target_claim_id} after repair {repair.repair_id}",
                    attack_question=f"Does claim {target_claim_id} remain unsupported or fragile despite the proposed repair?",
                    required_evidence=list(claim.supporting_evidence_ids),
                )
            )

        # 2. Collateral contradiction scan: check for newly surfaced or unresolved contradictions
        for cid, claim in repaired_twin.claims.items():
            if claim.contradicting_evidence_ids:
                scenarios.append(
                    AttackScenario(
                        attack_id=f"ATK_CONTR_{uuid.uuid4().hex[:8]}",
                        case_id=case_id,
                        attack_type=AttackType.CONTRADICTION_ATTACK,
                        target_node_id=cid,
                        target_node_type="CLAIM",
                        premise=f"Claim {cid} has contradicting evidence references in repaired twin",
                        attack_question=f"Can contradictory evidence against claim {cid} be reconciled?",
                        required_evidence=list(claim.contradicting_evidence_ids),
                    )
                )

        # 3. Unsupported assertion probe across the repaired twin
        for cid, claim in repaired_twin.claims.items():
            if not claim.supporting_evidence_ids:
                scenarios.append(
                    AttackScenario(
                        attack_id=f"ATK_UNSUP_{uuid.uuid4().hex[:8]}",
                        case_id=case_id,
                        attack_type=AttackType.COMPLETENESS_ATTACK,
                        target_node_id=cid,
                        target_node_type="CLAIM",
                        premise=f"Claim {cid} lacks supporting evidence in repaired twin",
                        attack_question=f"Is claim {cid} an ungrounded factual assertion?",
                    )
                )

        # 4. Timeline instability probe
        for eid, event in repaired_twin.events.items():
            if event.time_precision.value == "UNKNOWN" or event.temporal_status.value == "CONFLICTED":
                scenarios.append(
                    AttackScenario(
                        attack_id=f"ATK_TIME_{uuid.uuid4().hex[:8]}",
                        case_id=case_id,
                        attack_type=AttackType.TIMELINE_ATTACK,
                        target_node_id=eid,
                        target_node_type="EVENT",
                        premise=f"Event {eid} has uncertain or conflicted temporal status",
                        attack_question=f"Does temporal ambiguity in event {eid} undermine sequence assertions?",
                    )
                )

        # 5. Causal dependency break attack
        for rid, rel in repaired_twin.relationships.items():
            if rel.relationship_type.value == "DEPENDS_ON":
                scenarios.append(
                    AttackScenario(
                        attack_id=f"ATK_DEP_{uuid.uuid4().hex[:8]}",
                        case_id=case_id,
                        attack_type=AttackType.DEPENDENCY_ATTACK,
                        target_node_id=rel.source_id,
                        target_node_type="CLAIM",
                        premise=f"Dependency relationship {rid} between {rel.source_id} and {rel.target_id}",
                        attack_question=f"Does failure of prerequisite {rel.target_id} invalidate {rel.source_id}?",
                    )
                )

        return scenarios
