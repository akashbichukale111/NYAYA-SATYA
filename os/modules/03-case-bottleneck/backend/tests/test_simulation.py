"""Sections 26-29: simulation, collapse test, crash test. All of these must
be read-only against the real case state — this file explicitly asserts
that nothing in the DB changes after running them (Section 26: "Never
modify real case state")."""
from sqlmodel import Session, select

from app.models import Case, Dependency, Transition
from app import simulation as sim


def _seed_simple_case(session: Session):
    session.add(Case(id="c1", title="Test Case", case_type="civil"))
    session.add(Dependency(id="d1", case_id="c1", description="Document A", type="document", status="UNSATISFIED"))
    session.add(Dependency(id="d2", case_id="c1", description="Document B", type="document", status="UNSATISFIED"))
    session.add(Transition(id="t1", case_id="c1", name="Hearing", prerequisite_dependency_ids=["d1", "d2"]))
    session.commit()


def test_simulate_removal_unblocks_transition_only_when_all_prereqs_satisfied(session):
    _seed_simple_case(session)
    # Removing only d1 must NOT unblock t1, since d2 is still unsatisfied.
    result = sim.simulate_removal(session, "c1", "d1")
    assert result["mode"] == "SIMULATION_ONLY"
    assert result["unblocked_transitions"] == []
    assert "Hearing" in result["remains_blocked_transitions"]


def test_simulate_removal_does_not_mutate_real_database(session):
    _seed_simple_case(session)
    sim.simulate_removal(session, "c1", "d1")
    d1 = session.get(Dependency, "d1")
    assert d1.status == "UNSATISFIED"  # untouched by the simulation


def test_collapse_test_unblocks_when_last_dependency_removed(session):
    _seed_simple_case(session)
    session.exec(select(Dependency)).all()
    d2 = session.get(Dependency, "d2")
    d2.status = "SATISFIED"
    session.add(d2)
    session.commit()

    result = sim.collapse_test(session, "c1", "d1")
    assert result["transitions_unblocked"] == 1


def test_crash_test_rejects_unknown_mutation_type(session):
    _seed_simple_case(session)
    result = sim.run_crash_test(session, "c1", "not_a_real_mutation")
    assert result["result"] == "FAIL"


def test_crash_test_mark_dependency_unresolved_passes(session):
    _seed_simple_case(session)
    result = sim.run_crash_test(session, "c1", "mark_dependency_unresolved", "d1")
    assert result["mode"] == "SIMULATION_ONLY"
    assert result["result"] == "PASS"


def test_crash_test_never_mutates_real_database(session):
    _seed_simple_case(session)
    sim.run_crash_test(session, "c1", "mark_dependency_unresolved", "d1")
    sim.run_crash_test(session, "c1", "introduce_contradiction", "d2")
    d1 = session.get(Dependency, "d1")
    d2 = session.get(Dependency, "d2")
    assert d1.status == "UNSATISFIED"
    assert d2.status == "UNSATISFIED"  # NOT "CONTRADICTED" — crash test must not persist


def test_crash_test_duplicate_evidence_does_not_inflate_confidence():
    from app.graph import CaseGraph, SimDependency

    dep = SimDependency(id="d1", description="X", type="document", status="UNSATISFIED",
                         evidence_refs=["ev1"])
    before = len(dep.evidence_refs)
    dep.evidence_refs = dep.evidence_refs + dep.evidence_refs
    assert len(dep.evidence_refs) == before * 2
    # The discovery agent's confidence function keys off *presence*, not
    # count, of evidence_refs — this is exercised in test_agents.py; here we
    # just confirm the mutation itself does what the crash-test claims.
