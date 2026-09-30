"""
Case Flow Graph (Section 6) and Causal Dependency Graph (Section 8) helpers.

This is a plain in-memory graph over the Dependency/Transition rows already
stored for a case — deliberately simple (dict-of-nodes + edges) rather than a
dedicated graph database, since case sizes in this system are small (tens,
not millions, of nodes). Documented as a scope simplification in the README.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union
from sqlmodel import Session, select

from .models import Dependency, Transition


@dataclass
class SimDependency:
    """Plain, session-detached stand-in for Dependency, used only inside the
    simulation/crash-test engine (Sections 26-29). Deliberately NOT a SQLModel
    table instance: mutating a copied ORM row was found (during testing) to
    raise sqlalchemy.orm.exc.ObjectDereferencedError once the original row
    fell out of scope, because SQLModel's model_copy() carries over live
    SQLAlchemy instrumentation state. A plain dataclass has no such coupling,
    which also makes the "simulation never touches the database" guarantee
    structurally true rather than merely a convention."""
    id: str
    description: str
    type: str
    status: str
    depends_on: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class SimTransition:
    id: str
    name: str
    prerequisite_dependency_ids: list[str] = field(default_factory=list)
    status: str = "PENDING"


def _to_sim_dependency(d: Dependency) -> SimDependency:
    return SimDependency(
        id=d.id, description=d.description, type=d.type, status=d.status,
        depends_on=list(d.depends_on), evidence_refs=list(d.evidence_refs),
    )


def _to_sim_transition(t: Transition) -> SimTransition:
    return SimTransition(
        id=t.id, name=t.name,
        prerequisite_dependency_ids=list(t.prerequisite_dependency_ids), status=t.status,
    )


@dataclass
class CaseGraph:
    dependencies: dict[str, Union[Dependency, SimDependency]] = field(default_factory=dict)
    transitions: dict[str, Union[Transition, SimTransition]] = field(default_factory=dict)

    def blocked_transitions(self) -> list[Transition]:
        blocked = []
        for t in self.transitions.values():
            for dep_id in t.prerequisite_dependency_ids:
                dep = self.dependencies.get(dep_id)
                if dep and dep.status != "SATISFIED":
                    blocked.append(t)
                    break
        return blocked

    def transitions_gated_by(self, dependency_id: str) -> list[str]:
        """Every transition (directly or transitively) gated by this dependency."""
        result = []
        for t in self.transitions.values():
            if self._dependency_gates_transition(dependency_id, t):
                result.append(t.id)
        return result

    def _dependency_gates_transition(self, dependency_id: str, t: Transition) -> bool:
        for prereq_id in t.prerequisite_dependency_ids:
            if prereq_id == dependency_id:
                return True
            if self._depends_transitively(prereq_id, dependency_id, set()):
                return True
        return False

    def _depends_transitively(self, from_id: str, target_id: str, seen: set) -> bool:
        if from_id in seen:
            return False  # cycle guard
        seen.add(from_id)
        dep = self.dependencies.get(from_id)
        if not dep:
            return False
        if target_id in dep.depends_on:
            return True
        return any(self._depends_transitively(child, target_id, seen) for child in dep.depends_on)

    def unsatisfied_leaf_dependencies(self, dependency_id: str, _seen: frozenset = frozenset()) -> list[str]:
        """Walk depends_on recursively; return the unsatisfied dependencies with
        no further unsatisfied ancestors — i.e. root-cause candidates.

        _seen guards against a dependency cycle (Section 10: "never loop
        indefinitely"). A cycle is a genuine bad-data case in a real case
        file, not something to crash on: if we're about to revisit a node
        already on the current path, we stop descending and report this
        node as a leaf itself, rather than raising RecursionError."""
        dep = self.dependencies.get(dependency_id)
        if not dep or dependency_id in _seen:
            return [dependency_id] if dep and dep.status != "SATISFIED" else []
        seen = _seen | {dependency_id}
        unsatisfied_children = [
            c for c in dep.depends_on
            if c in self.dependencies and self.dependencies[c].status != "SATISFIED"
        ]
        if not unsatisfied_children:
            return [dependency_id] if dep.status != "SATISFIED" else []
        leaves = []
        for c in unsatisfied_children:
            leaves.extend(self.unsatisfied_leaf_dependencies(c, seen))
        return leaves or [dependency_id]

    def to_sim_clone(self) -> "CaseGraph":
        """Detached, mutable deep copy safe for simulation/crash-testing.
        Never returns live ORM rows — see SimDependency/SimTransition above."""
        return CaseGraph(
            dependencies={k: _to_sim_dependency(v) for k, v in self.dependencies.items()},
            transitions={k: _to_sim_transition(v) for k, v in self.transitions.items()},
        )


def load_case_graph(session: Session, case_id: str) -> CaseGraph:
    deps = session.exec(select(Dependency).where(Dependency.case_id == case_id)).all()
    trans = session.exec(select(Transition).where(Transition.case_id == case_id)).all()
    return CaseGraph(
        dependencies={d.id: d for d in deps},
        transitions={t.id: t for t in trans},
    )
