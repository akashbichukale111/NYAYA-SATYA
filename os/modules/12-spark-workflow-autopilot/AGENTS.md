# Agents

All 12 agents live in `app/engine/agents.py`. Each is independently unit
tested in `tests/test_agents.py` without needing the others running. None
of them makes a legal decision — each turns a signal, a state, or a
question into a proposal, a classification, or a permitted action within
its own narrow lane.

| Agent | Responsibility | Real logic (not a rename) |
|---|---|---|
| `TriggerAgent` | Maps an inbound `trigger_type` to a workflow template name | A static, human-curated map; returns `None` for anything unmapped rather than guessing |
| `WorkflowPlanningAgent` | Decides *whether and what* to plan | Delegates the *how* to `planner.plan_workflow`, but is the layer that would hold "should we even propose this" logic as it grows |
| `TaskDecompositionAgent` | Previews a template's task graph without creating anything | Read-only; used to answer "what would this workflow look like" before triggering it |
| `DependencyAgent` | Answers "what is this task still waiting on?" | Walks the real `Dependency` graph transitively, returns only unsatisfied upstream tasks |
| `RiskAgent` | Classifies risk and decides if a human gate is needed | Risk levels are read from the task (set by the human-authored template), never inferred from free text |
| `ApprovalAgent` | Finds the pending approval for a task | Queries `ApprovalRequest` directly |
| `ExecutionAgent` | Runs a task through start→complete | Surfaces `APPROVAL_REQUIRED` as a structured result instead of raising past the caller |
| `VerificationAgent` | Verifies a task outcome | Thin, explicit call — verification is never automatic |
| `RecoveryAgent` | Surfaces recovery options / performs a gated retry | Delegates to `recovery.py`, which refuses `system`-initiated retry of consequential tasks |
| `AttentionAgent` | Surfaces what needs a human right now | Queries live workflow state for `BLOCKED`/`APPROVAL_REQUIRED` |
| `SimulationAgent` | What-if façade | Delegates to the isolated simulation lab |
| `ConflictAgent` | Open conflicts / resolution | Delegates to `conflict.py`, which refuses `system`-initiated resolution |
| `AuditAgent` | Read-side query API over the audit ledger | Every write already goes through `app.engine.audit.record_event`; this agent only reads |

## Why these are real agents, not renamed functions

Each agent:
1. Has a single, stated responsibility distinct from the others (see table)
2. Is tested in isolation in `tests/test_agents.py` with no dependency on
   the others being exercised first
3. Enforces at least one real constraint of its own — e.g. `TriggerAgent`
   returns `None` rather than a guess for unmapped triggers;
   `TaskDecompositionAgent.preview()` provably creates zero database rows
   (asserted in `test_task_decomposition_agent_previews_without_creating`);
   `RecoveryAgent`/`ConflictAgent` inherit the `system`-cannot-self-approve
   guarantee from the functions they wrap

## What's not yet agent-ified

The spec's multi-agent list is fully represented (12/12). What's still thin
is inter-agent coordination — right now each agent is called directly by the
API layer or another agent's caller; there is no separate "agent
orchestrator" process. That coordination logic is exactly what
`WorkflowPlanningAgent` and `TriggerAgent` chained together already do for
the planning path; extending that pattern is Section 3/4 work as the
frontend and evaluation lab start calling agents directly.
