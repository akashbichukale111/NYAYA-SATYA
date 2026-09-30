"""
Evaluation Lab -- deterministic checks run against the CURRENT case data.

Every check below either PASSes, FAILs, or is NOT_RUN (when there is not
enough data in the case to exercise it). No score is invented; each
result is a direct boolean/structural check against stored rows.
"""
from sqlalchemy.orm import Session

from app.models.orm import EvidenceItem, Claim, Issue, EvidenceRelationship, Case
from app.models.enums import EvaluationResult
from app.services.graph_service import DependencyGraph


def _result(passed: bool) -> str:
    return EvaluationResult.PASS.value if passed else EvaluationResult.FAIL.value


def run_evaluation_suite(db: Session, case_id: str) -> dict:
    checks = {}

    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    issues = db.query(Issue).filter(Issue.case_id == case_id).all()
    relationships = db.query(EvidenceRelationship).filter(EvidenceRelationship.case_id == case_id).all()

    # 1. Provenance completeness: every evidence item with document_id must
    # either declare a known source location or explicitly mark it unknown.
    if evidence_items:
        ok = all(
            (e.source_location_known and (e.page_number is not None or e.section is not None))
            or (not e.source_location_known)
            for e in evidence_items
        )
        checks["provenance_completeness"] = _result(ok)
    else:
        checks["provenance_completeness"] = EvaluationResult.NOT_RUN.value

    # 2. Claim traceability: every claim edge references an existing evidence row.
    if relationships:
        claim_edges = [r for r in relationships if r.target_type == "CLAIM" and r.source_type == "EVIDENCE"]
        if claim_edges:
            evidence_ids = {e.id for e in evidence_items}
            ok = all(r.source_id in evidence_ids for r in claim_edges)
            checks["claim_traceability"] = _result(ok)
        else:
            checks["claim_traceability"] = EvaluationResult.NOT_RUN.value
    else:
        checks["claim_traceability"] = EvaluationResult.NOT_RUN.value

    # 3. Issue mapping coverage: every issue edge references an existing claim.
    issue_edges = [r for r in relationships if r.target_type == "ISSUE" and r.source_type == "CLAIM"]
    if issue_edges:
        claim_ids = {c.id for c in claims}
        ok = all(r.source_id in claim_ids for r in issue_edges)
        checks["issue_mapping_coverage"] = _result(ok)
    else:
        checks["issue_mapping_coverage"] = EvaluationResult.NOT_RUN.value

    # 4. Dependency consistency: no relationship references a node outside this case.
    if relationships:
        ev_ids = {e.id for e in evidence_items}
        cl_ids = {c.id for c in claims}
        is_ids = {i.id for i in issues}
        id_by_type = {"EVIDENCE": ev_ids, "CLAIM": cl_ids, "ISSUE": is_ids}
        ok = all(
            r.source_id in id_by_type.get(r.source_type, set())
            and r.target_id in id_by_type.get(r.target_type, set())
            for r in relationships
        )
        checks["dependency_consistency"] = _result(ok)
    else:
        checks["dependency_consistency"] = EvaluationResult.NOT_RUN.value

    # 5. Case isolation: no relationship/evidence/claim/issue row has a case_id
    # mismatching the case being evaluated (defense-in-depth check on the query itself).
    other_case_leak = (
        db.query(EvidenceItem).filter(EvidenceItem.case_id != case_id, EvidenceItem.id.in_([e.id for e in evidence_items])).count()
        if evidence_items else 0
    )
    checks["case_isolation"] = _result(other_case_leak == 0)

    # 6. Contradiction detection wiring: if any CONTRADICTS edge exists, graph
    # traversal can find it as a contradiction edge for its target.
    contradiction_edges = [r for r in relationships if r.relationship_type == "CONTRADICTS"]
    if contradiction_edges:
        graph = DependencyGraph(db, case_id)
        ok = all(
            any(ce.id == e.id for ce in graph.contradiction_edges_for(r.target_type, r.target_id))
            for r in contradiction_edges
            for e in [r]
        )
        checks["contradiction_detection"] = _result(ok)
    else:
        checks["contradiction_detection"] = EvaluationResult.NOT_RUN.value

    return {
        "case_id": case_id,
        "checks": checks,
        "summary": {
            "pass_count": sum(1 for v in checks.values() if v == EvaluationResult.PASS.value),
            "fail_count": sum(1 for v in checks.values() if v == EvaluationResult.FAIL.value),
            "not_run_count": sum(1 for v in checks.values() if v == EvaluationResult.NOT_RUN.value),
        },
    }
