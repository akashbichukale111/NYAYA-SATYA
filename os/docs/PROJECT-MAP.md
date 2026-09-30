# NYAYA-SATYA OS — Project Map & Functional Taxonomy

NYAYA-SATYA OS integrates 12 modular legal engines organized across 5 core functional categories.

---

## Architecture Grouping

```
                     ┌──────────────────────────────────────────────┐
                     │            NYAYA-SATYA OS SHELL              │
                     │  Global Case Context • Ctrl+K Search • Gate  │
                     └──────────────────────┬───────────────────────┘
                                            │
        ┌───────────────────────────────────┴───────────────────────────────────┐
        │                                                                       │
┌───────▼──────────────┐   ┌──────────────────────┐   ┌─────────────────────────▼────────────┐
│ EVIDENCE & REASONING │   │ PROCEDURAL & RULE    │   │ CASE ACCELERATION                    │
│                      │   │                      │   │                                      │
│ 06: Evidence Depend. │   │ 02: Case Continuity  │   │ 01: Hearing Readiness                │
│ 09: Case Crash Test  │   │ 05: Procedural Oblig │   │ 03: Case Bottleneck Engine           │
│                      │   │ 08: Registry Defect  │   │                                      │
└──────────────────────┘   │ 11: Deadline Guard.  │   └──────────────────────────────────────┘
                           └──────────┬───────────┘
                                      │
        ┌─────────────────────────────┴─────────────────────────────────────────┐
        │                                                                       │
┌───────▼──────────────┐                                      ┌─────────────────▼────────────────────┐
│ HUMAN RIGHTS & LAW   │                                      │ PRACTICE AUTOMATION                  │
│                      │                                      │                                      │
│ 04: Legal-Aid Handoff│                                      │ 10: Spark Personal OS                │
│ 07: Undertrial Sent. │                                      │ 12: Spark Workflow Autopilot         │
└──────────────────────┘                                      └──────────────────────────────────────┘
```

---

## 1. Evidence & Adversarial Reasoning
- **06. Evidence Dependency Engine**: Maps the bipartite directed acyclic graph (DAG) connecting legal assertions (claims) to physical, testimonial, and electronic exhibits. Automatically computes claim vulnerability and single points of evidentiary failure.
- **09. Case Crash Test / Resilience Lab**: Runs adversarial stress scenarios against legal arguments (e.g. key witness turning hostile, electronic evidence excluded under Section 63 BSA). Evaluates cascading failure blast radiuses and computes the case resilience score.

## 2. Procedural Governance & Compliance
- **02. Case Continuity Engine**: Tracks cross-counsel handoffs, ordersheet vs pleading contradictions, and discrepancies in procedural steps to prevent institutional memory loss.
- **05. Procedural Obligation Engine**: Strict WHO / WHAT / LOSS / SIGN implementation ensuring that any invalidated filing or unserved notice results in a human-signed correction obligation.
- **08. Registry Defect Engine**: Scrutinizes petitions against High Court and District Court filing rules, detects formatting/notarization/annexure defects, and calculates curative actions within statutory scrutiny windows.
- **11. Spark Deadline Guardian**: Statutory limitation and court timeline calculator. Automatically accounts for court vacations, limitation triggers under the Limitation Act 1963, and raises escalation alerts.

## 3. Case Acceleration & Bottlenecks
- **01. Hearing Readiness Engine**: Conducts pre-hearing audits to ensure all prerequisites (service of summons, certified copies, witness lists) are met before hearing date to eliminate routine adjournments.
- **03. Case Bottleneck Engine**: Analyzes median stage duration per court and isolates root-cause blockages (e.g. summons service delay, forensic laboratory backlogs).

## 4. Human Rights & Liberty
- **04. Legal-Aid Handoff Engine**: Packages criminal and civil dockets into comprehensive briefing packets for legal-aid counsel, preserving all mapped facts, timelines, and bail grounds.
- **07. Undertrial Liberty Sentinel**: Enforces Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS) and Section 436A of the Code of Criminal Procedure (CrPC). Monitors detention duration against the 1/3rd maximum imprisonment threshold for first-time offenders to secure statutory bail.

## 5. Practice Automation
- **10. Spark Personal OS**: Generates morning digests, manages personalized case views, monitors priority change feeds, and powers practitioner daily workflow.
- **12. Spark Workflow Autopilot**: Coordinates procedural Standard Operating Procedures (SOPs) across multi-stage workflows with strict human sign-off gates.
