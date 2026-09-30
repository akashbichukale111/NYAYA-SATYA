"""
Integration adapters.

Each adapter normalizes a specific upstream engine's event shape into a
common, generic NormalizedTrigger the planner already understands. Adapters
never touch another engine's internal database schema — they accept
plain dicts (what an HTTP webhook or message-queue payload would look like)
and produce a normalized trigger. Business/legal meaning stays entirely
inside the upstream engine; the adapter only re-shapes envelope fields.
"""
import datetime as dt
from dataclasses import dataclass, field


@dataclass
class NormalizedTrigger:
    case_id: str
    trigger_type: str
    source_engine: str
    source_event_id: str
    occurred_at: str
    raw_payload: dict = field(default_factory=dict)


class BaseAdapter:
    """Subclasses declare `source_engine` and implement `normalize`."""
    source_engine: str = "unknown"

    def normalize(self, event: dict) -> NormalizedTrigger:
        raise NotImplementedError

    def _base(self, event: dict, trigger_type: str) -> NormalizedTrigger:
        return NormalizedTrigger(
            case_id=event["case_id"],
            trigger_type=trigger_type,
            source_engine=self.source_engine,
            source_event_id=event.get("event_id", f"{self.source_engine}-{event.get('case_id')}-{event.get('kind','')}"),
            occurred_at=event.get("occurred_at", dt.datetime.now(dt.timezone.utc).isoformat()),
            raw_payload=event,
        )


class CaseContinuityAdapter(BaseAdapter):
    source_engine = "CaseContinuityAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "CASE_CHANGED")


class EvidenceDependencyAdapter(BaseAdapter):
    source_engine = "EvidenceDependencyAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "NEW_EVIDENCE_GAP")


class ProceduralObligationAdapter(BaseAdapter):
    source_engine = "ProceduralObligationAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        kind = event.get("kind", "created")
        trigger_type = "OBLIGATION_BLOCKED" if kind == "blocked" else "OBLIGATION_CREATED"
        return self._base(event, trigger_type)


class RegistryDefectAdapter(BaseAdapter):
    source_engine = "RegistryDefectAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "REGISTRY_DEFECT_DETECTED")


class UndertrialLibertyAdapter(BaseAdapter):
    source_engine = "UndertrialLibertyAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        # Liberty-related attention never maps to an automated template —
        # it always requires a manually-typed workflow after human review.
        return self._base(event, "MANUAL_TRIGGER")


class HearingReadinessAdapter(BaseAdapter):
    source_engine = "HearingReadinessAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "HEARING_READINESS_BLOCKER")


class CaseBottleneckAdapter(BaseAdapter):
    source_engine = "CaseBottleneckAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "CASE_BOTTLENECK_DETECTED")


class DeadlineGuardianAdapter(BaseAdapter):
    source_engine = "DeadlineGuardianAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        kind = event.get("kind", "approaching")
        trigger_type = "PAST_TRACKED_DATE" if kind == "past" else "TRACKED_DATE_APPROACHING"
        return self._base(event, trigger_type)


class LegalAidHandoffAdapter(BaseAdapter):
    source_engine = "LegalAidHandoffAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "HANDOFF_REQUIRED")


class CrashTestAdapter(BaseAdapter):
    source_engine = "CrashTestAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        return self._base(event, "MANUAL_TRIGGER")


class SparkPersonalOSAdapter(BaseAdapter):
    """Outbound direction: SPARK Personal OS calls /api/cases/{id}/workflow-summary
    directly (see app/api/main.py) rather than receiving pushed events, so this
    adapter exists to document the contract, not to normalize inbound events."""
    source_engine = "SparkPersonalOSAdapter"

    def normalize(self, event: dict) -> NormalizedTrigger:
        raise NotImplementedError(
            "SparkPersonalOSAdapter is pull-based; use GET /api/cases/{case_id}/workflow-summary"
        )


ADAPTERS = {
    "case_continuity": CaseContinuityAdapter(),
    "evidence_dependency": EvidenceDependencyAdapter(),
    "procedural_obligation": ProceduralObligationAdapter(),
    "registry_defect": RegistryDefectAdapter(),
    "undertrial_liberty": UndertrialLibertyAdapter(),
    "hearing_readiness": HearingReadinessAdapter(),
    "case_bottleneck": CaseBottleneckAdapter(),
    "deadline_guardian": DeadlineGuardianAdapter(),
    "legal_aid_handoff": LegalAidHandoffAdapter(),
    "crash_test": CrashTestAdapter(),
}


def get_adapter(name: str) -> BaseAdapter:
    if name not in ADAPTERS:
        raise ValueError(f"unknown adapter: {name}")
    return ADAPTERS[name]
