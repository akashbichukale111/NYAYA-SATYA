# Phase 6: Auto-Healer, Independent Re-Attack, Legal Perturbation Lab & Judicial Review Dossier

## 1. Overview & Product Positioning

Phase 6 implements the **Auto-Healer / Self-Healing Legal Drafting**, **Independent Re-Attack Engine**, **Legal Perturbation Lab**, **Case Readiness Delta**, and **Judicial Review Dossier** for NYAYA-SATYA.

Phase 6 transforms the system from:
> "Find weaknesses and simulate consequences" (Phases 4 & 5)

into:
> "Find weakness → propose evidence-grounded repair → independently attack the repair → verify repair immunity → measure readiness change → produce an auditable judicial review dossier."

### Strictly Non-Adjudicative Mandate
NYAYA-SATYA is **NOT**:
- an autonomous lawyer, advocate, or legal advisor
- an autonomous judge, arbitrator, or prosecutor
- a verdict predictor or legal outcome probability engine
- an automated filing or electronic certification agent

**The AI proposes. Evidence constrains. Causality explains. Adversarial reasoning attacks. Repair attempts to strengthen. Independent re-attack tries to break it. UNWIND governs. The Human Legal Gate decides.**

---

## 2. Core Phase 6 Pipeline

```
Existing Case Digital Twin (Phase 3)
     │
     ▼
Adversarial Findings (Phase 4)
     │
     ▼
Causal Dependency Analysis (Phase 5)
     │
     ▼
Repair Candidate Generation (RepairGenerator)
     │
     ▼
Repair Utility Evaluation (RepairUtilityVector)
     │
     ▼
Repair Validation (RepairValidator, EvidenceSupportValidator, LegalGroundingValidator)
     │
     ▼
Blast-Radius Recalculation (CausalRepairAdapter)
     │
     ▼
Independent Re-Attack (ReAttackEngine / IndependentAttacker)
     │
     ▼
Repair Immunity Evaluation (RepairImmunityEvaluator)
     │
     ├── FAILED (Regression / Vulnerable) ──► Repair Rejected / Escalated
     │
     └── PASSED (Immune / Partially Immune) ──► Case Readiness Delta
                                                   │
                                                   ▼
                                            Legal Perturbation Lab (Should-Change / Should-Not-Change)
                                                   │
                                                   ▼
                                            Judicial Review Dossier (24 Sections)
                                                   │
                                                   ▼
                                            UNWIND Governance (GovernanceStateMachine)
                                                   │
                                                   ▼
                                            Human Legal Gate (Final Human Authority)
```

---

## 3. Subsystem Architecture & Modules

### A. Auto-Healer (`nyaya_repair/`)
- **`contracts/`**:
  - `repair_candidate.py`: Strongly typed `RepairCandidate` with 12 distinct change types (`ADD_EVIDENCE_REFERENCE`, `QUALIFY_ASSERTION`, `REQUEST_MISSING_EVIDENCE`, etc.) and deterministic SHA-256 fingerprinting.
  - `repair_utility.py`: `RepairUtilityVector` evaluating `evidence_support`, `legal_grounding`, `fragility_reduction`, `collateral_impact`, `uncertainty`, `new_vulnerabilities`, `critical_collateral_impact`. Enforces hard constraints.
  - `repair.py`: `LegalGrounding` and `LegalAuthorityRef` distinguishing `VERIFIED_AUTHORITY` from `AUTHORITY_UNVERIFIED`.
  - `repair_action.py`: Atomic `RepairAction` primitives.
  - `repair_constraint.py`: Configurable `RepairConstraints`.
  - `repair_result.py`: `RepairExecutionResult` and `SimulatedRepairReport`.
  - `repair_certificate.py`: `AdmissibilityReadinessGate` enforcing BSA evidence certification safety (`CERTIFICATION_PENDING_HUMAN_SIGNATURE`).
- **`engine/`**:
  - `repair_generator.py`: Generates evidence-grounded repair candidates from Phase 4 findings.
  - `repair_planner.py`: Prioritizes candidates by structural importance and safety.
  - `repair_applier.py`: Simulates repairs on isolated `copy.deepcopy` clones; asserts `canonical_twin.integrity_hash == pre_hash`.
  - `repair_evaluator.py`: Calculates multi-dimensional utility vector.
  - `convergence_governor.py`: Tracks iteration history and halts loops upon repeated repair/attack fingerprints.
- **`validation/`**:
  - `repair_validator.py`: Enforces non-adjudication lexicon and prompt injection defense.
  - `evidence_support_validator.py`: Resolves evidence references; flags `EVIDENCE_REQUIRED` if unresolvable; blocks quarantined items.
  - `legal_grounding_validator.py`: Disallows unverified LLM citations from claiming verified status.
  - `collateral_impact_validator.py`: Detects unintended shifts to non-target nodes.
  - `vulnerability_validator.py`: Ensures zero new vulnerabilities post-repair.
- **`provenance/`**:
  - `repair_provenance.py`: Generates immutable cryptographic `ProvenanceRef` records.
- **`integration/`**:
  - `adversarial_adapter.py`: Ingests Phase 4 gauntlet findings.
  - `causal_adapter.py`: Calls Phase 5 `BlastRadiusEngine`.
  - `tarka_adapter.py`: Produces `ReasoningProposal(reasoning_type=ReasoningType.REPAIR_PROPOSAL)`.
  - `unwind_adapter.py`: Routes proposals through `GovernanceStateMachine` to `HumanLegalGate`.

