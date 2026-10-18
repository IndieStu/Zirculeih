# Owner authorization — Phase 9

Date: 18.10.2026. Owner: “starte 9”, following explicit acceptance of Phase 8.

Phase 9 notifications/calendars is authorized according to PROJECT_SPEC and
ADR-015: reliable SMTP delivery, reminders/preferences/templates, personal and
scoped operational calendars, private revocable standards-compliant ICS feeds.
Base: accepted Phase-8 branch 4694880; main remains de92c55, so no merge is assumed.
Work branch: phase-9-notifications-calendars.

Keep all accepted domain, authorization, privacy, time and booking invariants.
No production, NCtest upgrade, existing credential changes, CalDAV, Phase 10 or
real personal data are authorized. Nextcloud interoperability needs an isolated
fictional acceptance client; never silently use a production account.

## Owner clarification — Nextcloud acceptance

Owner explicitly declines setting up a Nextcloud test instance and will manually
verify the subscription later. Automated RFC/parser, update/cancellation, DST and
access/revocation tests remain in scope. Record CAL-06 as pending owner testing;
do not claim it passed and do not provision a test cloud.
