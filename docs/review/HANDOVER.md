# Deelvo — Owner UX correction handover

Phase 6 remains merged but **not accepted**. Stop for actual owner/team UX review.
**No Phase 7.** Branch `review/phase-6-ux-gate`.

Application commit: `218f712e03602194ee8f3846ff94c3205d6f4e66`.
[Private NCtest review](http://nctest.tailf7eaa5.ts.net:8766/) through Tailscale.
Subsequent handover documentation does not change the tested application.

## Changes

Grouped operational sidebar, Dashboard landing, concise labels, combined **Meine
Vorgänge**, selectable daily availability and simple time controls. Public catalogue
filter areas are independent of inventory locations. Category administration and
editable resource types are discoverable. Opening/closure management has owner and
purpose filters, compact paginated tables and bounded vacation ranges.

Persons are invited without admin-chosen passwords or silent verification. The
visible Admin access combines protected administration and explicit operational
grants; ordinary staff groups are not elevated. Resource-specific agreements and
staff-issued qualifications remain distinct and are enforced at booking/checkout.
Versioned consent and qualification evidence are immutable. Account status is visible.

[Full scope and deliberate limits](UX_CORRECTION_STATUS.md), [ADR-020](../adr/020.md),
[team tasks](UX_REVIEW_PHASE_6.md), [navigation](NAVIGATION_REVIEW.md),
[terminology choices](TERMINOLOGY_REVIEW.md), [feedback](UX_FEEDBACK_TEMPLATE.md).
MyTurn was used only for operational presentation evidence; its domain assumptions
were explicitly excluded. Owner feedback and Deelvo architecture prevail.

## Verification

[CI 38884152250](https://github.com/IndieStu/Zirculeih/actions/runs/38884152250):
**219 passed**, 179.64 seconds, Docker/Linux/PostgreSQL 17. Lint, formatting, Mypy,
migrations, health/static and review seed/additive rerun all passed.
Local full regression: **219 passed**, 68.70 seconds, PostgreSQL 16.
[Machine-readable evidence](../test-results/ux-correction-ci.json),
[local JUnit](../test-results/ux-correction-local.xml), [browser evidence](VERIFICATION.md).

## Data preservation

NCtest was upgraded with additive migrations, never reset. Backup is private in
`/home/timo/deelvo-review/operator-backup/ux-correction-before/` (database, media,
environment and pre-update identity/password digest snapshot).

All 7 previous User records, 7 bookings/claims, 2 loans/3 loan lines, 16 assets,
7 resources/9 units, 12 acceptances and the existing asset-media record are retained.
Every previous password hash is unchanged. Both existing media files were compared
byte-for-byte. Three assets/resources/units, qualification/consent examples and four
fictional users were added. Other NCtest services and the private bind are unchanged.

Four new scenarios: `ux_ready`, `ux_old`, `ux_noqualification`, `ux_neither`.
**Their first usable passwords remain pending explicit owner approval.** Automatic
approval review rejected credential provisioning separately from fixture creation.
Existing six role credentials remain valid and unchanged. Credentials stay in a
separate private local file, never the repository or review ZIP.

## Review boundary

Daily occupancy is not a monthly drag planner, series engine or ICS feed. Final
booking rechecks personal eligibility and appointments. Qualification issuance is
global-only in this minimal groundwork; bundles and advanced qualification scopes
are not implemented. No actual hardware-scanner test, comprehensive WCAG audit,
production readiness or team UX acceptance is claimed.

GitHub connector still rejects draft PR creation with 403. SSH push succeeds.
[Compare branch / create PR](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-6-ux-gate?expand=1).
