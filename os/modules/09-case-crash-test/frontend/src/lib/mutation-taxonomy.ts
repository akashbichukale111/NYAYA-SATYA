// Mirrors backend/app/enums.py MutationType exactly, grouped by the crash
// scenario taxonomy from the master spec. Every entry here is implemented
// in backend/app/simulation_engine/mutation_engine.py — no dead options.

export const MUTATION_GROUPS: { group: string; mutations: string[] }[] = [
  {
    group: "Evidence Failure",
    mutations: [
      "REMOVE_EVIDENCE",
      "EXCLUDE_EVIDENCE",
      "MARK_EVIDENCE_UNVERIFIED",
      "INVALIDATE_PROVENANCE",
      "CONTRADICT_EVIDENCE",
      "SUPERSEDE_EVIDENCE",
    ],
  },
  {
    group: "Document Failure",
    mutations: [
      "REMOVE_DOCUMENT",
      "CORRUPT_DOCUMENT",
      "SUPERSEDE_DOCUMENT",
      "REPLACE_DOCUMENT_VERSION",
      "MAKE_DOCUMENT_UNAVAILABLE",
    ],
  },
  {
    group: "Claim Failure",
    mutations: ["REMOVE_CLAIM", "CONTRADICT_CLAIM", "MARK_CLAIM_UNVERIFIED", "BREAK_CLAIM_DEPENDENCY"],
  },
  {
    group: "Issue Failure",
    mutations: ["REMOVE_ISSUE_SUPPORT", "CREATE_ISSUE_CONFLICT", "MARK_ISSUE_UNKNOWN"],
  },
  {
    group: "Obligation Failure",
    mutations: [
      "BLOCK_OBLIGATION",
      "REMOVE_OBLIGATION_EVIDENCE",
      "MARK_OBLIGATION_UNVERIFIED",
      "SUPERSEDE_OBLIGATION",
      "CREATE_OBLIGATION_CONFLICT",
    ],
  },
  {
    group: "Deadline Failure",
    mutations: ["REMOVE_TRACKED_DATE", "CHANGE_USER_ENTERED_DATE", "MARK_DATE_UNKNOWN", "CREATE_DATE_CONFLICT"],
  },
  {
    group: "Hearing Failure",
    mutations: [
      "REMOVE_HEARING_RESULT",
      "MARK_HEARING_UNVERIFIED",
      "CHANGE_SOURCE_STATED_HEARING_DATE",
      "REMOVE_HEARING_DOCUMENT",
    ],
  },
  {
    group: "Order Failure",
    mutations: ["SUPERSEDE_ORDER", "REMOVE_ORDER_SOURCE", "MARK_ORDER_UNVERIFIED", "CREATE_ORDER_CONFLICT"],
  },
  {
    group: "Registry Failure",
    mutations: [
      "INTRODUCE_DEFECT",
      "REMOVE_REQUIRED_DOCUMENT",
      "CREATE_METADATA_CONFLICT",
      "CREATE_MISSING_REFERENCE",
      "LEAVE_OBJECTION_UNRESOLVED",
    ],
  },
  {
    group: "Liberty / Custody Failure",
    mutations: [
      "MARK_CUSTODY_EVENT_UNVERIFIED",
      "CREATE_CUSTODY_CONFLICT",
      "REMOVE_CUSTODY_DOCUMENT",
      "REMOVE_RELEASE_EVENT_SOURCE",
    ],
  },
  {
    group: "Workflow Failure",
    mutations: ["BLOCK_ACTION", "REMOVE_ACTION_DEPENDENCY", "ACTION_FAILURE", "VERIFICATION_FAILURE", "APPROVAL_MISSING"],
  },
  {
    group: "Provenance Failure",
    mutations: ["INVALIDATE_SOURCE", "REMOVE_SOURCE_REFERENCE", "BREAK_PROVENANCE_CHAIN"],
  },
];
