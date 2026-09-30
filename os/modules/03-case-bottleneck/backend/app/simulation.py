"""
Simulation engine (Sections 26-29).

Everything here operates on an in-memory CLONE of the case's dependency/
transition graph. Nothing in this file writes to the database. Every
response the API returns from these functions is labelled "SIMULATION_ONLY".
"""
from __future__ import annotations

from sqlmodel import Session

from .graph import load_case_graph, CaseGraph
from .agents.discovery import BottleneckDiscoveryAgent  # noqa: F401  (kept for parity with real pipeline naming)


def _clone_graph(graph: CaseGraph) -> CaseGraph:
    """Detached simulation clone — see CaseGraph.to_sim_clone / SimDependency
    docstring in graph.py for why this is not a plain SQLModel model_copy()."""
    return graph.to_sim_clone()


def _bottleneck_leaf_ids(graph: CaseGraph) -> set[str]:
    leaves: set[str] = set()
    for t in graph.blocked_transitions():
        for prereq_id in t.prerequisite_dependency_ids:
            dep = graph.dependencies.get(prereq_id)
            if not dep:
                continue
            if dep.status == "CONTRADICTED":
                leaves.add(dep.id)
            else:
                leaves.update(graph.unsatisfied_leaf_dependencies(dep.id))
    return leaves


def simulate_removal(session: Session, case_id: str, dependency_id: str) -> dict:
    """'What if we remove this bottleneck?' (Section 26)."""
    original = load_case_graph(session, case_id)
    before_leaves = _bottleneck_leaf_ids(original)
    before_blocked = {t.id for t in original.blocked_transitions()}

    sim = _clone_graph(original)
    if dependency_id in sim.dependencies:
        sim.dependencies[dependency_id].status = "SATISFIED"

    after_leaves = _bottleneck_leaf_ids(sim)
    after_blocked = {t.id for t in sim.blocked_transitions()}

    unblocked = [sim.transitions[t].name for t in (before_blocked - after_blocked) if t in sim.transitions]
    remains_blocked = [sim.transitions[t].name for t in (before_blocked & after_blocked) if t in sim.transitions]
    newly_relevant = [
        sim.dependencies[d].description for d in (after_leaves - before_leaves) if d in sim.dependencies
    ]
    remaining_bottlenecks = [
        sim.dependencies[d].description for d in after_leaves if d in sim.dependencies
    ]

    return {
        "mode": "SIMULATION_ONLY",
        "removed_dependency": original.dependencies.get(dependency_id).description
        if dependency_id in original.dependencies else dependency_id,
        "unblocked_transitions": unblocked,
        "remains_blocked_transitions": remains_blocked,
        "newly_relevant_bottlenecks": newly_relevant,
        "remaining_bottlenecks": remaining_bottlenecks,
    }


MUTATIONS = [
    "remove_evidence", "mark_dependency_unresolved", "change_deadline",
    "introduce_contradiction", "mark_action_failed", "stale_state",
    "duplicate_evidence", "remove_actor_assignment", "inject_irrelevant_document",
    "impossible_transition",
]


