> Historical initial assignment. Phase 0 has been reviewed; [Owner review](docs/OWNER_REVIEW_PHASE_0.md) authorizes Phase 1 after documentation updates. This initial prompt does not revoke that approval.

# First Codex assignment — Phase 0 only

You are taking over the initial architecture work for **Zirculeih**, a self-hosted, open-source resource booking, lending and asset management application for the WERK / Zircula environment, designed to be reusable by other makerspaces.

Read `PROJECT_SPEC.md` and `AGENTS.md` completely before doing anything else. The product specification contains binding scope, business rules, acceptance scenarios and a phase-by-phase roadmap.

**Your assignment is PHASE 0 ONLY. Do not implement Django models, UI screens, migrations, APIs, or deployable application features.**

1. Inspect the repository and summarize existing content.
2. Create/refine `ARCHITECTURE.md`, `DATA_MODEL.md`, `BOOKING_ENGINE.md`, `PERMISSIONS.md`, `UI_UX.md`, `DEVELOPMENT_PLAN.md`, `DEPENDENCIES.md` and relevant `docs/adr/` records. If any files already exist, preserve and improve them instead of overwriting blindly.
3. Propose a modular-monolith architecture, entity relationships, booking and loan state machines, resource/pool/bundle allocation model, PostgreSQL concurrency strategy, timezone/DST handling, recurrence and approval behavior, and a fully group-configurable permission model.
4. Specify how external local signup and optional Authentik OIDC coexist without account takeover or privilege escalation.
5. Propose a responsive German-first UI and detailed booking/checkout workflows.
6. Check proposed runtime and frontend packages for OSI-approved licenses and plausible AGPL-3.0-or-later compatibility. Record exact packages/licenses to be verified, risks and alternatives. Do not claim a definitive legal opinion.
7. Turn the acceptance scenarios in the spec into a traceable test matrix. Mark what must be tested against real PostgreSQL.
8. Produce a prioritized, small-increment roadmap with phase gates, dependencies and realistic deliverables. Include initial deployment topology for Docker Compose behind an existing reverse proxy.
9. List remaining decisions as ADRs with recommendation, alternatives, tradeoffs and whether owner approval is required.
10. Summarize architecture and unresolved decisions for review, then **STOP AND WAIT FOR EXPLICIT APPROVAL** before any Phase 1 implementation.

Critical invariants: no double booking; no unauthorized access; employee marker does not confer operational permissions; booking/loan/asset are separate; external users do not require Authentik; recurring series require approval unless created by authorized editors/admins; no fees/payments in v1; no precise machine usage telemetry; inventory-only assets are supported.

Do not overengineer. Prefer simple, maintainable, well-tested architecture and concrete acceptance tests over speculative frameworks.

