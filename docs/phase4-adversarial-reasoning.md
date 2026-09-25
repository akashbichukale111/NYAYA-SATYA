# NYAYA-SATYA — Phase 4: Adversarial Reasoning Specification
**ADVERSARIAL GAUNTLET + EVIDENCE CONFLICT ARENA + JENGA / ACHILLES-HEEL ANALYSIS + MISSING-EVIDENCE / VALUE-OF-INFORMATION FOUNDATION**

> [!IMPORTANT]
> **NON-ADJUDICATION GUARANTEE**:
> NYAYA-SATYA does **not** predict verdicts.
> NYAYA-SATYA does **not** act as an autonomous judge.
> NYAYA-SATYA does **not** autonomously determine guilt, fraud, perjury, liability, or win probabilities.
> 
> "Don't trust the draft. Attack it. Expose its dependencies. Identify what evidence would reduce uncertainty. Do not decide the verdict."
> 
> All adversarial stress-test outputs remain auditable proposals subject to the **Human Legal Gate** and UNWIND Core governance.

---

## 1. System Overview & Architecture

The **Adversarial Reasoning Subsystem (`nyaya_adversarial`)** implements deterministic case stress-testing against the immutable **Case Digital Twin (`nyaya_twin`)**. It subjects legal theories, claims, and evidence networks to rigorous adversarial counter-theories, simulated evidence removals, and missing-evidence impact assessments.

```
       ┌─────────────────────────────────────────────────────────────┐
       │                CASE DIGITAL TWIN (IMMUTABLE)                │
       │   Entities • Claims • Evidence Refs • Events • Relationships│
       └──────────────────────────────┬──────────────────────────────┘
                                      │ (Read-Only Copy)
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                  TARKA-VYUH ADVERSARIAL REASONING ENGINE                  │
├──────────────────────────┬──────────────────────────┬─────────────────────┤
│  EVIDENCE CONFLICT ARENA │   ADVERSARIAL GAUNTLET   │     JENGA ENGINE    │
│  - Pairwise Conflicts    │   - 10 Attack Classes    │  - Simulated Loss   │
│  - Hypothesis Competition│   - Isolated Simulation  │  - Cascade Collapse │
│  - Contradiction Clusters│   - Severity Evaluation  │  - Achilles Heels   │
├──────────────────────────┴──────────────────────────┴─────────────────────┤
│                       MISSING EVIDENCE & VoI FOUNDATION                   │
│  - Evidentiary Gaps • Critical Unknowns • Next-Best-Evidence Ranking       │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                 GOVERNANCE & HUMAN LEGAL GATE               │
       │  UNWIND State Machine • Audit Trail • Cryptographic Hashing │
       └─────────────────────────────────────────────────────────────┘
```

---

## 2. Immutability & Zero-Trust Guarantees

1. **Digital Twin Immutability**:
   All adversarial operations clone the `CaseDigitalTwin` prior to simulation. The canonical case record is **never** mutated by gauntlet attacks, hypothetical removals, or stress tests.
2. **Strict Evidence Quarantine**:
   Quarantined, unverified, or malicious evidence files are blocked at the perimeter. They can never enter the Gauntlet or Conflict Arena.
3. **No Fabricated Facts**:
   Missing evidence is surfaced as evidentiary questions, gaps, and requests for documents—never as hallucinated witness statements or fabricated documents.
4. **Deterministic Reproducibility**:
   Every attack, conflict, and Jenga calculation produces a deterministic SHA-256 fingerprint from canonical sorting of its inputs and parameters.

---

## 3. Subsystem Breakdown

### 3.1 Contracts (`nyaya_adversarial/contracts/`)
- `conflict.py`: `EvidenceConflict`, `ConflictType` (`DIRECT_CONTRADICTION`, `TEMPORAL_IMPOSSIBILITY`, `IDENTITY_AMBIGUITY`, `ALIBI_COLLISION`, `DOCUMENT_INTEGRITY_DISCREPANCY`, `PROVENANCE_GAP`, `CHAIN_OF_CUSTODY_DEFECT`), `ConflictSeverity` (`CRITICAL`, `MAJOR`, `MODERATE`, `MINOR`).
- `hypothesis.py`: `LegalHypothesis`, `HypothesisType` (`PRIMARY_THEORY`, `ALTERNATIVE_EXPLANATION`, `DEFENSE_THEORY`, `NULL_HYPOTHESIS`), `HypothesisStatus`.
- `attack.py`: `AdversarialAttack`, `AttackClass` (10 classes), `AttackSeverity`, `AttackStatus`, `AttackResult`.
- `fragility.py`: `FragilityReport`, `FragilityScore` (0.0 to 1.0), `FragilityLevel` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `RESILIENT`), `CascadeStep`.
- `assumption.py`: `CaseAssumption`, `AssumptionType` (`UNPROVEN_FACT`, `INFERRED_INTENT`, `ASSUMED_TIMELINE`, `UNVERIFIED_CUSTODY`), `AssumptionStatus`.
- `missing_evidence.py`: `MissingEvidenceItem`, `MissingCategory`, `ImpactPotential`.
- `voi.py`: `ValueCandidate`, `UncertaintyImpact`, `NextBestEvidence`.
- `result.py`: `AdversarialGauntletResult`, `AdversarialSummary`.

