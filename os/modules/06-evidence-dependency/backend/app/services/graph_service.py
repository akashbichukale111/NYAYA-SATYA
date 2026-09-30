"""
Dependency graph construction + traversal.

This is the core differentiator of the product: build an explicit
Evidence -> Claim -> Issue graph (plus lateral edges) from stored rows,
and answer graph-derived questions (coverage, fragility, impact) purely
from real data. Nothing here invents a relationship, a confidence score,
or a source location that isn't in the database.
"""
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

from sqlalchemy.orm import Session

from app.models.orm import EvidenceRelationship, EvidenceItem, Claim, Issue
from app.models.enums import EvidenceState, RelationshipType

# Relationship types that count as "this target depends on this source
# being valid/available" for forward dependency-impact traversal.
SUPPORT_LIKE = {
    RelationshipType.SUPPORTS.value,
    RelationshipType.PARTIALLY_SUPPORTS.value,
    RelationshipType.CORROBORATES.value,
    RelationshipType.REQUIRES.value,
    RelationshipType.DEPENDS_ON.value,
}

NEGATIVE_LIKE = {
    RelationshipType.CONTRADICTS.value,
}


class DependencyGraph:
    """In-memory adjacency built from EvidenceRelationship rows for one case."""

    def __init__(self, db: Session, case_id: str):
        self.db = db
        self.case_id = case_id
        self.edges: List[EvidenceRelationship] = (
            db.query(EvidenceRelationship)
            .filter(EvidenceRelationship.case_id == case_id, EvidenceRelationship.is_active == True)  # noqa: E712
            .all()
        )
        # forward[node_key] = list of (edge)
        self.forward: Dict[Tuple[str, str], List[EvidenceRelationship]] = defaultdict(list)
        self.backward: Dict[Tuple[str, str], List[EvidenceRelationship]] = defaultdict(list)
        for e in self.edges:
            self.forward[(e.source_type, e.source_id)].append(e)
            self.backward[(e.target_type, e.target_id)].append(e)

    def downstream_impact(self, node_type: str, node_id: str) -> Dict:
        """
        BFS forward from a node along SUPPORT_LIKE edges to find every
        claim/issue that would lose support if this node were removed.
        Returns real traversal results only.
        """
        visited: Set[Tuple[str, str]] = set()
        affected_claims: Set[str] = set()
        affected_issues: Set[str] = set()
        queue = deque([(node_type, node_id)])
        visited.add((node_type, node_id))

        while queue:
            cur = queue.popleft()
            for edge in self.forward.get(cur, []):
                if edge.relationship_type not in SUPPORT_LIKE:
                    continue
                tgt = (edge.target_type, edge.target_id)
                if edge.target_type == "CLAIM":
                    affected_claims.add(edge.target_id)
                elif edge.target_type == "ISSUE":
                    affected_issues.add(edge.target_id)
                if tgt not in visited:
                    visited.add(tgt)
                    queue.append(tgt)

        return {
            "affected_claims": sorted(affected_claims),
            "affected_issues": sorted(affected_issues),
            "affected_node_count": len(visited) - 1,
        }

    def support_edges_for(self, node_type: str, node_id: str) -> List[EvidenceRelationship]:
        """All incoming SUPPORT_LIKE edges into a given claim/issue."""
        return [
            e for e in self.backward.get((node_type, node_id), [])
            if e.relationship_type in SUPPORT_LIKE
        ]

    def contradiction_edges_for(self, node_type: str, node_id: str) -> List[EvidenceRelationship]:
        return [
            e for e in self.backward.get((node_type, node_id), [])
            if e.relationship_type in NEGATIVE_LIKE
        ]

    def has_conflicting_support(self, node_type: str, node_id: str) -> bool:
        """
        True if this node is directly contradicted (a CONTRADICTS edge
        targets it), OR -- for a claim -- if two of its own supporting
        evidence items directly contradict each other. This is what makes
        an Evidence<->Evidence CONTRADICTS edge (e.g. from the Contradiction
        Agent) visible as "this claim has conflicting evidence" even though
        neither evidence item's edge targets the claim itself.
        """
        if self.contradiction_edges_for(node_type, node_id):
            return True
        if node_type != "CLAIM":
            return False
        support = self.support_edges_for(node_type, node_id)
        evidence_ids = [e.source_id for e in support if e.source_type == "EVIDENCE"]
        for i in range(len(evidence_ids)):
            for j in range(i + 1, len(evidence_ids)):
                a, b = evidence_ids[i], evidence_ids[j]
                for edge in self.forward.get(("EVIDENCE", a), []):
                    if edge.relationship_type in NEGATIVE_LIKE and edge.target_id == b:
                        return True
                for edge in self.forward.get(("EVIDENCE", b), []):
                    if edge.relationship_type in NEGATIVE_LIKE and edge.target_id == a:
                        return True
        return False

    def independent_source_count(self, node_type: str, node_id: str) -> int:
        """
        Count distinct upstream *documents* supporting a node, walking back
        through evidence edges. Two evidence items from the same document
        are NOT counted as independent (per spec: don't assume independence
        just because files differ -- here we go one step further and key
        on the actual document_id, the ground truth of independence).
        """
        edges = self.support_edges_for(node_type, node_id)
        doc_ids: Set[str] = set()
        no_doc_evidence: Set[str] = set()
        for e in edges:
            if e.source_type != "EVIDENCE":
                continue
            ev = self.db.query(EvidenceItem).filter(EvidenceItem.id == e.source_id).first()
            if ev and ev.document_id:
                doc_ids.add(ev.document_id)
            elif ev:
                no_doc_evidence.add(ev.id)
        return len(doc_ids) + len(no_doc_evidence)


