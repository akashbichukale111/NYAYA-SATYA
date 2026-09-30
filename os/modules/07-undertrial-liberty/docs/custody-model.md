# Custody Model

## Event types (`CustodyEventType`)

`ARREST_RECORDED`, `CUSTODY_STARTED`, `REMAND_ORDER`, `CUSTODY_EXTENDED`,
`JUDICIAL_CUSTODY`, `POLICE_CUSTODY`, `TRANSFER`, `PRODUCTION`,
`COURT_APPEARANCE`, `RELEASE_ORDER_RECORDED`, `RELEASE_RECORDED`,
`CUSTODY_STATUS_UPDATED`, `UNKNOWN_CUSTODY_EVENT`.

An event's existence never proves *current* legal custody by itself — that
determination is left entirely to `app/agents/digital_twin.py::compute_current_custody_status`,
which only ever returns one of `CUSTODY_STATE_KNOWN_VERIFIED`,
`CUSTODY_STATE_KNOWN_UNVERIFIED`, `CUSTODY_STATE_CONFLICTING`, or
`CUSTODY_STATE_UNKNOWN` — never a legal lawfulness judgment.

## Dates

Every date-bearing field pairs with a `date_type`
(`SOURCE_EXPLICIT_DATE` / `SOURCE_RELATIVE_DATE` / `USER_ENTERED_DATE` /
`SYSTEM_DERIVED_DATE` / `UNKNOWN_DATE`). `app/agents/date_parser.py` only ever
recognizes dates that are *explicitly written* in source text (an ISO date, a
"14 October 2026"-style date, or an explicitly-stated relative phrase like
"within 10 days"). It never computes a statutory period, limitation period,
or holiday-adjusted deadline. If no such phrase is found, the date is
`UNKNOWN_DATE` and the field is left null — never guessed.

## Release events

`ReleaseRelatedEvent.current_status_confidence` is one of
`CURRENT_STATUS_VERIFIED`, `CURRENT_STATUS_UNVERIFIED`,
`CURRENT_STATUS_UNKNOWN`. A reported release is created with
`CURRENT_STATUS_UNVERIFIED` and only ever becomes `CURRENT_STATUS_VERIFIED`
through an explicit human `Verification` action
(`POST /api/cases/{case_id}/verification`) — never automatically.
