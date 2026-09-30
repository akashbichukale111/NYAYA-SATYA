"""Section 6/8: Case Flow Graph + Causal Dependency Graph.

These are pure in-memory graph tests — no DB, no agents, no LLM. If these
fail, nothing built on top of the graph (discovery, root-cause, simulation)
can be trusted, so this file is deliberately the most exhaustive.
"""
from app.graph import CaseGraph
from app.models import Dependency, Transition


def _dep(id_, status="UNSATISFIED", depends_on=None):
    return Dependency(
        id=id_, case_id="c1", description=id_, type="test", status=status,
        depends_on=depends_on or [],
    )


def _trans(id_, prereqs):
    return Transition(id=id_, case_id="c1", name=id_, prerequisite_dependency_ids=prereqs)


def test_blocked_transitions_single_unsatisfied_dependency():
    g = CaseGraph(
        dependencies={"d1": _dep("d1")},
        transitions={"t1": _trans("t1", ["d1"])},
    )
    blocked = g.blocked_transitions()
    assert [t.id for t in blocked] == ["t1"]


def test_transition_not_blocked_when_dependency_satisfied():
    g = CaseGraph(
        dependencies={"d1": _dep("d1", status="SATISFIED")},
        transitions={"t1": _trans("t1", ["d1"])},
    )
    assert g.blocked_transitions() == []


def test_unsatisfied_leaf_dependencies_walks_to_true_root_cause():
    # d1 depends on d2 depends on d3 (unsatisfied leaf). d1/d2 should NOT be
    # reported as the root cause — only d3, the actual leaf — matching
    # Section 7's "don't stop at the first missing item" requirement.
    g = CaseGraph(
        dependencies={
            "d1": _dep("d1", depends_on=["d2"]),
            "d2": _dep("d2", depends_on=["d3"]),
            "d3": _dep("d3"),
        },
        transitions={},
    )
    assert g.unsatisfied_leaf_dependencies("d1") == ["d3"]


def test_unsatisfied_leaf_stops_at_satisfied_link():
    # d1 depends on d2 (satisfied) -> d1 itself is the leaf now.
    g = CaseGraph(
        dependencies={
            "d1": _dep("d1", depends_on=["d2"]),
            "d2": _dep("d2", status="SATISFIED"),
        },
        transitions={},
    )
    assert g.unsatisfied_leaf_dependencies("d1") == ["d1"]


def test_unsatisfied_leaf_returns_empty_for_satisfied_dependency():
    g = CaseGraph(dependencies={"d1": _dep("d1", status="SATISFIED")}, transitions={})
    assert g.unsatisfied_leaf_dependencies("d1") == []


def test_depends_transitively_has_cycle_guard():
    # d1 -> d2 -> d1 (cycle). Must terminate, not recurse forever.
    g = CaseGraph(
        dependencies={
            "d1": _dep("d1", depends_on=["d2"]),
            "d2": _dep("d2", depends_on=["d1"]),
        },
        transitions={},
    )
    # Should return without raising RecursionError.
    result = g.unsatisfied_leaf_dependencies("d1")
    assert isinstance(result, list)


def test_transitions_gated_by_direct_and_transitive():
    g = CaseGraph(
        dependencies={
            "d1": _dep("d1"),
            "d2": _dep("d2", depends_on=["d1"]),
        },
        transitions={
            "t1": _trans("t1", ["d1"]),
            "t2": _trans("t2", ["d2"]),
        },
    )
    gated_by_d1 = set(g.transitions_gated_by("d1"))
    # t1 depends directly on d1; t2 depends on d2 which depends on d1
    assert gated_by_d1 == {"t1", "t2"}


def test_to_sim_clone_is_fully_detached_from_orm():
    """Regression test for the ObjectDereferencedError bug found during manual
    QA: cloning via SQLModel .model_copy() on a live ORM row corrupts
    SQLAlchemy instrumentation once the original row is garbage collected.
    to_sim_clone() must return plain, mutable, detached objects instead."""
    from app.graph import SimDependency, SimTransition

    g = CaseGraph(
        dependencies={"d1": _dep("d1")},
        transitions={"t1": _trans("t1", ["d1"])},
    )
    clone = g.to_sim_clone()
    assert isinstance(clone.dependencies["d1"], SimDependency)
    assert isinstance(clone.transitions["t1"], SimTransition)

    # Mutating the clone must not raise, and must not affect the original.
    clone.dependencies["d1"].status = "SATISFIED"
    assert g.dependencies["d1"].status == "UNSATISFIED"
    assert clone.dependencies["d1"].status == "SATISFIED"
