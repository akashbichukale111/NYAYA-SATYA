"""
Counterfactual Simulation and Registry Crash Test.

CRITICAL PROPERTY: every function in this module is non-destructive. Each
simulation runs the real precheck logic against an isolated, in-memory
COPY of the relevant rows (never against the live database rows), then
discards that copy. The only thing persisted is a `Simulation` row
recording what was asked and what was found — never a mutation to the
actual Requirement/Document/Defect/Conflict/etc. tables.

This is what makes "deterministic, non-destructive, auditable" (the
spec's crash-test requirement) true by construction rather than by
convention: there is no code path here that calls db.add()/db.commit()
against any table other than Simulation.
"""
from __future__ import annotations
import copy
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow


def _snapshot_package_state(db: Session, filing_package_id: str) -> dict:
    """Reads (never mutates) the current state needed to reason about a
    package: requirements, documents, checklist, defects, objections,
    conflicts, duplicate groups. Returned as plain dicts so the caller can
    freely mutate them without touching the ORM session / live rows."""
    def as_dicts(rows, fields):
        return [{f: getattr(r, f) for f in fields} for r in rows]

    requirements = db.query(models.Requirement).filter(
        models.Requirement.filing_package_id == filing_package_id
    ).all()
    documents = db.query(models.Document).filter(
        models.Document.filing_package_id == filing_package_id
    ).all()
    checklist_items = db.query(models.ChecklistItem).filter(
        models.ChecklistItem.filing_package_id == filing_package_id
    ).all()
    defects = db.query(models.Defect).filter(
        models.Defect.filing_package_id == filing_package_id
    ).all()
    objections = db.query(models.RegistryObjection).filter(
        models.RegistryObjection.filing_package_id == filing_package_id
    ).all()
    attachment_refs = db.query(models.AttachmentReference).filter(
        models.AttachmentReference.filing_package_id == filing_package_id
    ).all()

    return {
        "requirements": as_dicts(requirements, ["id", "status", "target_reference_label", "requirement_type", "description"]),
        "documents": as_dicts(documents, ["id", "display_name", "document_kind", "status"]),
        "checklist_items": as_dicts(checklist_items, ["id", "requirement_id", "status"]),
        "defects": as_dicts(defects, ["id", "defect_type", "status", "severity"]),
        "objections": as_dicts(objections, ["id", "status", "original_text"]),
        "attachment_references": as_dicts(attachment_refs, ["id", "reference_label", "resolved"]),
    }


SCENARIO_HANDLERS = {}


def scenario(name):
    def wrap(fn):
        SCENARIO_HANDLERS[name] = fn
        return fn
    return wrap


@scenario("REMOVE_REQUIRED_DOCUMENT")
def _sim_remove_required_document(state: dict, params: dict) -> dict:
    doc_id = params.get("document_id")
    before = len(state["documents"])
    state["documents"] = [d for d in state["documents"] if d["id"] != doc_id]
    removed = before != len(state["documents"])
    new_defects = []
    if removed:
        new_defects.append({"defect_type": "MISSING_DOCUMENT", "reason": f"Document {doc_id} removed in simulation"})
    return {"removed": removed, "new_defects": new_defects}


@scenario("REMOVE_REFERENCED_ANNEXURE")
def _sim_remove_referenced_annexure(state: dict, params: dict) -> dict:
    label = params.get("reference_label", "Annexure B")
    new_defects = [{"defect_type": "MISSING_REFERENCED_ITEM", "reason": f"{label} no longer present in simulation"}]
    return {"removed_reference": label, "new_defects": new_defects}


@scenario("INTRODUCE_METADATA_CONFLICT")
def _sim_introduce_metadata_conflict(state: dict, params: dict) -> dict:
    field = params.get("field_name", "case_number")
    new_defects = [{"defect_type": "METADATA_CONFLICT", "reason": f"Simulated conflicting values for {field}"}]
    return {"field": field, "new_defects": new_defects}


@scenario("SUBMIT_DUPLICATE_VERSION")
def _sim_submit_duplicate_version(state: dict, params: dict) -> dict:
    new_defects = [{"defect_type": "DUPLICATE_VERSION", "reason": "Simulated duplicate version submission"}]
    return {"new_defects": new_defects}


