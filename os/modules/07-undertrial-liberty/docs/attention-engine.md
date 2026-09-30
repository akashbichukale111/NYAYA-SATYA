# Liberty Attention Engine

`app/agents/attention.py::run_attention_engine` recomputes `AttentionItem`
rows for a case from scratch on every call (previous open auto-generated
items in each category are resolved and replaced), so the engine always
reflects current state rather than accumulating stale signals.

## Categories generated (verified against live demo data)

| Category | Generated when |
|---|---|
| `UPCOMING_SOURCE_DATE` | A hearing's source-stated date is within `UPCOMING_DATE_WINDOW_DAYS` (default 14) of today. |
| `PAST_TRACKED_DATE` | A hearing's source-stated date has passed with no recorded result. (Deliberately **not** called "LEGALLY_OVERDUE".) |
| `MISSING_HEARING_RESULT` | Same trigger as above — stated separately since it's actionable on its own. |
| `MISSING_CUSTODY_INFORMATION` | No custody events at all, or a custody event with no identifiable date. |
| `CONFLICTING_CUSTODY_INFORMATION` | An open `Conflict` record exists. |
| `UNVERIFIED_RELEASE_EVENT` | A release event's `current_status_confidence` is not `CURRENT_STATUS_VERIFIED`. |
| `UNVERIFIED_BAIL_EVENT` | A bail event's `verification_status` is not `SOURCE_FACT`. |
| `MISSING_ORDER` | A hearing has a recorded result but no linked order. |
| `STALE_CASE_STATE` | No case activity in `STALE_CASE_DAYS` (default 30). |
| `PROVENANCE_GAP` | A record has neither a source document nor a reporting user. |
| `HUMAN_REVIEW_REQUIRED` | One or more `ReviewTask` rows are `PENDING`. |
| `MISSING_DOCUMENT`, `DEPENDENCY_BLOCKED` | Reserved categories, populated via the dependency graph's `BLOCKED` status (see `app/agents/dependency.py`). |

## Severity (`SignalSeverity`)

`INFO` / `ATTENTION` / `HIGH_ATTENTION` / `REQUIRES_HUMAN_REVIEW` — an
**operational priority**, explicitly not a legal-seriousness score. There is
no "risk of illegal detention" score anywhere in the system.
