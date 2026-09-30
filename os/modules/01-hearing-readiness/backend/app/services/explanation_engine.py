"""
"Why?" Explanation Engine (section 9). Composes the fixed structured
explanation shape purely from fields that already exist on the
requirement/blocker/evidence rows -- it never invents a citation or a
page number that isn't already recorded.
"""
from __future__ import annotations


def explain_blocker(blocker: dict, requirement: dict, evidence_items: list[dict]) -> dict:
    evidence_lines = []
    for e in evidence_items:
        ref = e.get("page_ref")
        evidence_lines.append(
            f"{e['label']}" + (f" (page/section: {ref})" if ref else " (no page reference on file)")
        )

    unknowns = []
    if requirement.get("confidence") in ("LOW", "UNKNOWN"):
        unknowns.append("Confidence in this finding is low; more evidence review is recommended.")
    if not evidence_items:
        unknowns.append("No evidence has been linked to this requirement yet.")
    for e in evidence_items:
        if e.get("availability") == "UNKNOWN":
            unknowns.append(f"Availability of '{e['label']}' could not be confirmed from the record.")

    return {
        "what": f"{requirement['category']} requirement appears unresolved: {requirement['description']}.",
        "why": requirement.get("reason", "Not specified."),
        "evidence": evidence_lines or ["No supporting evidence on file."],
        "dependency": blocker.get("downstream_impact", ""),
        "confidence": requirement.get("confidence", "UNKNOWN"),
        "unknown": unknowns,
        "next_safe_action": blocker.get("suggested_safe_action", "None suggested."),
    }