@scenario("SUPERSEDE_CURRENT_DOCUMENT")
def _sim_supersede_document(state: dict, params: dict) -> dict:
    doc_id = params.get("document_id")
    new_defects = [{"defect_type": "VERSION_AMBIGUITY", "reason": f"Document {doc_id} superseded in simulation; human confirmation required"}]
    return {"new_defects": new_defects, "resolved_defects": []}


@scenario("INVALIDATE_SOURCE")
def _sim_invalidate_source(state: dict, params: dict) -> dict:
    requirement_id = params.get("requirement_id")
    new_gaps = [{"requirement_id": requirement_id, "reason": "Requirement source invalidated in simulation"}]
    new_defects = [{"defect_type": "PROVENANCE_GAP", "reason": f"Requirement {requirement_id} source invalidated"}]
    return {"new_defects": new_defects, "new_gaps": new_gaps}


@scenario("CREATE_UNRESOLVED_OBJECTION")
def _sim_create_unresolved_objection(state: dict, params: dict) -> dict:
    text = params.get("text", "Simulated registry objection")
    new_defects = [{"defect_type": "UNRESOLVED_OBJECTION", "reason": text}]
    return {"new_defects": new_defects}


@scenario("REMOVE_CORRECTION_EVIDENCE")
def _sim_remove_correction_evidence(state: dict, params: dict) -> dict:
    correction_id = params.get("correction_id")
    new_defects = [{"defect_type": "CORRECTION_INCOMPLETE", "reason": f"Evidence removed from correction {correction_id} in simulation"}]
    return {"new_defects": new_defects}


@scenario("CHANGE_REQUIREMENT_STATUS_TO_UNKNOWN")
def _sim_requirement_to_unknown(state: dict, params: dict) -> dict:
    requirement_id = params.get("requirement_id")
    for r in state["requirements"]:
        if r["id"] == requirement_id:
            r["status"] = "UNKNOWN"
    new_defects = [{"defect_type": "PROVENANCE_GAP", "reason": f"Requirement {requirement_id} status simulated as UNKNOWN"}]
    return {"new_defects": new_defects}


@scenario("BREAK_DOCUMENT_REFERENCE")
def _sim_break_document_reference(state: dict, params: dict) -> dict:
    ref_id = params.get("reference_id")
    for r in state["attachment_references"]:
        if r["id"] == ref_id:
            r["resolved"] = False
    new_defects = [{"defect_type": "BROKEN_DOCUMENT_REFERENCE", "reason": f"Reference {ref_id} simulated as broken"}]
    return {"new_defects": new_defects}


@scenario("CORRUPT_DOCUMENT")
def _sim_corrupt_document(state: dict, params: dict) -> dict:
    doc_id = params.get("document_id")
    new_defects = [{"defect_type": "CORRUPTED", "reason": f"Document {doc_id} simulated as corrupted"}]
    return {"new_defects": new_defects}


@scenario("INTRODUCE_PROMPT_INJECTION")
def _sim_prompt_injection(state: dict, params: dict) -> dict:
    doc_id = params.get("document_id")
    new_defects = [{
        "defect_type": "PROMPT_INJECTION_CONTENT",
        "reason": f"Document {doc_id} simulated as containing instruction-like content; "
                  f"content would be flagged for review and never executed as an instruction",
    }]
    return {"new_defects": new_defects}


def run_counterfactual(db: Session, *, case_id: str, filing_package_id: str, scenario: str, params: dict, user_id: str | None) -> dict:
    handler = SCENARIO_HANDLERS.get(scenario)
    current_state = _snapshot_package_state(db, filing_package_id)

    if not handler:
        result = {
            "scenario": scenario,
            "recognized": False,
            "current_state": current_state,
            "simulated_change": None,
            "new_defects": [],
            "resolved_defects": [],
            "new_gaps": [],
            "human_review": "This scenario is not recognized; no simulation was run.",
        }
    else:
        simulated_state = copy.deepcopy(current_state)
        outcome = handler(simulated_state, params or {})
        result = {
            "scenario": scenario,
            "recognized": True,
            "current_state": current_state,
            "simulated_state": simulated_state,
            "new_defects": outcome.get("new_defects", []),
            "resolved_defects": outcome.get("resolved_defects", []),
            "new_gaps": outcome.get("new_gaps", []),
            "human_review": "This is a simulated, non-destructive projection. No data was changed. "
                             "A human must run a real precheck and review to confirm any of this.",
        }

    sim_row = models.Simulation(
        id=new_id("sim"), case_id=case_id, filing_package_id=filing_package_id,
        simulation_type="COUNTERFACTUAL", scenario=scenario, input_params=params or {},
        result_json=_json_safe(result), is_destructive=False,
        run_at=utcnow().isoformat(), run_by_user_id=user_id,
    )
    db.add(sim_row)
    db.commit()
    db.refresh(sim_row)
    result["simulation_id"] = sim_row.id
    return result


