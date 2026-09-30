"""
Deterministic synthetic DEMO cases. Every node created here is clearly
synthetic (labels prefixed, is_demo=True on the Case). No real case data is
ever used to generate these. Every screen/response referencing a demo case
must display: "DEMONSTRATION DATA — NOT A REAL CASE" — this label is
returned by the /integration-summary and demo endpoints alongside the data;
enforcing it in the UI is a Section 3 (frontend) task.
"""

from sqlalchemy.orm import Session

from app.models.domain import Case, CaseNode, CaseRelationship
from app.simulation_engine.snapshot_service import create_snapshot

DEMO_DISCLAIMER = "DEMONSTRATION DATA — NOT A REAL CASE"


def _node(case_id, node_type, label, status="KNOWN", **attrs):
    return CaseNode(case_id=case_id, node_type=node_type, label=label, status=status, attributes=attrs)


def _rel(case_id, source, target, rel_type):
    return CaseRelationship(case_id=case_id, source_id=source.id, target_id=target.id, rel_type=rel_type)


def build_demo_a_evidence_collapse(db: Session) -> Case:
    """Demo A: one evidence item supports multiple downstream nodes; removing it collapses support."""
    case = Case(title="[DEMO] Evidence Collapse", description=DEMO_DISCLAIMER, is_demo=True)
    db.add(case)
    db.flush()

    evidence = _node(case.id, "EVIDENCE", "[DEMO] Evidence E12 — recovered device log", status="VERIFIED")
    claim_a = _node(case.id, "CLAIM", "[DEMO] Claim C4 — timeline claim", status="VERIFIED")
    claim_b = _node(case.id, "CLAIM", "[DEMO] Claim C5 — location claim", status="VERIFIED")
    issue = _node(case.id, "ISSUE", "[DEMO] Issue I2 — timeline consistency", status="KNOWN")
    obligation = _node(case.id, "OBLIGATION", "[DEMO] Obligation O3 — disclosure requirement", status="KNOWN")
    hearing = _node(case.id, "HEARING", "[DEMO] Hearing H1 — readiness review", status="KNOWN")

    db.add_all([evidence, claim_a, claim_b, issue, obligation, hearing])
    db.flush()

    db.add_all([
        _rel(case.id, claim_a, evidence, "DEPENDS_ON"),
        _rel(case.id, claim_b, evidence, "DEPENDS_ON"),
        _rel(case.id, issue, claim_a, "DEPENDS_ON"),
        _rel(case.id, obligation, issue, "DEPENDS_ON"),
        _rel(case.id, hearing, obligation, "DEPENDS_ON"),
    ])
    db.commit()
    create_snapshot(db, case.id, label="initial", created_by="demo-loader")
    return case


def build_demo_b_obligation_cascade(db: Session) -> Case:
    """Demo B: one blocked obligation affects a workflow and a hearing-readiness item."""
    case = Case(title="[DEMO] Obligation Cascade", description=DEMO_DISCLAIMER, is_demo=True)
    db.add(case)
    db.flush()

    obligation = _node(case.id, "OBLIGATION", "[DEMO] Obligation O7 — filing deadline compliance", status="KNOWN")
    workflow = _node(case.id, "WORKFLOW", "[DEMO] Workflow W2 — pre-hearing checklist", status="KNOWN")
    action = _node(case.id, "ACTION", "[DEMO] Action A5 — submit compliance form", status="KNOWN")
    hearing = _node(case.id, "HEARING", "[DEMO] Hearing H2 — readiness review", status="KNOWN")

    db.add_all([obligation, workflow, action, hearing])
    db.flush()

    db.add_all([
        _rel(case.id, workflow, obligation, "DEPENDS_ON"),
        _rel(case.id, action, workflow, "DEPENDS_ON"),
        _rel(case.id, hearing, action, "DEPENDS_ON"),
    ])
    db.commit()
    create_snapshot(db, case.id, label="initial", created_by="demo-loader")
    return case


def build_demo_c_registry_document_failure(db: Session) -> Case:
    """Demo C: removing a required filing document creates downstream registry defects."""
    case = Case(title="[DEMO] Registry + Document Failure", description=DEMO_DISCLAIMER, is_demo=True)
    db.add(case)
    db.flush()

    document = _node(case.id, "DOCUMENT", "[DEMO] Document D9 — required filing annexure", status="VERIFIED")
    filing_package = _node(case.id, "FILING_PACKAGE", "[DEMO] Filing Package F1", status="KNOWN")
    registry_defect = _node(case.id, "REGISTRY_DEFECT", "[DEMO] Registry check RC-1", status="KNOWN")
    workflow = _node(case.id, "WORKFLOW", "[DEMO] Workflow W3 — registry clearance", status="KNOWN")

    db.add_all([document, filing_package, registry_defect, workflow])
    db.flush()

    db.add_all([
        _rel(case.id, filing_package, document, "REQUIRES"),
        _rel(case.id, registry_defect, filing_package, "DEPENDS_ON"),
        _rel(case.id, workflow, registry_defect, "DEPENDS_ON"),
    ])
    db.commit()
    create_snapshot(db, case.id, label="initial", created_by="demo-loader")
    return case


def build_demo_d_multi_failure(db: Session) -> Case:
    """Demo D: combined evidence-unverified + order-superseded + hearing-missing + workflow-blocked."""
    case = Case(title="[DEMO] Multi-Failure Scenario", description=DEMO_DISCLAIMER, is_demo=True)
    db.add(case)
    db.flush()

    evidence = _node(case.id, "EVIDENCE", "[DEMO] Evidence E20 — witness statement", status="VERIFIED")
    order = _node(case.id, "ORDER", "[DEMO] Order OR4 — procedural order", status="VERIFIED")
    hearing = _node(case.id, "HEARING", "[DEMO] Hearing H4 — status hearing", status="VERIFIED")
    workflow = _node(case.id, "WORKFLOW", "[DEMO] Workflow W9 — evidence intake", status="KNOWN")
    claim = _node(case.id, "CLAIM", "[DEMO] Claim C11 — corroborated claim", status="VERIFIED")
    obligation = _node(case.id, "OBLIGATION", "[DEMO] Obligation O15 — pre-trial obligation", status="KNOWN")

    db.add_all([evidence, order, hearing, workflow, claim, obligation])
    db.flush()

    db.add_all([
        _rel(case.id, claim, evidence, "DEPENDS_ON"),
        _rel(case.id, obligation, order, "DEPENDS_ON"),
        _rel(case.id, workflow, hearing, "DEPENDS_ON"),
        _rel(case.id, obligation, claim, "DEPENDS_ON"),
    ])
    db.commit()
    create_snapshot(db, case.id, label="initial", created_by="demo-loader")
    return case


def load_all_demo_cases(db: Session) -> list[Case]:
    return [
        build_demo_a_evidence_collapse(db),
        build_demo_b_obligation_cascade(db),
        build_demo_c_registry_document_failure(db),
        build_demo_d_multi_failure(db),
    ]
