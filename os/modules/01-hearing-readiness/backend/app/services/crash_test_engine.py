"""
Case/Hearing Crash Test (section 16). Every mutation function operates on
an in-memory deep copy of requirement/evidence dicts loaded fresh from the
DB; nothing is ever written back for these rows, so real evidence is never
destructively mutated. Only the CrashTest result row is persisted.
"""
from __future__ import annotations

import copy

from app.models.requirement import Requirement
from app.models.evidence import Evidence
from app.models.blocker import Blocker
from app.models.hearing import Hearing
from app.models.crash_test import CrashTest
from app.services.readiness_engine import build_readiness_snapshot, compute_requirement_status


def _load(db, case_id: str):
    reqs = [r.to_dict() for r in db.query(Requirement).filter(Requirement.case_id == case_id).all()]
    evid = {e.id: e.to_dict() for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()}
    blockers = [b.to_dict() for b in db.query(Blocker).filter(Blocker.case_id == case_id).all()]
    hearing = db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    hearing_uncertain = (hearing is None) or (hearing.purpose_status == "UNCERTAIN")
    return reqs, evid, blockers, hearing_uncertain


def _recompute(reqs, evid, hearing_uncertain, blockers):
    reqs = copy.deepcopy(reqs)
    for r in reqs:
        linked = [evid[eid] for eid in (r.get("evidence_refs") or []) if eid in evid]
        status, _, confidence = compute_requirement_status(linked)
        r["status"], r["confidence"] = status, confidence
    return build_readiness_snapshot(reqs, blockers, hearing_uncertain)


# Each mutation returns (mutated_evidence, mutated_requirements, impacted_ids, expected_effect)
def _mut_remove_evidence(evid, reqs):
    evid = copy.deepcopy(evid)
    if not evid:
        return evid, reqs, [], "no_change (no evidence to remove)"
    target_id = next(iter(evid))
    del evid[target_id]
    return evid, reqs, [target_id], "at_least_one_requirement_becomes_unresolved_or_unknown"


def _mut_alter_availability(evid, reqs):
    evid = copy.deepcopy(evid)
    available = [e for e in evid.values() if e["availability"] == "AVAILABLE"]
    if not available:
        return evid, reqs, [], "no_change (nothing available to alter)"
    target = available[0]
    target["availability"] = "MISSING"
    return evid, reqs, [target["id"]], "linked_requirement_becomes_unresolved"


def _mut_introduce_contradiction(evid, reqs):
    evid = copy.deepcopy(evid)
    verified = [e for e in evid.values() if e["verification_state"] == "VERIFIED"]
    if not verified:
        return evid, reqs, [], "no_change (nothing verified to contradict)"
    target = verified[0]
    target["verification_state"] = "DISPUTED"
    return evid, reqs, [target["id"]], "linked_requirement_becomes_unresolved"


def _mut_remove_dependency(evid, reqs):
    reqs = copy.deepcopy(reqs)
    linked = [r for r in reqs if r.get("evidence_refs")]
    if not linked:
        return evid, reqs, [], "no_change (no requirement had linked evidence)"
    target = linked[0]
    removed = target["evidence_refs"]
    target["evidence_refs"] = []
    return evid, reqs, [target["id"]], "requirement_becomes_unknown (no evidence linked)"


def _mut_add_irrelevant_doc(evid, reqs):
    # Adding an unrelated evidence item must NOT change any existing
    # requirement's computed status -- this tests noise-robustness.
    evid = copy.deepcopy(evid)
    new_id = "evi_irrelevant_synthetic"
    evid[new_id] = {
        "id": new_id, "label": "Irrelevant synthetic document", "availability": "AVAILABLE",
        "verification_state": "VERIFIED",
    }
    return evid, reqs, [new_id], "no_change_to_existing_requirements"


