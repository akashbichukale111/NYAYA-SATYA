// PARTIAL translation -- see hi.ts comment. Same honesty caveat applies.
import type { TranslationKey } from "./en";

const mr: Partial<Record<TranslationKey, string>> = {
  "nav.command_center": "कमांड सेंटर",
  "nav.cases": "प्रकरणे",
  "nav.readiness": "सज्जता",
  "nav.blockers": "अडथळे",
  "nav.evidence": "पुरावा",
  "nav.audit": "लेखापरीक्षण",
  "nav.settings": "सेटिंग्ज",
  "readiness.READY": "सज्ज",
  "readiness.CONDITIONAL": "सशर्त",
  "readiness.BLOCKED": "अडथळा आलेला",
  "readiness.UNKNOWN": "अज्ञात",
  "common.loading": "लोड होत आहे…",
  "common.next_hearing": "पुढील सुनावणी",
};

export default mr;