### 3.2 Evidence Conflict Arena (`nyaya_adversarial/arena/`)
- **ConflictArena**: Identifies pairwise contradictions, temporal impossibilities, and custody discrepancies across registered evidence items.
- **ContradictionCluster**: Multi-party, multi-document conflict grouping with graph-based cluster detection.
- **HypothesisManager**: Competing legal hypothesis manager tracking claims and supporting/contradicting evidence without choosing a winner.

### 3.3 The Adversarial Gauntlet (`nyaya_adversarial/gauntlet/`)
Implements **10 distinct attack classes** against claims and evidence:
1. `EVIDENCE_SUPPRESSION`: Tests claim survivability if primary evidence is ruled inadmissible or excluded.
2. `TIMELINE_DISRUPTION`: Introduces temporal ambiguity, reordering, or conflicting timestamp records.
3. `CREDIBILITY_IMPEACHMENT`: Challenges entity reliability, self-contradicting statements, or conflicts of interest.
4. `CHAIN_OF_CUSTODY_BREACH`: Probes document gaps, transfer signatures, or custody log interruptions.
5. `ALTERNATIVE_EXPLANATION`: Synthesizes coherent defense or null hypotheses explaining the same evidence.
6. `FABRICATION_STRESS`: Evaluates vulnerability if key evidence is flagged for integrity discrepancies.
7. `JURISDICTIONAL_DEFECT`: Tests statutory or jurisdictional prerequisite dependencies.
8. `HEARSAY_AMBIGUITY`: Scrutinizes uncorroborated out-of-court assertions or multi-hop statements.
9. `MISSING_CORROBORATION`: Targets uncorroborated single-source claims with zero secondary backing.
10. `FOUNDATIONAL_CHALLENGE`: Attacks root prerequisite claims that anchor multi-tier `DEPENDS_ON` chains.

### 3.4 Jenga Fragility & Achilles-Heel Engine (`nyaya_adversarial/jenga/`)
- **FragilityEngine**: Simulates evidence removal and tracks structural collapse across claims. Computes numerical fragility (0.0 = resilient, 1.0 = catastrophic).
- **DependencyStress**: Traverses multi-hop `DEPENDS_ON` DAGs to compute cascade propagation depth.
- **AchillesEngine**: Computes network centrality combined with fragility scores to isolate the single point of failure (Achilles Heel) in a legal theory.

### 3.5 Missing Evidence & Value-of-Information (`nyaya_adversarial/missing/`)
- **MissingEvidenceDetector**: Flags uncorroborated single-source claims, temporal voids, and missing foundational documents.
- **UncertaintyReductionEngine**: Calculates the uncertainty delta if a missing evidentiary item were obtained.
- **NextBestEvidenceRanker**: Deterministically prioritizes requests for records, bank statements, or official logs by maximum uncertainty reduction.

### 3.6 Validation & Non-Adjudication Enforcer (`nyaya_adversarial/validation/`)
- **ResultValidator**: Scans all outputs to strictly block prohibited judicial verdict language (`guilty`, `not guilty`, `liable`, `verdict`, `innocent`, `perjury`, `fraud confirmed`, `win probability`, `conviction likelihood`).
- **AttackValidator**: Enforces schema and parameter constraints on all adversarial attacks.
- **SafetyValidator**: Prevents quarantined or unsafe evidence from being accessed.

---

## 4. REST API Reference

All endpoints are mounted under `/api/nyaya/cases/{case_id}/adversarial` and require valid UNWIND operator/analyst bearer tokens:

| Endpoint | Method | Description |
|---|---|---|
| `/run` | `POST` | Executes full adversarial gauntlet and returns `AdversarialGauntletResult` |
| `/findings` | `GET` | Retrieves existing adversarial stress-test findings |
| `/conflicts` | `GET` | Lists all detected evidence conflicts and clusters |
| `/attacks` | `GET` | Lists all generated adversarial attacks with severity |
| `/fragility` | `GET` | Returns Jenga fragility report across all case claims |
| `/achilles-heels` | `GET` | Identifies critical single points of failure |
| `/assumptions` | `GET` | Lists registered implicit/explicit assumptions |
| `/assumptions` | `POST` | Registers a new case assumption for challenge |
| `/missing-evidence` | `GET` | Lists identified missing evidence gaps |
| `/next-best-evidence` | `GET` | Ranks high-value evidence items to reduce uncertainty |
| `/claims/{claim_id}/attacks` | `GET` | Retrieves all attacks targeting a specific claim |
| `/evidence/{evidence_id}/dependencies` | `GET` | Analyzes blast-radius if evidence is suppressed |
| `/validate` | `POST` | Validates adversarial proposals against non-adjudication rules |
| `/snapshot` | `GET` | Returns cryptographic snapshot and provenance hash |

---

## 5. Non-Adjudication Compliance Checklist

- [x] No verdict predictions (guilty, liable, acquitted).
- [x] No win/loss probabilities or outcome percentages.
- [x] CaseDigitalTwin is strictly read-only and immutable.
- [x] Missing items are identified as evidentiary voids, not facts.
- [x] All outputs format as auditable `ReasoningProposal` contracts for the Human Legal Gate.
