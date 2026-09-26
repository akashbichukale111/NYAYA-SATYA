# Phase 5: Causal Reasoning Engine + Counterfactual Lab

## Overview

Phase 5 implements the **Causal Reasoning Engine** and **Counterfactual Lab** for NYAYA-SATYA.
This phase adds the ability to construct, traverse, and analyze causal dependency graphs
over the Case Digital Twin, run controlled counterfactual scenarios, compute blast-radius
impact analysis, and classify structural materiality.

> **Non-Adjudication Guarantee**: Phase 5 does NOT predict verdicts, determine guilt,
> calculate win probabilities, or act as an autonomous judge. All outputs are structural
> analyses submitted for Human Legal Gate review.

## Architecture

```
CaseDigitalTwin (Phase 3)
    |
    +-- TwinToCausalAdapter --> CausalGraph
    |                              +-- CausalNode (typed: EVENT, FACT, CLAIM, EVIDENCE, etc.)
    |                              +-- CausalEdge (typed: CAUSES, DEPENDS_ON, ENABLES, etc.)
    |                              +-- CausalHypothesis
    |
    +-- InterventionEngine --> Counterfactual Twin (deep copy)
    |                              +-- BlastRadiusEngine -> BlastRadiusReport
    |                                      +-- TwinComparator -> CounterfactualComparison
    |
    +-- CounterfactualLab (coordinator)
    |       +-- ScenarioRunner
    |       +-- CounterfactualScenario
    |       +-- Scenario Replay
    |
    +-- MaterialityClassifier
    |       +-- ShouldChangeAnalyzer
    |       +-- ShouldNotChangeAnalyzer
    |
    +-- Integration Layer
            +-- CausalTarkaAdapter -> ReasoningProposal
            +-- CausalUnwindAdapter -> GovernanceStateMachine
            +-- AdversarialToCausalAdapter -> Intervention from P4 findings
```

## Components

### Contracts (nyaya_causal/contracts/)

| Contract | Purpose |
|----------|---------|
| CausalNode | Typed node in causal graph |
| CausalEdge | Directed typed causal edge with explicit causal_basis |
| CausalHypothesis | Competing causal explanation |
| Intervention | Controlled hypothetical change to case state |
| CausalEffect | Classified impact of an intervention on a node |
| BlastRadiusReport | Structural blast-radius report |
| CounterfactualComparison | Before/after comparison of twin states |
| CounterfactualScenario | Complete scenario package with integrity hash |

### API Endpoints

All under /api/nyaya/cases/{case_id}/causal/:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /graph/build | Build causal graph from twin |
| GET | /graph | Get causal graph |
| GET | /graph/validate | Validate graph integrity |
| GET | /graph/paths | Find causal paths |
| GET | /graph/downstream/{node_id} | Get downstream nodes |
| GET | /graph/upstream/{node_id} | Get upstream nodes |
| POST | /blast-radius | Compute blast-radius |
| POST | /scenarios | Create and run scenario |
| GET | /scenarios | List scenarios |
| GET | /scenarios/{scenario_id} | Get scenario |
| POST | /scenarios/{scenario_id}/replay | Replay scenario |
| GET | /materiality/evidence/{evidence_id} | Evidence materiality |
| GET | /materiality/claims/{claim_id} | Claim materiality |
| POST | /should-change | Should-change analysis |
| POST | /should-not-change | Should-not-change analysis |
| POST | /validate | Validate causal subsystem |
| GET | /snapshot | Full causal snapshot |

## Safety Guarantees

1. Twin Immutability: Canonical CaseDigitalTwin is NEVER mutated
2. Cross-Case Isolation: All operations isolated to a single case
3. Non-Adjudication: No verdict prediction or guilt determination
4. Quarantine Boundary: Blocked evidence cannot enter causal analysis
5. Prompt Injection Detection: Adversarial text patterns detected
6. Deterministic Hashing: All scenarios have reproducible SHA-256 hashes
7. Governance Integration: All proposals route through UNWIND -> Human Legal Gate

## Test Coverage

70+ tests across 16 categories covering contracts, graph operations,
path analysis, blast-radius, counterfactual scenarios, intervention engine,
twin comparison, materiality, should-change/should-not-change, integration
adapters, provenance, validation, API endpoints, and non-adjudication compliance.