def coverage_metrics(db: Session, case_id: str) -> Dict:
    """Real, graph-derived coverage metrics -- see spec section 3."""
    graph = DependencyGraph(db, case_id)
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    issues = db.query(Issue).filter(Issue.case_id == case_id).all()
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()

    claims_with_evidence = 0
    single_source_claims = 0
    conflicting_claims = 0
    for c in claims:
        support = graph.support_edges_for("CLAIM", c.id)
        if support:
            claims_with_evidence += 1
        if graph.independent_source_count("CLAIM", c.id) == 1:
            single_source_claims += 1
        if graph.has_conflicting_support("CLAIM", c.id):
            conflicting_claims += 1

    issues_with_supporting_claims = 0
    for i in issues:
        support = graph.support_edges_for("ISSUE", i.id)
        if support:
            issues_with_supporting_claims += 1

    verified = sum(1 for e in evidence_items if e.verification_status == "VERIFIED")
    unverified = sum(1 for e in evidence_items if e.verification_status != "VERIFIED")

    return {
        "claims_total": len(claims),
        "claims_with_evidence": claims_with_evidence,
        "claims_without_evidence": len(claims) - claims_with_evidence,
        "issues_total": len(issues),
        "issues_with_supporting_claims": issues_with_supporting_claims,
        "unsupported_issues": len(issues) - issues_with_supporting_claims,
        "conflicting_claims": conflicting_claims,
        "single_source_claims": single_source_claims,
        "verified_evidence_items": verified,
        "unverified_evidence_items": unverified,
        "evidence_items_total": len(evidence_items),
    }


def fragility_report(db: Session, case_id: str) -> List[Dict]:
    """
    For every evidence item, compute what breaks if it disappears.
    Sorted by number of affected claims+issues, descending -- surfaces
    single-point-of-failure evidence first.
    """
    graph = DependencyGraph(db, case_id)
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    report = []
    for ev in evidence_items:
        impact = graph.downstream_impact("EVIDENCE", ev.id)
        affected_total = len(impact["affected_claims"]) + len(impact["affected_issues"])
        criticality = "NONE"
        if affected_total == 0:
            criticality = "NONE"
        elif any(
            graph.independent_source_count("CLAIM", cid) == 1
            for cid in impact["affected_claims"]
        ):
            criticality = "SINGLE_POINT_DEPENDENCY"
        elif affected_total >= 3:
            criticality = "MODERATE"
        elif affected_total >= 1:
            criticality = "LOW"
        report.append({
            "evidence_id": ev.id,
            "label": ev.label,
            "affected_claims": impact["affected_claims"],
            "affected_issues": impact["affected_issues"],
            "dependency_count": affected_total,
            "criticality": criticality,
        })
    report.sort(key=lambda r: r["dependency_count"], reverse=True)
    return report


def missing_evidence_report(db: Session, case_id: str) -> Dict:
    """Claims/issues with no evidence, insufficient evidence, or only conflicting/excluded support."""
    graph = DependencyGraph(db, case_id)
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    issues = db.query(Issue).filter(Issue.case_id == case_id).all()

    no_evidence = []
    fragile_single_source = []
    conflicting_only = []

    for c in claims:
        support = graph.support_edges_for("CLAIM", c.id)
        contradictions_direct = graph.contradiction_edges_for("CLAIM", c.id)
        conflicting = graph.has_conflicting_support("CLAIM", c.id)
        if not support and not contradictions_direct:
            no_evidence.append({"claim_id": c.id, "text": c.text})
        elif not support and contradictions_direct:
            conflicting_only.append({"claim_id": c.id, "text": c.text})
        elif graph.independent_source_count("CLAIM", c.id) == 1 and not conflicting:
            fragile_single_source.append({"claim_id": c.id, "text": c.text})

    unsupported_issues = []
    for i in issues:
        support = graph.support_edges_for("ISSUE", i.id)
        if not support:
            unsupported_issues.append({"issue_id": i.id, "question": i.question})

    return {
        "claims_without_evidence": no_evidence,
        "claims_with_only_conflicting_evidence": conflicting_only,
        "claims_with_single_source_only": fragile_single_source,
        "issues_without_supporting_claims": unsupported_issues,
    }