### B. Independent Re-Attack Engine (`nyaya_reattack/`)
- `attack_profile.py`: Strategies (`TARGET_VERIFICATION_PROBE`, `COLLATERAL_CONTRADICTION_SCAN`, etc.).
- `independent_attacker.py`: Independent probe generator that does not trust the repair author.
- `reattack_engine.py`: Executes adversarial gauntlet against repaired twin simulation.
- `attack_comparator.py`: Compares pre-repair findings vs post-repair findings.
- `regression_detector.py`: Diagnoses regression severity (`NONE`, `MINOR`, `CRITICAL`).
- `repair_immunity.py`: Classifies `RepairImmunityStatus` (`IMMUNE`, `PARTIALLY_IMMUNE`, `VULNERABLE`, `REGRESSION`, `UNKNOWN`).

### C. Legal Perturbation Lab (`nyaya_perturbation/`)
- `perturbation_scenario.py`: Models `SHOULD_CHANGE` and `SHOULD_NOT_CHANGE` experiments.
- `perturbation_engine.py`: Runs perturbations on isolated clones and compares expected vs observed propagations (`EXPECTED_CHANGE`, `EXPECTED_NO_CHANGE`, `UNEXPECTED_CHANGE`, `EXPECTED_CHANGE_MISSING`).
- `stability_analyzer.py`: Aggregates structural stability score and detects spurious propagation.

### D. Case Readiness Delta (`nyaya_readiness/`)
- `readiness_snapshot.py`: Multi-dimensional structural metrics (evidence coverage ratio, unresolved contradictions, provenance coverage, authority verification, causal dependency coverage, human review obligations).
- `readiness_delta.py`: Quantitative deltas across all dimensions before and after repair.
- `calculator.py`: Computes snapshots and deltas without outcome probabilities.

### E. Judicial Review Dossier (`nyaya_dossier/`)
- `dossier_model.py`: 24 auditable sections categorizing items as `FACT`, `EVIDENCE`, `INFERENCE`, `ASSUMPTION`, `HYPOTHESIS`, `UNRESOLVED`, `PROPOSED_REPAIR`, or `HUMAN_DECISION`.
- `dossier_builder.py`: Compiles cross-subsystem dossier.
- `export_formatter.py`: Markdown and JSON export formatters.

---

## 4. API Endpoints

Mounted under `/api/nyaya/cases/{case_id}/`:

| Method | Path | Description |
|---|---|---|
| POST | `/repair/generate` | Generate evidence-grounded repair candidates |
| GET | `/repair/candidates` | List generated repair candidates |
| GET | `/repair/candidates/{repair_id}` | Get specific repair candidate |
| POST | `/repair/validate` | Validate candidate against safety and grounding |
| POST | `/repair/simulate` | Simulate repair on cloned twin and compute utility |
| POST | `/repair/utility` | Retrieve multi-dimensional utility vector |
| POST | `/reattack/run` | Run independent re-attack and evaluate immunity |
| POST | `/reattack/compare` | Compare pre vs post-repair adversarial findings |
| GET | `/reattack/immunity/{repair_id}` | Retrieve repair immunity assessment |
| POST | `/perturbation/run` | Execute controlled SHOULD_CHANGE or SHOULD_NOT_CHANGE |
| GET | `/perturbation/outcomes` | List perturbation outcomes |
| GET | `/perturbation/stability` | Aggregate reasoning stability report |
| GET | `/readiness/snapshot` | Compute structural case readiness snapshot |
| POST | `/readiness/delta` | Compute structural readiness delta for a repair |
| POST | `/dossier/build` | Compile 24-section Judicial Review Dossier |
| GET | `/dossier/latest` | Retrieve latest compiled dossier |
| GET | `/dossier/export/markdown` | Export dossier as structured Markdown |
| GET | `/dossier/export/json` | Export dossier as structured JSON |

---

## 5. Synthetic Demonstration

> **SYNTHETIC DEMONSTRATION DATA**
> This example uses synthetic data to illustrate the Phase 6 workflow. It does not represent actual court records or real individuals.

1. **Initial Case State**:
   - Case `SYNTHETIC_CASE_01` has evidence `EV_17` (bank transfer statement).
   - `EV_17` supports claim `C_04` ("Defendant authorized payment").
   - `C_04` supports issue `ISS_02` ("Whether payment obligation was met").
   - An unsupported assertion exists on claim `C_08` ("Defendant acted with malice").
2. **Adversarial Gauntlet Execution**:
   - Adversarial engine flags `C_08` as `UNSUPPORTED_CLAIM` (`StructuralSeverity.HIGH`).
3. **Repair Candidate Generation**:
   - Auto-Healer proposes repair `REP_812`: `QUALIFY_ASSERTION` on `C_08`, converting predicate to "Subject to independent corroboration: Alleged malice".
4. **Utility & Simulation**:
   - Cloned twin simulated: `canonical_twin.integrity_hash` preserved.
   - `RepairUtilityVector`: EvidenceSupport=0.8, FragilityReduction=0.85, NewVulnerabilities=0, MeetsHardConstraints=True.
5. **Independent Re-Attack**:
   - Re-Attack engine runs independent challenge targeting `C_08`.
   - Probe confirms overstatement vulnerability resolved. Zero new vulnerabilities.
   - `RepairImmunityStatus`: `IMMUNE`.
6. **Perturbation Lab**:
   - Immaterial metadata perturbation tested (`SHOULD_NOT_CHANGE`): protected claim `C_04` remains stable (`EXPECTED_NO_CHANGE`).
7. **Readiness Delta**:
   - Unsupported claims delta: -1. Net structural progress: True.
8. **Judicial Dossier Compiled**:
   - 24 sections generated with deterministic SHA-256 fingerprint.
   - Submitted to UNWIND Governance State Machine (`ASK_HUMAN`).
   - Human Legal Gate holds final approval authority.