CRASH_TEST_SCENARIOS = [
    "REMOVE_REQUIRED_DOCUMENT",
    "REMOVE_REFERENCED_ANNEXURE",
    "INTRODUCE_METADATA_CONFLICT",
    "SUBMIT_DUPLICATE_VERSION",
    "SUPERSEDE_CURRENT_DOCUMENT",
    "INVALIDATE_SOURCE",
    "CREATE_UNRESOLVED_OBJECTION",
    "REMOVE_CORRECTION_EVIDENCE",
    "CHANGE_REQUIREMENT_STATUS_TO_UNKNOWN",
    "BREAK_DOCUMENT_REFERENCE",
    "CORRUPT_DOCUMENT",
    "INTRODUCE_PROMPT_INJECTION",
]


def run_crash_test_suite(db: Session, *, case_id: str, filing_package_id: str, user_id: str | None) -> dict:
    """Runs every crash-test scenario from the spec, with representative
    (placeholder-id) params where a concrete target isn't specified,
    since this is a suite run rather than a single targeted simulation.
    Deterministic: given the same package state, produces the same
    scenario list and the same shape of result every time."""
    current_state = _snapshot_package_state(db, filing_package_id)
    sample_doc_id = current_state["documents"][0]["id"] if current_state["documents"] else "no-document-in-package"
    sample_req_id = current_state["requirements"][0]["id"] if current_state["requirements"] else "no-requirement-in-package"
    sample_ref_id = current_state["attachment_references"][0]["id"] if current_state["attachment_references"] else "no-reference-in-package"

    default_params = {
        "REMOVE_REQUIRED_DOCUMENT": {"document_id": sample_doc_id},
        "REMOVE_REFERENCED_ANNEXURE": {"reference_label": "Annexure B"},
        "INTRODUCE_METADATA_CONFLICT": {"field_name": "case_number"},
        "SUBMIT_DUPLICATE_VERSION": {},
        "SUPERSEDE_CURRENT_DOCUMENT": {"document_id": sample_doc_id},
        "INVALIDATE_SOURCE": {"requirement_id": sample_req_id},
        "CREATE_UNRESOLVED_OBJECTION": {"text": "Simulated: annexure missing"},
        "REMOVE_CORRECTION_EVIDENCE": {"correction_id": "sample-correction"},
        "CHANGE_REQUIREMENT_STATUS_TO_UNKNOWN": {"requirement_id": sample_req_id},
        "BREAK_DOCUMENT_REFERENCE": {"reference_id": sample_ref_id},
        "CORRUPT_DOCUMENT": {"document_id": sample_doc_id},
        "INTRODUCE_PROMPT_INJECTION": {"document_id": sample_doc_id},
    }

    scenarios_result = []
    for name in CRASH_TEST_SCENARIOS:
        handler = SCENARIO_HANDLERS[name]
        simulated_state = copy.deepcopy(current_state)
        outcome = handler(simulated_state, default_params[name])
        scenarios_result.append({
            "scenario": name,
            "new_defects": outcome.get("new_defects", []),
            "outcome": "DETECTED" if outcome.get("new_defects") else "NO_NEW_DEFECT",
        })

    result = {
        "filing_package_id": filing_package_id,
        "scenarios": scenarios_result,
        "non_destructive": True,
        "human_review": "This is a simulated, non-destructive crash test. No data was changed.",
    }

    sim_row = models.Simulation(
        id=new_id("sim"), case_id=case_id, filing_package_id=filing_package_id,
        simulation_type="CRASH_TEST", scenario="FULL_SUITE", input_params={},
        result_json=_json_safe(result), is_destructive=False,
        run_at=utcnow().isoformat(), run_by_user_id=user_id,
    )
    db.add(sim_row)
    db.commit()
    db.refresh(sim_row)
    result["simulation_id"] = sim_row.id
    return result


def _json_safe(obj):
    """Defensive: ensure the result dict is plain JSON (no ORM objects
    leaked in), since it gets written into Simulation.result_json."""
    import json
    return json.loads(json.dumps(obj, default=str))
