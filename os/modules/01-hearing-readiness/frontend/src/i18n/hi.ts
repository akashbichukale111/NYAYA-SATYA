// PARTIAL translation -- proves the localization architecture works
// end-to-end (see i18n/index.ts fallback logic), but full Hindi coverage
// of every string is PLANNED, not implemented, per the project's honesty
// requirement (section 45: distinguish implemented vs planned).
import type { TranslationKey } from "./en";

const hi: Partial<Record<TranslationKey, string>> = {
  "nav.command_center": "कमांड सेंटर",
  "nav.cases": "मामले",
  "nav.readiness": "तैयारी",
  "nav.blockers": "अवरोध",
  "nav.evidence": "साक्ष्य",
  "nav.audit": "ऑडिट",
  "nav.settings": "सेटिंग्स",
  "readiness.READY": "तैयार",
  "readiness.CONDITIONAL": "सशर्त",
  "readiness.BLOCKED": "अवरुद्ध",
  "readiness.UNKNOWN": "अज्ञात",
  "common.loading": "लोड हो रहा है…",
  "common.next_hearing": "अगली सुनवाई",
};

export default hi;
