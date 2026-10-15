# Codex instructions — Zirculeih

Read `PROJECT_SPEC.md` completely before any work. The specification is authoritative.

1. Work in explicit phases. **Phase 0 is documentation and architecture only.** Do not create application feature code or start Phase 1 without owner approval.
2. Keep Zirculeih a modular monolith, single organization, fully self-hosted. Never assume inventory asset = bookable resource = loan.
3. Local email/password signup must work without Authentik. OIDC is optional. Group membership and permissions are administered in the app; employee status grants nothing by itself.
4. Enforce object-level authorization in all views, APIs, exports and service methods. Use default deny and explicit, audited admin overrides.
5. Never confirm overlapping exclusive bookings. Booking writes use one service layer and transaction-safe PostgreSQL allocation; test concurrent requests.
6. Distinguish website access, pickup/return opening hours and room/machine usage hours. Store UTC instants and preserve Europe/Berlin local scheduling semantics.
7. Recurring reservations from ordinary users require approval; editor/admin groups may create/approve. All occurrences are validated; exceptions remain editable.
8. Do not add payments, billing, telemetry, mandatory cloud services, multi-tenancy or unnecessary microservices.
9. Use only reviewed open-source components compatible with intended AGPL-3.0-or-later distribution; log dependencies and SPDX licenses in `DEPENDENCIES.md`. Do not choose final project license without owner approval.
10. Every feature needs automated tests, docs, and an explicit acceptance check. Never report a test passed unless run. Never deploy or touch production without instruction.
11. Record architectural choices in `docs/adr/`. Escalate unresolved requirements that impact schema, security, booking invariants or legal compliance.
12. At end of each phase: summarize files changed, commands run, tests, open risks, and ask for approval before the next phase.