def _mut_change_service_status(evid, reqs):
    evid = copy.deepcopy(evid)
    service_items = [e for e in evid.values() if "service" in e["label"].lower()]
    if not service_items:
        return evid, reqs, [], "no_change (no service-related evidence present)"
    available = [e for e in service_items if e["availability"] == "AVAILABLE"]
    if not available:
        # Every service item is already unavailable -- flipping it again has
        # no further effect on readiness, and that IS the correct expectation.
        return evid, reqs, [service_items[0]["id"]], "no_change (service evidence already unavailable)"
    target = available[0]
    target["availability"] = "MISSING"
    return evid, reqs, [target["id"]], "service_requirement_becomes_unresolved"


def _mut_modify_requirement_input(evid, reqs):
    reqs = copy.deepcopy(reqs)
    if not reqs:
        return evid, reqs, [], "no_change (no requirements present)"
    target = reqs[0]
    target["evidence_refs"] = ["nonexistent_evidence_id"]
    return evid, reqs, [target["id"]], "requirement_becomes_unknown (dangling reference)"


def _mut_stale_state(evid, reqs):
    evid = copy.deepcopy(evid)
    for e in evid.values():
        if e.get("confidence") == "HIGH":
            e["confidence"] = "LOW"
    # Confidence is metadata on the evidence record; it does not feed into
    # compute_requirement_status()'s availability/verification_state logic,
    # so category/overall readiness must NOT change from this mutation alone.
    return evid, reqs, list(evid.keys()), "no_change (confidence metadata is not a status input)"


def _mut_duplicate_evidence(evid, reqs):
    evid = copy.deepcopy(evid)
    if not evid:
        return evid, reqs, [], "no_change (no evidence to duplicate)"
    src_id = next(iter(evid))
    src = evid[src_id]
    dup_id = src_id + "_dup"
    evid[dup_id] = {**src, "id": dup_id}
    return evid, reqs, [dup_id], "no_change_to_requirement_status (duplicate not referenced)"


MUTATIONS = {
    "remove_evidence": _mut_remove_evidence,
    "alter_availability": _mut_alter_availability,
    "introduce_contradiction": _mut_introduce_contradiction,
    "remove_dependency": _mut_remove_dependency,
    "add_irrelevant_document": _mut_add_irrelevant_doc,
    "change_service_status": _mut_change_service_status,
    "modify_requirement_input": _mut_modify_requirement_input,
    "stale_state": _mut_stale_state,
    "duplicate_evidence": _mut_duplicate_evidence,
}


def run_crash_test(db, case_id: str, mutation_name: str) -> CrashTest:
    if mutation_name not in MUTATIONS:
        raise ValueError(f"Unknown mutation '{mutation_name}'. Options: {list(MUTATIONS)}")

    reqs, evid, blockers, hearing_uncertain = _load(db, case_id)
    baseline_snapshot = build_readiness_snapshot(reqs, blockers, hearing_uncertain)

    mutated_evid, mutated_reqs, impacted, expected_effect = MUTATIONS[mutation_name](evid, reqs)
    mutated_snapshot = _recompute(mutated_reqs, mutated_evid, hearing_uncertain, blockers)

    changed = mutated_snapshot["categories"] != baseline_snapshot["categories"] or \
        mutated_snapshot["overall"] != baseline_snapshot["overall"]

    if expected_effect.startswith("no_change"):
        observed_effect = "no_change" if not changed else "state_changed_unexpectedly"
        passed = not changed
    else:
        observed_effect = "state_changed" if changed else "no_change_but_expected_change"
        passed = changed

    explanation = (
        f"Mutation '{mutation_name}' expected '{expected_effect}'. "
        f"Baseline overall={baseline_snapshot['overall']}, categories={baseline_snapshot['categories']}. "
        f"Post-mutation overall={mutated_snapshot['overall']}, categories={mutated_snapshot['categories']}."
    )

    record = CrashTest(
        case_id=case_id, mutation=mutation_name, expected_effect=expected_effect,
        observed_effect=observed_effect, passed="true" if passed else "false",
        explanation=explanation, impacted_state=impacted, regression_status="NOT_APPLICABLE",
    )
    db.add(record)
    db.flush()
    return record


def run_all_crash_tests(db, case_id: str) -> list[CrashTest]:
    return [run_crash_test(db, case_id, name) for name in MUTATIONS]