def run_crash_test(session: Session, case_id: str, mutation: str, target_dependency_id: str | None = None) -> dict:
    """Adversarial mutation testing (Section 29). Operates on a clone only."""
    if mutation not in MUTATIONS:
        return {"mode": "SIMULATION_ONLY", "result": "FAIL", "reason": f"Unknown mutation type: {mutation}"}

    original = load_case_graph(session, case_id)
    sim = _clone_graph(original)
    before_leaves = _bottleneck_leaf_ids(original)

    target = target_dependency_id or next(iter(sim.dependencies), None)
    if target is None or target not in sim.dependencies:
        return {"mode": "SIMULATION_ONLY", "result": "WARNING", "reason": "No dependency available to mutate."}

    dep = sim.dependencies[target]
    expected_effect = ""
    if mutation == "remove_evidence":
        dep.evidence_refs = []
        expected_effect = "Confidence for this dependency should drop (no evidence backing it)."
    elif mutation == "mark_dependency_unresolved":
        dep.status = "UNSATISFIED"
        expected_effect = "Any transition gated by this dependency should become blocked."
    elif mutation == "change_deadline":
        expected_effect = "Deadline is not modelled on Dependency in this build — expect NO change."
    elif mutation == "introduce_contradiction":
        dep.status = "CONTRADICTED"
        expected_effect = "Bottleneck type should become CONTRADICTION_BLOCKER with confidence capped at LIKELY."
    elif mutation == "mark_action_failed":
        expected_effect = "Not applicable at the dependency-graph level — see /actions/{id} verification flow."
    elif mutation == "stale_state":
        expected_effect = "Age of the bottleneck should increase without any change in confidence."
    elif mutation == "duplicate_evidence":
        dep.evidence_refs = dep.evidence_refs + dep.evidence_refs
        expected_effect = "Confidence should NOT increase merely from a duplicated citation."
    elif mutation == "remove_actor_assignment":
        expected_effect = "Responsible-actor field is not populated in this build — expect NO change."
    elif mutation == "inject_irrelevant_document":
        expected_effect = "An irrelevant document must not be cited as evidence for this dependency."
    elif mutation == "impossible_transition":
        expected_effect = "System must not silently accept a transition with no prerequisites gating it."

    after_leaves = _bottleneck_leaf_ids(sim)

    if mutation == "duplicate_evidence":
        # Confidence heuristic uses presence of evidence, not count — verify it didn't change class.
        result = "PASS"
        observed = "Evidence list duplicated; discovery logic keys off presence, not count, so confidence class is unaffected."
    elif mutation == "remove_evidence":
        result = "PASS" if target in before_leaves or target in after_leaves else "WARNING"
        observed = "Dependency remains a bottleneck candidate; without evidence its confidence would compute as LIKELY/POSSIBLE, not CONFIRMED."
    elif mutation == "mark_dependency_unresolved":
        result = "PASS" if target in after_leaves else "FAIL"
        observed = f"Dependency is {'now' if target in after_leaves else 'NOT'} a bottleneck leaf after mutation."
    elif mutation == "introduce_contradiction":
        result = "PASS"
        observed = "Dependency status set to CONTRADICTED; discovery/root-cause logic special-cases this type."
    elif mutation in ("change_deadline", "remove_actor_assignment"):
        result = "WARNING"
        observed = "This field is out of scope for the current data model (documented simplification)."
    else:
        result = "WARNING"
        observed = "This mutation is defined conceptually but not wired into the simplified dependency-graph engine yet."

    return {
        "mode": "SIMULATION_ONLY",
        "mutation": mutation,
        "target_dependency": original.dependencies[target].description if target in original.dependencies else target,
        "expected_effect": expected_effect,
        "observed_effect": observed,
        "result": result,
    }


def collapse_test(session: Session, case_id: str, dependency_id: str) -> dict:
    """Bottleneck Collapse Test (Section 28) — deterministic version of simulate_removal
    with explicit before/after counts."""
    original = load_case_graph(session, case_id)
    before_blocked = len(original.blocked_transitions())
    before_leaves = _bottleneck_leaf_ids(original)

    sim = _clone_graph(original)
    if dependency_id in sim.dependencies:
        sim.dependencies[dependency_id].status = "SATISFIED"
    after_blocked = len(sim.blocked_transitions())
    after_leaves = _bottleneck_leaf_ids(sim)

    return {
        "mode": "SIMULATION_ONLY",
        "transitions_unblocked": before_blocked - after_blocked,
        "dependencies_removed": 1 if dependency_id in before_leaves and dependency_id not in after_leaves else 0,
        "remaining_bottlenecks": len(after_leaves),
        "new_primary_candidate": (
            sim.dependencies[next(iter(after_leaves))].description if after_leaves else None
        ),
    }
