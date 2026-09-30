"""Unified Attention Center for NYAYA-SATYA OS.
Aggregates prioritized alerts, statutory deadlines, liberty risks, and filing defects.
"""

from typing import List, Dict, Optional
from datetime import datetime
from contracts.models import AttentionItem, AttentionSeverity


DEFAULT_ATTENTION_ITEMS: List[AttentionItem] = [
    AttentionItem(
        id="ATTN-2024-001",
        case_id="CASE-2024-DEL-0482",
        source_module_id="mod-07-undertrial-liberty",
        source_module_name="Undertrial Liberty Sentinel",
        severity=AttentionSeverity.CRITICAL,
        title="Statutory Bail Threshold Exceeded (Section 479 BNSS)",
        description="Accused Rajesh Kumar has completed 14 months in custody, exceeding 1/3rd of maximum sentence for first-time charge. Entitled to mandatory statutory bail petition.",
        action_label="Review Bail Entitlement",
        target_route="/modules/undertrial-liberty",
        is_resolved=False,
        requires_human_signoff=True
    ),
    AttentionItem(
        id="ATTN-2024-002",
        case_id="CASE-2024-DEL-0482",
        source_module_id="mod-08-registry-defect",
        source_module_name="Registry Defect Engine",
        severity=AttentionSeverity.HIGH,
        title="Registry Scrutiny: Unserved Notice on Accused No. 2",
        description="Filing scrutiny defect reported: Process server returned unserved summons. Hearing listed for 2024-10-18 will be adjourned unless dasti notice is ordered.",
        action_label="Generate Curative Application",
        target_route="/modules/registry-defect",
        is_resolved=False,
        requires_human_signoff=True
    ),
    AttentionItem(
        id="ATTN-2024-003",
        case_id="CASE-2024-DEL-0482",
        source_module_id="mod-06-evidence-dependency",
        source_module_name="Evidence Dependency Engine",
        severity=AttentionSeverity.HIGH,
        title="Single-Point Evidence Failure: Forensic Hash Mismatch",
        description="Claim 4 (Device Custody) relies solely on Exhibit P-3. Hash comparison revealed discrepancy with seizure memo. Secondary corroboration required.",
        action_label="Inspect Dependency Graph",
        target_route="/modules/evidence-dependency",
        is_resolved=False,
        requires_human_signoff=False
    ),
    AttentionItem(
        id="ATTN-2024-004",
        case_id="CASE-2024-DEL-0482",
        source_module_id="mod-11-spark-deadline-guardian",
        source_module_name="Spark Deadline Guardian",
        severity=AttentionSeverity.MEDIUM,
        title="Statutory Limitation: 4 Days Remaining for Reply",
        description="Section 173(8) further investigation objections must be filed before 2024-10-04. Limitation period expires under Delhi High Court Rules.",
        action_label="View Limitation Calendar",
        target_route="/modules/spark-deadline-guardian",
        is_resolved=False,
        requires_human_signoff=True
    ),
    AttentionItem(
        id="ATTN-2024-005",
        case_id="CASE-2023-BOM-1109",
        source_module_id="mod-03-case-bottleneck",
        source_module_name="Case Bottleneck Engine",
        severity=AttentionSeverity.HIGH,
        title="Procedural Bottleneck: 112 Days in Admission Arguments",
        description="Stage duration exceeds Bombay High Court median by 340%. Cause: delay in submission of joint compilation of documents.",
        action_label="Apply Bottleneck Remediation",
        target_route="/modules/case-bottleneck",
        is_resolved=False,
        requires_human_signoff=True
    ),
    AttentionItem(
        id="ATTN-2024-006",
        case_id="CASE-2024-KA-0077",
        source_module_id="mod-05-procedural-obligation",
        source_module_name="Procedural Obligation Engine",
        severity=AttentionSeverity.CRITICAL,
        title="Pending Human Signature on Corrected Affirmation",
        description="Obligation OBL-2024-098 requires Adv. Roopa Shankar signoff before submitting cured writ petition to High Court registry.",
        action_label="Sign Obligation",
        target_route="/modules/procedural-obligation",
        is_resolved=False,
        requires_human_signoff=True
    )
]


class AttentionCenter:
    def __init__(self):
        self._items: Dict[str, AttentionItem] = {item.id: item for item in DEFAULT_ATTENTION_ITEMS}

    def list_all(self, case_id: Optional[str] = None) -> List[AttentionItem]:
        if case_id:
            return [i for i in self._items.values() if i.case_id == case_id]
        return list(self._items.values())

    def get_unresolved(self, case_id: Optional[str] = None) -> List[AttentionItem]:
        items = self.list_all(case_id)
        return [i for i in items if not i.is_resolved]

    def resolve(self, item_id: str) -> Optional[AttentionItem]:
        if item_id in self._items:
            self._items[item_id].is_resolved = True
            return self._items[item_id]
        return None

    def add_item(self, item: AttentionItem) -> AttentionItem:
        self._items[item.id] = item
        return item


attention_center = AttentionCenter()
