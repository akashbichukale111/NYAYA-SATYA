"""
State Diff Engine (section 7 of the spec).

Given two Case Digital Twin snapshots (dicts produced by state_twin.build_snapshot,
or historical StateVersion.snapshot rows), compute a structured diff broken
down by entity collection (deadlines, obligations, orders, hearings, evidence,
actions, documents), with each item tagged as ADDED / REMOVED / CHANGED.

This module does NOT decide "RESOLVED" vs "NEWLY_BLOCKED" vs "STALE" vs
"UNCERTAIN" - those richer semantic categories are attached by the
Change Detection / Reconciliation / Staleness agents when they record
StateChange rows (see app/agents/*). This module gives the raw structural
diff they build on top of.
"""
from typing import Any

ENTITY_COLLECTIONS = ["deadlines", "obligations", "orders", "hearings", "evidence", "actions", "documents"]


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"entities": {}, "summary": {"added": 0, "removed": 0, "changed": 0}}

    for collection in ENTITY_COLLECTIONS:
        before_items: dict[str, dict] = before.get(collection, {}) or {}
        after_items: dict[str, dict] = after.get(collection, {}) or {}

        added = [{"id": k, "after": v} for k, v in after_items.items() if k not in before_items]
        removed = [{"id": k, "before": v} for k, v in before_items.items() if k not in after_items]
        changed = []
        for k in after_items.keys() & before_items.keys():
            if before_items[k] != after_items[k]:
                changed_fields = {
                    field: {"before": before_items[k].get(field), "after": after_items[k].get(field)}
                    for field in set(before_items[k]) | set(after_items[k])
                    if before_items[k].get(field) != after_items[k].get(field)
                }
                changed.append({"id": k, "before": before_items[k], "after": after_items[k], "fields": changed_fields})

        result["entities"][collection] = {"added": added, "removed": removed, "changed": changed}
        result["summary"]["added"] += len(added)
        result["summary"]["removed"] += len(removed)
        result["summary"]["changed"] += len(changed)

    result["summary"]["open_items_delta"] = after.get("open_items_count", 0) - before.get("open_items_count", 0)
    result["summary"]["procedural_stage_before"] = before.get("procedural_stage")
    result["summary"]["procedural_stage_after"] = after.get("procedural_stage")
    return result
