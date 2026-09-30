"""
Tests for the explicit multi-agent service boundaries (app/agents/agents.py).

These assert two things per the master prompt's non-negotiables:
  1. The agent pipeline produces the SAME analytical result as the direct
     run_simulation() path (no second, divergent implementation of "truth").
  2. Every agent's action is recorded in the audit trace, and no agent step
     ever silently mutates the base graph.
"""
import copy
import json

from app.agents.agents import SimulationPipeline, ScenarioPlannerAgent
from app.simulation_engine.runner import run_simulation


def _chain_case():
    return {
        "nodes": [
            {"id": "e1", "node_type": "EVIDENCE", "label": "Evidence 1", "status": "VERIFIED", "attributes": {}},
            {"id": "c1", "node_type": "CLAIM", "label": "Claim 1", "status": "VERIFIED", "attributes": {}},
            {"id": "i1", "node_type": "ISSUE", "label": "Issue 1", "status": "VERIFIED", "attributes": {}},
            {"id": "o1", "node_type": "OBLIGATION", "label": "Obligation 1", "status": "VERIFIED", "attributes": {}},
        ],
        "relationships": [
            {"id": "r1", "source_id": "c1", "target_id": "e1", "rel_type": "DEPENDS_ON", "attributes": {}},
            {"id": "r2", "source_id": "i1", "target_id": "c1", "rel_type": "DEPENDS_ON", "attributes": {}},
            {"id": "r3", "source_id": "o1", "target_id": "i1", "rel_type": "DEPENDS_ON", "attributes": {}},
        ],
    }


def test_pipeline_matches_direct_runner_result():
    case = _chain_case()
    mutations = [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": "e1"}]

    direct = run_simulation(case, mutations)
    piped = SimulationPipeline().run(case, mutations)

    assert direct["status"] == piped["status"] == "COMPLETED"
    assert direct["blast_radius"]["affected_claims"] == piped["blast_radius"]["affected_claims"]
    assert direct["blast_radius"]["human_review_items"] == piped["blast_radius"]["human_review_items"]
    assert {a["node_id"] for a in direct["affected_nodes"]} == {a["node_id"] for a in piped["affected_nodes"]}


def test_pipeline_never_mutates_base_graph():
    case = _chain_case()
    original = copy.deepcopy(case)
    SimulationPipeline().run(case, [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": "e1"}])
    assert json.dumps(case, sort_keys=True) == json.dumps(original, sort_keys=True)


def test_pipeline_records_every_agent_stage():
    case = _chain_case()
    result = SimulationPipeline().run(case, [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": "e1"}])
    agents_seen = {t["agent"] for t in result["agent_trace"]}
    assert {
        "ScenarioPlannerAgent", "StateSnapshotAgent", "MutationAgent",
        "DependencyTraversalAgent", "BlastRadiusAgent", "ConflictPropagationAgent",
        "VerificationImpactAgent", "WorkflowImpactAgent", "RecoveryPlannerAgent",
    }.issubset(agents_seen)


def test_pipeline_fails_closed_on_malformed_mutation_shape():
    case = _chain_case()
    result = SimulationPipeline().run(case, [{"mutation_type": "REMOVE_EVIDENCE"}])  # missing target_node_id
    assert result["status"] == "FAILED"
    assert "error" in result


def test_scenario_planner_rejects_malformed_step_directly():
    try:
        ScenarioPlannerAgent().plan([{"mutation_type": "REMOVE_EVIDENCE"}])
        assert False, "expected ValueError"
    except ValueError:
        pass
