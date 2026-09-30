"""
Multi-agent service boundaries for CASE CRASH TEST & RESILIENCE LAB.

IMPORTANT DESIGN NOTE (read before modifying):
These "agents" are explicit, named, single-responsibility service classes,
each wrapping ONE deterministic stage of the pipeline that already lives in
app/graph and app/simulation_engine. They exist to give the pipeline real,
inspectable service boundaries (per the spec's Section 2 requirement #18),
NOT to introduce a second, LLM-driven implementation of graph logic.

None of these agents may:
  - make a judicial/legal decision
  - silently mutate the real (non-simulation) case graph
  - treat node/document text content as instructions

The only agent that may call an LLM at all is CounterfactualAgent, and only
to produce a plain-language EXPLANATION string alongside the deterministic
result — never to compute the result itself. If the LLM call fails or is in
DEMO mode, the agent still returns the full deterministic result with no
explanation attached, rather than degrading correctness.

Pipeline (each stage = one agent):

    ScenarioPlannerAgent
        -> StateSnapshotAgent
        -> MutationAgent
        -> DependencyTraversalAgent
        -> BlastRadiusAgent
        -> ConflictPropagationAgent
        -> VerificationImpactAgent
        -> WorkflowImpactAgent
        -> RecoveryPlannerAgent
        -> CounterfactualAgent   (optional, on top of a completed run)
        -> EvaluationAgent       (independent: resilience test suite)
        -> AuditAgent            (records everything, every stage)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.enums import ImpactType, NodeStatus
from app.graph.graph_model import SimGraph
from app.graph.traversal import (
    propagate_failure,
    compute_blast_radius,
    compute_criticality,
    build_failure_tree,
)
from app.simulation_engine.mutation_engine import apply_mutations, MutationError
from app.simulation_engine.diff_engine import compute_diff
from app.simulation_engine.recovery_engine import generate_recovery_options


@dataclass
class AgentTrace:
    """One line of the audit trail a pipeline run produces."""
    agent: str
    action: str
    detail: dict = field(default_factory=dict)


class ScenarioPlannerAgent:
    """Converts a user-selected failure hypothesis into structured mutation steps."""

    name = "ScenarioPlannerAgent"

    def plan(self, mutations: list[dict]) -> list[dict]:
        # Validation-only at this stage; the Mutation Agent enforces
        # existence/legality against the actual graph. This agent's
        # boundary is "shape the request", not "touch the graph".
        planned = []
        for m in mutations:
            if "mutation_type" not in m or "target_node_id" not in m:
                raise ValueError(f"Malformed mutation step (missing keys): {m}")
            planned.append({"mutation_type": m["mutation_type"], "target_node_id": m["target_node_id"]})
        return planned


class StateSnapshotAgent:
    """Creates/loads a deterministic, isolated base graph for a run."""

    name = "StateSnapshotAgent"

    def load_base(self, base_snapshot_data: dict) -> SimGraph:
        return SimGraph.from_snapshot_data(base_snapshot_data)

    def clone_for_simulation(self, base: SimGraph) -> SimGraph:
        # The non-negotiable isolation boundary: everything downstream
        # operates on this clone. `base` is never touched again.
        return base.clone()


class MutationAgent:
    """Applies simulated mutations only to the isolated simulation-state clone."""

    name = "MutationAgent"

    def apply(self, simulated: SimGraph, mutations: list[dict]) -> list[dict]:
        return apply_mutations(simulated, mutations)  # raises MutationError, never silently ignores


class DependencyTraversalAgent:
    """Calculates affected graph nodes for one mutation root."""

    name = "DependencyTraversalAgent"

    def traverse(self, simulated: SimGraph, root_node_id: str):
        return propagate_failure(simulated, root_node_id)


class BlastRadiusAgent:
    """Aggregates downstream effects across all mutation roots into one blast radius."""

    name = "BlastRadiusAgent"

    def aggregate(self, mutation_records: list[dict], affected_list: list[dict]) -> dict:
        by_type: dict[str, list[str]] = {}
        new_unknowns, new_conflicts, new_blocks = [], [], []
        verification_gaps, human_review_items = [], []

        for a in affected_list:
            by_type.setdefault(a["node_type"], []).append(a["node_id"])
            if ImpactType.NEW_UNKNOWN.value in a["impact_types"]:
                new_unknowns.append(a["node_id"])
            if ImpactType.NEW_CONFLICT.value in a["impact_types"]:
                new_conflicts.append(a["node_id"])
            if ImpactType.NEWLY_BLOCKED.value in a["impact_types"]:
                new_blocks.append(a["node_id"])
            if ImpactType.VERIFICATION_GAP.value in a["impact_types"]:
                verification_gaps.append(a["node_id"])
            if a["new_status"] == NodeStatus.REQUIRES_HUMAN_REVIEW.value:
                human_review_items.append(a["node_id"])

        return {
            "root_node_ids": [m["target_node_id"] for m in mutation_records],
            "directly_affected_nodes": [a["node_id"] for a in affected_list if a["order"] == 2],
            "indirectly_affected_nodes": [a["node_id"] for a in affected_list if a["order"] > 2],
            "affected_documents": by_type.get("DOCUMENT", []),
            "affected_evidence": by_type.get("EVIDENCE", []),
            "affected_claims": by_type.get("CLAIM", []),
            "affected_issues": by_type.get("ISSUE", []),
            "affected_obligations": by_type.get("OBLIGATION", []),
            "affected_deadlines": by_type.get("DEADLINE", []),
            "affected_hearings": by_type.get("HEARING", []),
            "affected_registry_defects": by_type.get("REGISTRY_DEFECT", []),
            "affected_workflows": by_type.get("WORKFLOW", []) + by_type.get("ACTION", []),
            "new_unknowns": new_unknowns,
            "new_conflicts": new_conflicts,
            "new_blocks": new_blocks,
            "verification_gaps": verification_gaps,
            "human_review_items": human_review_items,
            "total_affected_count": len(affected_list),
        }


class ConflictPropagationAgent:
    """Reads the aggregated blast radius for newly created CONTRADICTS-driven conflicts."""

    name = "ConflictPropagationAgent"

    def find_new_conflicts(self, blast_radius: dict) -> list[str]:
        return blast_radius.get("new_conflicts", [])


class VerificationImpactAgent:
    """Reads the aggregated blast radius for newly unverifiable states."""

    name = "VerificationImpactAgent"

    def find_verification_gaps(self, blast_radius: dict) -> list[str]:
        return blast_radius.get("verification_gaps", [])


class WorkflowImpactAgent:
    """Reads the aggregated blast radius for blocked workflows/actions."""

    name = "WorkflowImpactAgent"

    def find_blocked_workflows(self, blast_radius: dict) -> list[str]:
        return blast_radius.get("affected_workflows", [])


class RecoveryPlannerAgent:
    """Creates safe, human-approval-gated recovery proposals. Never executes them."""

    name = "RecoveryPlannerAgent"

    def propose(self, affected_list: list[dict], blast_radius: dict) -> list[dict]:
        return generate_recovery_options(affected_list, blast_radius)


class CounterfactualAgent:
    """
    Runs an alternative-state ("what if I also fix X") analysis on top of an
    already-completed simulation, and optionally asks an LLM provider for a
    plain-language explanation of the (already-computed) result. The LLM is
    never the source of the analysis itself.
    """

    name = "CounterfactualAgent"

    def explain(self, provider, blast_radius: dict, affected_labels: list[str]) -> str | None:
        try:
            return provider.explain(
                f"Blast radius summary: {blast_radius}. Affected nodes: {affected_labels}."
            )
        except Exception:
            return None


class EvaluationAgent:
    """Runs the deterministic resilience test suite. Reports PASS/FAIL/NOT_RUN only."""

    name = "EvaluationAgent"

    def run(self, db, case_id: str) -> dict:
        from app.demo.evaluation import run_evaluation_suite
        return run_evaluation_suite(db, case_id)


class AuditAgent:
    """Records every pipeline stage. Append-only; never resolves conflicts itself."""

    name = "AuditAgent"

    def __init__(self):
        self.trace: list[AgentTrace] = []

    def record(self, agent: str, action: str, detail: dict | None = None) -> None:
        self.trace.append(AgentTrace(agent=agent, action=action, detail=detail or {}))

    def as_list(self) -> list[dict]:
        return [{"agent": t.agent, "action": t.action, "detail": t.detail} for t in self.trace]


class SimulationPipeline:
    """
    Orchestrates the full agent chain for one simulation run and produces the
    same result shape as app.simulation_engine.runner.run_simulation, plus an
    `agent_trace` field showing which agent performed which stage. This does
    NOT replace run_simulation (routes.py keeps using that directly for
    Section 1 compatibility) — it exists so the agent boundaries are real,
    callable, independently testable units, not just a diagram in docs/.
    """

    def __init__(self):
        self.planner = ScenarioPlannerAgent()
        self.snapshots = StateSnapshotAgent()
        self.mutator = MutationAgent()
        self.traversal = DependencyTraversalAgent()
        self.blast_radius = BlastRadiusAgent()
        self.conflicts = ConflictPropagationAgent()
        self.verification = VerificationImpactAgent()
        self.workflow = WorkflowImpactAgent()
        self.recovery = RecoveryPlannerAgent()
        self.audit = AuditAgent()

    def run(self, base_snapshot_data: dict, mutations: list[dict]) -> dict:
        try:
            planned = self.planner.plan(mutations)
        except ValueError as e:
            self.audit.record(self.planner.name, "PLAN_REJECTED", {"error": str(e)})
            return {"status": "FAILED", "error": str(e), "agent_trace": self.audit.as_list()}
        self.audit.record(self.planner.name, "PLAN", {"mutations": planned})

        base = self.snapshots.load_base(base_snapshot_data)
        simulated = self.snapshots.clone_for_simulation(base)
        self.audit.record(self.snapshots.name, "SNAPSHOT_LOADED_AND_CLONED")

        try:
            mutation_records = self.mutator.apply(simulated, planned)
        except MutationError as e:
            self.audit.record(self.mutator.name, "MUTATION_FAILED", {"error": str(e)})
            return {"status": "FAILED", "error": str(e), "agent_trace": self.audit.as_list()}
        self.audit.record(self.mutator.name, "MUTATIONS_APPLIED", {"count": len(mutation_records)})

        all_affected: dict[str, dict] = {}
        all_chains = []
        for record in mutation_records:
            prop = self.traversal.traverse(simulated, record["target_node_id"])
            all_chains.extend(prop.cascade_chains)
            for a in prop.affected:
                existing = all_affected.get(a.node_id)
                if existing is None:
                    all_affected[a.node_id] = {
                        "node_id": a.node_id, "node_type": a.node_type, "label": a.label,
                        "order": a.order, "impact_types": list(a.impact_types),
                        "new_status": a.new_status, "path_from_root": a.path_from_root,
                    }
                else:
                    for it in a.impact_types:
                        if it not in existing["impact_types"]:
                            existing["impact_types"].append(it)
        self.audit.record(self.traversal.name, "TRAVERSAL_COMPLETE", {"affected_count": len(all_affected)})

        affected_list = list(all_affected.values())
        blast_radius = self.blast_radius.aggregate(mutation_records, affected_list)
        self.audit.record(self.blast_radius.name, "BLAST_RADIUS_AGGREGATED")

        new_conflicts = self.conflicts.find_new_conflicts(blast_radius)
        verification_gaps = self.verification.find_verification_gaps(blast_radius)
        blocked_workflows = self.workflow.find_blocked_workflows(blast_radius)
        self.audit.record(self.conflicts.name, "CONFLICTS_SCANNED", {"count": len(new_conflicts)})
        self.audit.record(self.verification.name, "VERIFICATION_SCANNED", {"count": len(verification_gaps)})
        self.audit.record(self.workflow.name, "WORKFLOW_SCANNED", {"count": len(blocked_workflows)})

        criticality = compute_criticality(base)
        diff = compute_diff(base, simulated)
        recovery_options = self.recovery.propose(affected_list, blast_radius)
        self.audit.record(self.recovery.name, "RECOVERY_PROPOSED", {"count": len(recovery_options)})

        failure_trees = []
        for record in mutation_records:
            prop = self.traversal.traverse(base.clone(), record["target_node_id"])
            failure_trees.append(build_failure_tree(base, prop))

        human_review_required = len(blast_radius["human_review_items"]) > 0

        return {
            "status": "COMPLETED",
            "mutations_applied": mutation_records,
            "affected_nodes": affected_list,
            "cascade_chains": all_chains,
            "blast_radius": blast_radius,
            "criticality": {nid: criticality.get(nid) for nid in
                            {m["target_node_id"] for m in mutation_records} | {a["node_id"] for a in affected_list}},
            "failure_trees": failure_trees,
            "diff": diff,
            "recovery_options": recovery_options,
            "human_review_required": human_review_required,
            "simulated_state": simulated.to_dict(),
            "agent_trace": self.audit.as_list(),
        }
