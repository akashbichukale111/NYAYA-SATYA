"""
Handoff Crash Test (sec 48).

Runs constructed adversarial cases through run_quality_and_risk_checks /
privacy.is_allowed and asserts the engine catches each one. Uses
lightweight in-memory stand-ins (not DB rows) so this never touches
production data. Implements 5 of the 11 listed mutations; the remainder
(duplicate document, stale handoff version, wrong recipient role as a
distinct DB-level test, alter-date-after-generation, regression replay
of prior tests) are tracked as NOT_IMPLEMENTED in docs/LIMITATIONS.md
rather than faked.
"""
from types import SimpleNamespace
from models import FactStatus, Sensitivity, Role
from handoff.generator import run_quality_and_risk_checks
from privacy.engine import is_allowed


def _fact(label, status, sensitivity=Sensitivity.INTERNAL):
    return SimpleNamespace(id=f"fact_{label}", label=label, status=status, sensitivity=sensitivity)


def run_crash_tests() -> list[dict]:
    results = []

    # 1. remove_critical_fact -> engine must flag critical_facts_sourced
    facts = [_fact("notice_date", FactStatus.NOT_PROVIDED)]
    checks, risks = run_quality_and_risk_checks(
        included_facts=facts, all_facts=facts, documents=[], deadlines=[], conflicts=[],
        excluded_notes=[], recipient_role=Role.ADVOCATE,
    )
    results.append({
        "mutation": "remove_critical_fact",
        "expected": "FAIL/BLOCKED caught by critical_facts_sourced check",
        "result": "PASS" if checks["overall"] == "BLOCKED" else "FAIL",
    })

    # 2. inject_unsupported_fact -> should appear as a risk, not silently pass
    facts = [_fact("verified_fact", FactStatus.VERIFIED), _fact("guess", FactStatus.UNKNOWN)]
    checks, risks = run_quality_and_risk_checks(
        included_facts=facts, all_facts=facts, documents=[], deadlines=[], conflicts=[],
        excluded_notes=[], recipient_role=Role.ADVOCATE,
    )
    caught = any(r["risk"] == "unsupported_critical_fact" for r in risks)
    results.append({
        "mutation": "inject_unsupported_fact",
        "expected": "flagged in risk_flags",
        "result": "PASS" if caught else "FAIL",
    })

    # 3. hide_conflict -> conflicts_visible check must be honest about count
    checks, risks = run_quality_and_risk_checks(
        included_facts=[], all_facts=[], documents=[], deadlines=[],
        conflicts=[SimpleNamespace(id="c1")], excluded_notes=[], recipient_role=Role.PARALEGAL,
    )
    results.append({
        "mutation": "hide_conflict",
        "expected": "conflicts_visible detail mentions the conflict, overall != READY_FOR_REVIEW",
        "result": "PASS" if checks["overall"] != "READY_FOR_REVIEW" else "FAIL",
    })

    # 4. expose_restricted_field -> privacy engine must reject HIGHLY_SENSITIVE to CITIZEN
    allowed = is_allowed(Sensitivity.HIGHLY_SENSITIVE, Role.CITIZEN)
    results.append({
        "mutation": "expose_restricted_field",
        "expected": "HIGHLY_SENSITIVE denied to CITIZEN role",
        "result": "PASS" if not allowed else "FAIL",
    })

    # 5. wrong_recipient_role (role above its own ceiling requesting HIGHLY_SENSITIVE as PARALEGAL)
    allowed2 = is_allowed(Sensitivity.HIGHLY_SENSITIVE, Role.PARALEGAL)
    results.append({
        "mutation": "role_ceiling_paralegal_highly_sensitive",
        "expected": "HIGHLY_SENSITIVE denied to PARALEGAL (ceiling is SENSITIVE)",
        "result": "PASS" if not allowed2 else "FAIL",
    })

    return results
