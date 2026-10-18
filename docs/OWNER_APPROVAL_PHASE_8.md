# Phase 7 accepted; Phase 8 authorized — 2026-10-17

Owner: “Okay ist abgenommen 8 darf gestartet werden”. This accepts Phase 7 and
explicitly authorizes Phase 8 (approvals and bounded recurring reservations,
AC-10/11/23). Main de92c55 contains merged Phase 7 (PR #8). Work continues on
`phase-8-approvals-recurrence`.

Preserve the accepted resource/asset/booking/loan distinctions, booking integrity,
scoped permissions and calendar UX. Requests do not hold capacity; approval is
all-or-nothing, rechecks every occurrence and uses the existing allocator. Weekly
rules preserve local time and have a configurable initial cap of 52 occurrences.
Individual occurrence exceptions retain original identity and audit history.

Earlier Phase-8 stop statements are historical gates superseded by this approval.
Phase 9, production, credential changes and real personal data are not authorized.
