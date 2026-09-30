from __future__ import annotations

from sqlmodel import Session

from ..graph import load_case_graph


class DependencyAgent:
    name = "dependency-agent"

    def graph_json(self, session: Session, case_id: str) -> dict:
        graph = load_case_graph(session, case_id)
        nodes = [
            {
                "id": d.id, "kind": "dependency", "description": d.description,
                "type": d.type, "status": d.status,
            }
            for d in graph.dependencies.values()
        ] + [
            {
                "id": t.id, "kind": "transition", "description": t.name,
                "type": "transition", "status": t.status,
            }
            for t in graph.transitions.values()
        ]
        edges = []
        for d in graph.dependencies.values():
            for child in d.depends_on:
                edges.append({"from": d.id, "to": child, "relationship": "depends_on"})
        for t in graph.transitions.values():
            for prereq in t.prerequisite_dependency_ids:
                edges.append({"from": t.id, "to": prereq, "relationship": "requires"})
        return {"nodes": nodes, "edges": edges}
