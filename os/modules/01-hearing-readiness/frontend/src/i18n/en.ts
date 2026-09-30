const en = {
  "nav.command_center": "Command Center",
  "nav.cases": "Cases",
  "nav.readiness": "Readiness",
  "nav.blockers": "Blockers",
  "nav.evidence": "Evidence",
  "nav.timeline": "Timeline",
  "nav.simulate": "Simulate",
  "nav.crash_test": "Crash Test",
  "nav.time_machine": "Time Machine",
  "nav.evaluation_lab": "Evaluation Lab",
  "nav.audit": "Audit",
  "nav.settings": "Settings",

  "app.tagline": "Don't waste a hearing date because nobody knew what was missing.",
  "app.demo_mode": "Demo Mode — deterministic mock provider, no API key required",

  "readiness.READY": "Ready",
  "readiness.CONDITIONAL": "Conditional",
  "readiness.BLOCKED": "Blocked",
  "readiness.UNKNOWN": "Unknown",

  "common.loading": "Loading…",
  "common.error": "Something went wrong",
  "common.retry": "Retry",
  "common.approve": "Approve",
  "common.edit": "Edit",
  "common.reject": "Reject",
  "common.confidence": "Confidence",
  "common.why": "Why?",
  "common.next_hearing": "Next hearing",
  "common.no_data": "Nothing here yet.",

  "settings.language": "Language",
  "settings.low_bandwidth": "Low-bandwidth mode",
  "settings.low_bandwidth_desc": "Reduces animation and visual weight for constrained connections.",
} as const;

export type TranslationKey = keyof typeof en;
export default en;
