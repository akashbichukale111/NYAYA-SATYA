"""
Tool Registry (section 11). Wraps service functions as named tools with
an explicit `consequential` flag. Consequential tools (anything that
changes case state) are only callable with an authorization context that
proves either (a) it's a read/analysis step, or (b) an Approval exists.
This is enforced here, once, rather than trusted to be checked correctly
by every call site.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class AuthorizationError(Exception):
    pass


@dataclass
class ToolSpec:
    name: str
    fn: Callable
    consequential: bool  # True => requires an approved Action to run


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, fn: Callable, consequential: bool = False):
        self._tools[name] = ToolSpec(name=name, fn=fn, consequential=consequential)

    def call(self, name: str, *, authorized: bool = False, **kwargs):
        if name not in self._tools:
            raise KeyError(f"Unknown tool '{name}'")
        spec = self._tools[name]
        if spec.consequential and not authorized:
            raise AuthorizationError(
                f"Tool '{name}' is consequential and requires an approved action before it can run."
            )
        return spec.fn(**kwargs)

    def list_tools(self) -> list[dict]:
        return [{"name": t.name, "consequential": t.consequential} for t in self._tools.values()]


def build_default_registry() -> ToolRegistry:
    from app.services import (
        case_twin, readiness_engine, blocker_engine, causal_graph,
        action_planner, verification_engine, simulation_engine,
        crash_test_engine, audit_service,
    )

    registry = ToolRegistry()
    registry.register("document_reader", case_twin.get_case_full, consequential=False)
    registry.register("case_state_lookup", case_twin.get_case_full, consequential=False)
    registry.register("hearing_lookup", case_twin.refresh_hearing_context, consequential=False)
    registry.register("requirement_check", readiness_engine.run_readiness_audit, consequential=False)
    registry.register("blocker_analysis", blocker_engine.sync_blockers, consequential=False)
    registry.register("dependency_graph_query", causal_graph.get_graph, consequential=False)
    registry.register("draft_action", action_planner.propose_action, consequential=False)
    registry.register("state_update", verification_engine.execute_action, consequential=True)
    registry.register("verification", verification_engine.verify_action, consequential=False)
    registry.register("simulation", simulation_engine.simulate, consequential=False)
    registry.register("crash_test", crash_test_engine.run_crash_test, consequential=False)
    registry.register("audit_log", audit_service.get_case_audit, consequential=False)
    return registry
