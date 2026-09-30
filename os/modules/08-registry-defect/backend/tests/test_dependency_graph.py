from app.services import precheck, requirement_engine, dependency_graph, impact_analysis
from app import models
from app.core.ids import new_id, utcnow


def _setup(db_session):
    case = models.Case(id=new_id("case"), title="T", status="ACTIVE",
                        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(case)
    db_session.commit()
    pkg = models.FilingPackage(id=new_id("pkg"), case_id=case.id, name="P", lifecycle_state="DRAFT",
                                created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(pkg)
    db_session.commit()
    return case, pkg


def test_dependency_graph_links_requirement_to_checklist_to_defect(db_session):
    case, pkg = _setup(db_session)
    requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Affidavit required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist item 1",
        target_reference_label="Affidavit",
    )
    precheck.run_precheck(db_session, case_id=case.id, filing_package_id=pkg.id)

    graph = dependency_graph.build_dependency_graph(db_session, filing_package_id=pkg.id)
    kinds = {n["kind"] for n in graph["nodes"]}
    assert "REQUIREMENT" in kinds
    assert "CHECKLIST_ITEM" in kinds
    assert "DEFECT" in kinds

    edge_kinds = {e["kind"] for e in graph["edges"]}
    assert "REQUIREMENT_TO_CHECKLIST" in edge_kinds
    assert "REQUIREMENT_TO_DEFECT" in edge_kinds


def test_dependency_graph_never_synthesizes_relationships_not_in_db(db_session):
    case, pkg = _setup(db_session)
    graph = dependency_graph.build_dependency_graph(db_session, filing_package_id=pkg.id)
    # Nothing in the package yet -> empty graph, not a fabricated one.
    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_impact_analysis_traces_affected_requirement_and_checklist(db_session):
    case, pkg = _setup(db_session)
    requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Proof of ID required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist item 2",
        target_reference_label="Proof of ID",
    )
    precheck.run_precheck(db_session, case_id=case.id, filing_package_id=pkg.id)
    defect = db_session.query(models.Defect).filter(models.Defect.filing_package_id == pkg.id).first()

    impact = impact_analysis.analyze_defect_impact(db_session, defect_id=defect.id)
    assert impact["found"] is True
    assert len(impact["affected_requirements"]) == 1
    assert len(impact["affected_checklist_items"]) == 1
    # Never claims a legal consequence.
    assert "reject" not in impact["note"].lower()
    assert "invalid" not in impact["note"].lower()


def test_impact_analysis_unknown_defect_returns_not_found(db_session):
    impact = impact_analysis.analyze_defect_impact(db_session, defect_id="dft_nonexistent")
    assert impact["found"] is False
