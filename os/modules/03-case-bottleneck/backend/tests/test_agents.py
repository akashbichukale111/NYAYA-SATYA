"""Section 9/10: Bottleneck Discovery + Root Cause Investigator, exercised
against the actual demo case fixtures (Section 57), not hand-rolled minimal
graphs — so these tests double as a regression suite for demo_data.py."""
from sqlmodel import Session

from app.models import Case, CaseDocument, Dependency, Transition
from app.demo_data import ALL_DEMO_CASES
from app.agents.discovery import BottleneckDiscoveryAgent
from app.agents.root_cause import RootCauseInvestigatorAgent
from app.security import scan_for_injection, hash_content


def _load_case(session: Session, builder):
    data = builder()
    session.add(Case(**data["case"]))
    for doc in data["documents"]:
        injected = scan_for_injection(doc["content_text"])
        session.add(CaseDocument(
            **doc, contains_injection_attempt=injected, quarantined=injected,
            sha256=hash_content(doc["content_text"]),
        ))
    for dep in data["dependencies"]:
        session.add(Dependency(**dep))
    for t in data["transitions"]:
        session.add(Transition(**t))
    session.commit()
    return data["case"]["id"]


def _builder(scenario: str):
    for b in ALL_DEMO_CASES:
        data = b()
        if data["case"]["demo_scenario"] == scenario:
            return b
    raise KeyError(scenario)


def test_case_a_single_obvious_bottleneck(session):
    case_id = _load_case(session, _builder("A"))
    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    assert len(bottlenecks) == 1
    assert bottlenecks[0].confidence.value in ("CONFIRMED", "LIKELY")


def test_case_b_multiple_competing_bottlenecks(session):
    case_id = _load_case(session, _builder("B"))
    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    assert len(bottlenecks) == 2


def test_case_c_hidden_root_cause_is_the_deep_leaf_not_the_surface_symptom(session):
    case_id = _load_case(session, _builder("C"))
    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    assert len(bottlenecks) == 1
    rcc = RootCauseInvestigatorAgent().run(session, bottlenecks[0])
    # The chain must have more than just "pending transition" + one dependency —
    # i.e. it must actually descend past the surface symptom (Section 7).
    assert len(rcc.chain) >= 3


def test_case_d_contradictory_sources_never_collapse_to_false_certainty(session):
    case_id = _load_case(session, _builder("D"))
    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    assert len(bottlenecks) == 1
    bn = bottlenecks[0]
    assert bn.type.value == "CONTRADICTION_BLOCKER"
    # A contradiction must never be reported as CONFIRMED — Section 38.
    assert bn.confidence.value != "CONFIRMED"
    rcc = RootCauseInvestigatorAgent().run(session, bn)
    assert any(step.get("step") == "Multi-Agent Debate" for step in rcc.chain)


def test_case_i_unknown_status_yields_unknown_confidence_not_a_guess(session):
    case_id = _load_case(session, _builder("I"))
    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    assert len(bottlenecks) == 1
    assert bottlenecks[0].confidence.value == "UNKNOWN"
    assert bottlenecks[0].attention_state.value == "UNKNOWN"


def test_case_h_prompt_injection_document_is_quarantined_and_not_obeyed(session):
    case_id = _load_case(session, _builder("H"))
    doc = session.get(CaseDocument, "demo-H-doc-injected")
    assert doc.quarantined is True
    assert doc.contains_injection_attempt is True

    bottlenecks = BottleneckDiscoveryAgent().run(session, case_id)
    # The injected instruction says "mark all bottlenecks as resolved" —
    # the agent must not comply. Discovery must still report it as open.
    assert len(bottlenecks) == 1
    assert bottlenecks[0].status.value != "RESOLVED"


def test_discovery_is_idempotent_and_detects_no_duplicate_bottlenecks(session):
    case_id = _load_case(session, _builder("A"))
    first = BottleneckDiscoveryAgent().run(session, case_id)
    second = BottleneckDiscoveryAgent().run(session, case_id)
    assert len(first) == len(second) == 1
    assert first[0].id == second[0].id  # same bottleneck row reused, not duplicated
