# Owner UX correction — implementation and review gate

2026-10-16. Branch `review/phase-6-ux-gate`. Phase 7 remains unauthorized.

## Delivered scope

- Grouped desktop sidebar, responsive administration navigation, operational Dashboard
  landing including staff OIDC, compact labels and contextual explanations.
- Own bookings and linked physical loan status together under **Meine Vorgänge**.
- Separate concrete Prusa catalogue entries through the existing Resource/Unit/Asset
  relationships. Identical drills remain a pool. Rooms and machines remain onsite
  bookings, never physical loans merely for presentation simplicity.
- Month-first availability with a visual day timeline and continuous start/end
  selection; day-based offerings use inclusive date ranges. Current catalogue occupancy badges. Same capacity,
  maintenance, claim buffers and custody computation as the allocator. No identities.
  The final form checks beneficiary permissions, agreements, qualifications and
  pickup/return appointments; occupancy does not confer personal eligibility.
- Date/time controls with conditional DST disambiguation, explicit skipped-time error.
- Category administration in navigation; separate editable ResourceType/Art.
  Separately authored public filter areas, no inventory-location filter enumeration.
- Organization/category/resource/location scheduling using the existing intersection
  engine. Regular weekdays, bounded vacation ranges, closure/special-day management,
  separate usage/access/staffed/pickup/return purposes and preserved booking incidents.
- Persons list/search and invitations. Verified email, own password and privacy
  acknowledgement required; no silent verification or admin-chosen passwords.
- One visible Admin composition; protected authority remains separate internally,
  operational access uses explicit grants, existing denies still apply. Only the
  designated fictional admin is elevated by the explicit review enhancement.
- Resource-context multiple versioned agreements and qualification requirements;
  current-version acceptance, immutable evidence, staff issuance, account overview.
  Binding booking and physical checkout recheck current requirements server-side.
- Explicit idempotent additive `enhance_review_ux`, with three named printers and
  four fictional requirement states. No reset, no existing password rotation.

## MyTurn evidence and constraints

Safe inspiration: grouped navigation, visible occupancy, contextual actions, concise
operational lists, reservation quick filters and discoverable category management.
Do not import: item/check-out treatment of rooms, membership types as a replacement
for scoped groups, pickup-centric fulfillment, induction consent as a substitute
for staff-issued qualifications, fragmented calendars or large vanity statistics.
The observed morning/afternoon room split was configuration evidence, not proof of
an inherent MyTurn limitation. Actual return confirmation was not observed because
there were no active loans. Owner feedback and Deelvo domain principles prevail.

## Deliberate limits for team review

The owner rejected the original free-slot-card UI. The replacement is a month
calendar, followed by a visual day timeline or an inclusive date range. Start/end
controls stay synchronized with the selected overlay. No series planner or ICS feed.
Physical appointments and personal eligibility are checked in the booking step.
Closed, blocked, occupied and transition periods are shown distinctly; invalid
starts/ends cannot be selected. Weekly opening windows
are entered by weekday; a vacation period expands into bounded date exceptions.
Existing windows are removed and recreated to change them; no bulk spreadsheet UI.
Qualification issuance is global-only in this minimal groundwork; scoped issuer
administration, bundles and series are not part of this correction.

**Artikel & Ressourcen**, **Exemplar / Platz**, and calendar density remain
explicit terminology/presentation choices for the team review, not domain changes.
No final acceptance, production readiness, hardware scanner test or full WCAG audit
is implied. Actual team feedback is the next gate.

## Calendar correction

[Binding replacement instruction](OWNER_CALENDAR_CORRECTION.md), [ADR-021](../adr/021.md).
Existing maximum duration and grid fields are reused. Room/machine transitions
default to at least 30 minutes and can be raised (e.g. 45). Current transition
constraints cover legacy and completed onsite bookings without changing immutable
claims. A deferred SQL guard protects direct and concurrent allocations.
Review additions include four bookings, a usage-category closure, CNC temporary
block and a separate fictional day-mode cargo-bike offering; existing physical
loan modes and custody records are preserved.
