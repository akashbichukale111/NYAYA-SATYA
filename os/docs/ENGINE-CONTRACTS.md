# NYAYA-SATYA OS — Engine Contracts & Shared Data Schemas

This document defines the core data contracts located in `os/contracts/models.py`.

---

## 1. CaseContext Contract

The authoritative case object passed across all 12 engines:

```python
class CaseContext(BaseModel):
    case_id: str                      # Unique case ID (e.g. CASE-2024-DEL-0482)
    title: str                        # Case title (e.g. State v. Rajesh Kumar)
    court: str                        # Jurisdiction (e.g. Tis Hazari District Court)
    jurisdiction: JurisdictionalDomain# CIVIL, CRIMINAL, CONSTITUTIONAL, COMMERCIAL...
    stage: ProceduralStage            # INTAKE, FILING_DEFECT_SCRUTINY, BAIL_HEARING...
    statute: str                      # Governing statute(s)
    filing_date: str                  # Original filing date
    next_hearing: Optional[str]       # Scheduled next hearing date
    lead_counsel: str                 # Assigned lead advocate
    undertrial_in_custody: bool       # Custody flag
    custody_start_date: Optional[str] # Detention start date
    human_authorized: bool            # UNWIND Legal Gate approval flag
    summary: str                      # Executive background
    tags: List[str]                   # Filter tags
```

---

## 2. AttentionItem Contract

Defines prioritized cross-engine alerts:

```python
class AttentionSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Immediate statutory/liberty jeopardy
    HIGH = "HIGH"          # Filing defect / unserved notice blocking hearing
    MEDIUM = "MEDIUM"      # Evidentiary gap / upcoming limitation deadline
    LOW = "LOW"            # Recommended optimization / workflow cleanup
    INFO = "INFO"          # General notification

class AttentionItem(BaseModel):
    id: str
    case_id: str
    source_module_id: str
    source_module_name: str
    severity: AttentionSeverity
    title: str
    description: str
    action_label: Optional[str]
    target_route: Optional[str]
    is_resolved: bool
    requires_human_signoff: bool
```

---

## 3. Procedural Obligation Contract (WHO / WHAT / LOSS / SIGN)

Enforces non-negotiable legal compliance structure:

```python
class ObligationRecord(BaseModel):
    obligation_id: str
    case_id: str
    title: str
    status: ObligationStatus         # AWAITING_AUTHORISATION, AUTHORISED, DISPATCHED
    counterparties: List[CounterpartyNotice]  # WHO: told invalid claims
    reversible_actions: List[str]             # WHAT: actions to execute
    irreversible_loss: IrreversibleLossExposure# LOSS: range with stated assumptions
    approver: Optional[str]                  # SIGN: human lawyer
    signed_at: Optional[datetime]
    ruling_basis: str
```
