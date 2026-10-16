# Deelvo — Product & Engineering Specification

**Version:** 0.7 · **Status:** Phase 5 accepted and merged; Phase 6 merged, not accepted; owner/team UX review gate active · **Date:** 2026-10-16
**Product name:** Deelvo · **Primary language:** German (de-DE) · **Timezone:** Europe/Berlin

> This document is the authoritative product specification for Codex. Do not implement the entire product at once. First complete Phase 0, produce architecture artifacts, and request approval before writing application features. Unresolved choices must be captured as ADRs and must not be silently invented.

## 1. Mission and scope

Build a polished, accessible, self-hosted, Docker-deployable open-source resource reservation, equipment lending, and full asset-management application. Initial installation serves Zircula e.V. and the WERK cultural/makerspace in Bremerhaven, Germany, as **one platform**, not separate tenants. The design must remain reusable for other tool libraries, makerspaces, community workshops and cultural organizations. A future AGPL-3.0-or-later release must remain possible; no proprietary mandatory service or dependency.

**Core insight:** Inventory assets, bookable resources, and actual loans are different domain concepts. A room is bookable but not checked out; an impact driver is bookable and checked out; an unbookable mixing desk is inventoried only; a 3D printer is a time-bookable machine; a cargo bicycle may be booked with required accessories; multiple equivalent tools may be booked as a pool.

### 1.1 Outcomes
- Visitors discover resources with images, descriptions, category filters and search; registration is direct and simple.
- Authorized people reserve tools for dates/days, rooms for hourly slots and machines for hourly slots.
- Admins configure arbitrary groups, permissions, advance-booking windows, opening hours, pickup/return hours, resource-use hours and per-resource rules without code edits.
- Staff can manage reservations, pickup/return and bookings for others only when explicitly granted operational permissions via groups. System administrators retain protected system administration authority.
- Complete physical inventory including non-bookable assets, locations, condition, documentation, QR codes and maintenance.
- Runs independently on a VPS via Docker Compose, with local login and optional Authentik OIDC for internal people.

### 1.2 Out of scope for v1
No fees, invoices, payment gateway, deposits, fines, donation processing, procurement ERP, telemetry/precise actual machine operating time, hardware access control, mandatory SSO, multi-tenant SaaS, native mobile app, automated myTurn migration or microservices. A future optional pricing module may be considered only through explicit later design; avoid introducing fee logic into core booking calculations.

### 1.3 Product principles
1. **One installation, one organization**, but multiple locations, departments and configurable groups.
2. **Configuration over hardcoding:** never hardcode Zircula, WERK, staff group names, categories, days, times or permission horizons.
3. **Default deny** for privileged operations, restricted inventory and qualifications.
4. **Separation of concerns:** asset ≠ resource ≠ booking ≠ loan ≠ qualification ≠ group.
5. **Booking integrity first:** no confirmed double bookings, even under concurrency.
6. **Low-friction public UX:** local registration; Authentik optional for internals only.
7. **Accessible, responsive, privacy-conscious, maintainable and testable.**
8. **Fully self-hostable** with no mandatory third-party runtime APIs.

## 2. Personas and major journeys

**Guest:** browse public resources, search/filter, see descriptions and availability appropriate for anonymous users; cannot book without registration.

**Registered external user:** register by email/password, verify email, sign in, see own bookings, make permitted bookings under default restricted group/policy. Registration does not self-assign privileged groups.

**Member:** belongs to one or more admin-assigned groups, gets corresponding resource access and booking horizons (e.g. 90 days instead of 30).

**Qualified machine user:** holds a resource/category-specific qualification; can book a machine subject to other group rules.

**Booking editor / authorized employee:** group permission to create/edit/cancel bookings for others, including walk-ins, process checkouts, returns and exceptional cases within delegated scope. Being marked 'employee' alone conveys no privilege.

**System administrator:** manages groups, permission grants, integrations, critical settings and admin accounts. The application must always retain a secure recovery/bootstrap path; admins are distinct from group-granted editors.

**Inventory manager:** can inventory, label, relocate and maintain assets without automatically gaining system-wide booking or user-management powers.

### 2.1 User stories
- As a visitor I can browse without account, but only see resources marked public.
- As an external user I can book a tool within my 30-day horizon and see its pickup instructions.
- As an internal member I can reserve a meeting room 62 days ahead when my group permits 90 days.
- As a person without CNC induction I cannot reserve the CNC even if the time is free.
- As an editor I can create a reservation on behalf of another user and see an audit trail.
- As an inventory manager I can register an unbookable audio mixer and record location, serial number, attachments and condition.
- As a librarian I can scan a QR code and check out a reserved tool with required accessories.
- As a user I can request a weekly meeting-room series, which is not binding until reviewed.
- As an authorized editor I can approve the series or directly create one, with conflict reporting for every occurrence.
- As a staff member I can block a machine for repairs, preventing new reservations and flagging impacted confirmed bookings.

## 3. Domain model — authoritative boundaries

### 3.1 Identity and access
**User** (stable ID, email unique normalized, verification status, display name, local credential presence, active state, locale, consent timestamps, optional OIDC identities). **Group** (admin-defined name, description, status). **GroupMembership** (user, group, assignment history). **PermissionGrant** (group, action, scope, optional restrictions). **QualificationType**, **UserQualification** (user, type, issued (no expiry or individual revocation in the initial installation), issuer, evidence), **AuditEvent**. Use explicit system-admin status separate from employee marker; never allow public signup to assign groups or admin status.

**Physical borrowers:** registered accounts only; no BorrowerContact or accountless lending. Full borrower profile before binding physical-loan reservation; ID checked at first checkout without storing document data. See owner review.

### 3.2 Inventory
**Asset** represents a physical identifiable item: UUID, human inventory ID, title, description, category, tags, maker/model, serial number, acquisition date/value (optional and restricted), condition, lifecycle state, primary location, custodian, images, attachments, maintenance notes, custom field values. Inventory-only assets need no resource record.

**AssetType / AssetTemplate** can define common attributes. **CustomFieldDefinition** supports typed text, number, date, boolean, enum, URL and validation; values searchable/filterable where practical. Do not store all critical core fields in unvalidated JSON.

**Location** tree: organization → building → floor → room → storage location; arbitrary depth, stable IDs, move history; prevent cycles. A room may be both a location and a bookable resource, linked explicitly rather than conflated.

**AssetRelation** supports part-of, accessory-of, replacement-for and kit membership; enforce acyclic relations where appropriate. Track each physical item separately. **AssetEvent** tracks moves, state changes, inspections and disposals.

### 3.3 Resources
**Resource** is an offering that can be booked: title, slug, type (item / room / machine / vehicle / logical capacity / other), description, cover/gallery, visibility, booking-enabled state, location, linked asset(s), booking policy, availability schedule, qualifications, approval mode, tags and categories. Types are configurable in presentation and rules, not implemented as separate unrelated booking engines.

**ResourceUnit** represents a concrete capacity slot or physical unit; for identical drills allow pool booking (auto-assign unit) or selection of a named unit. For non-physical rooms a unit may be logical. **ResourcePool** groups equivalent units; capacity derives from eligible unblocked units, not a single editable counter disconnected from inventory. **ResourceBundle** declares required/optional components; all required components must be atomically available/allocated. Avoid circular bundles.

**Category** hierarchy and many-to-many resource associations; **Tag** for cross-category labels. Separate public visibility from permission to reserve and from internal inventory visibility.

### 3.4 Availability and policy
**AvailabilitySchedule** weekly recurring time windows; **ScheduleException** holidays, closures, temporary special hours. Maintain distinct schedules for (a) public opening, (b) checkout/pickup/return windows, (c) actual room/machine usage windows. **ResourceBlock** maintenance, administrative hold, outage or private event. **BookingPolicy** minimum/maximum duration, granularity, maximum future horizon, maximum concurrent bookings, lead time, buffer, allowed days/times, cancellation window, approval mode, pickup requirement, group overrides and qualification requirements.

Use a deterministic **PolicyResolver** with explicit precedence and explainable output. Proposed default: explicit security/resource denial wins; group grants union for eligibility; most permissive applicable horizon may apply unless overridden by a restrictive resource rule; qualifications are additional mandatory conditions; administrator override requires separate permission and reason, cannot silently bypass technical conflicts. Document exact policy algebra in an ADR and tests before implementation.

### 3.5 Reservations and loans
**Booking**: immutable identity, creator, beneficiary, resource, allocated unit(s), requested interval, status, approval actor/reason, timestamps, policy snapshot/reference, source, recurrence membership. **BookingAllocation** explicitly claims one or more exclusive units / room / machine / bundle components for a time interval. **Loan**: registered borrower, issue/expected-return/actual-return, checkout/return actor, condition and accessory checklist, overdue status. **LoanBooking** preserves links to one or more original bookings; **LoanLine** binds each physical asset and its booking/allocation, with independent return status. Spontaneous checkout creates Booking/Allocation and Loan atomically; reservation pickup reuses the existing Booking (owner addition 2026-10-15). **RecurrenceSeries** contains rule, timezone, start/end or count, approval state; occurrences are first-class bookings linked to series. **BookingEvent / LoanEvent** capture audit transitions.

A room or machine normally uses booking lifecycle only. A physical lendable item uses booking and loan lifecycles. Inventory-only assets use neither. Do not derive checkout status solely from reservation start time.

## 4. Booking engine — non-negotiable design

### 4.1 Time semantics
- Store timestamps as timezone-aware UTC instants; display and evaluate local rules in configurable `Europe/Berlin` by default. Date-only lending intervals require explicit local-day semantics; never model all-day borrowing as an accidental 24-hour timestamp assumption.
- Use half-open time intervals `[start, end)` so adjacent bookings do not conflict unless a buffer applies.
- Model resource-use time separately from physical pickup/return appointment times.
- Validate DST skipped and repeated wall-clock times; recurrence expansion preserves intended local time and has documented DST behavior.
- Opening hours do **not** restrict when a user may click Book; they restrict only relevant use/pickup windows.
- Availability search and final confirmation use the same authoritative server-side rules.

### 4.2 Booking modes
**Date-based lending:** calendar dates, multi-day periods, configurable earliest pickup and expected return; holidays and non-working pickup days may require alternate appointments. **Slot booking:** configurable 15/30/60-minute granularity, minimum/maximum duration and buffers. **Flexible hours:** resource may permit longer continuous periods, not forced to hourly-only. **Admin request mode:** no auto-confirmation; **auto-confirm mode:** immediately confirm if policy and capacity pass. **Pool:** allocate a specific available unit at confirmation or use a documented later allocation policy that still reserves capacity safely. **Bundle:** atomic reservation of required linked components.

### 4.3 State machines
Booking: `draft`, `requested`, `confirmed`, `active`, `completed`, `cancelled`, `rejected`, `no_show`. A new auto-confirmed room booking may start at `confirmed`; state transitions must be explicit and validated. A booking in `requested` does not necessarily hold inventory: make hold policy configurable and documented, with default non-blocking request unless a defined temporary hold is created. Confirmed/active allocations block overlapping bookings. Cancelled/rejected/completed allocations release future capacity as appropriate, but a still checked-out item must remain unavailable until physically returned.

Loan: `reserved`, `ready_for_pickup`, `checked_out`, `returned`, `overdue`, `lost`, `damaged` (consider separating terminal condition flags from workflow state in Phase 0). Overdue is derived from due time and active checkout, not just a manually writable status. A loan may extend beyond its booking; actual checkout forbids a second physical checkout until returned. Future reservations after expected return are allowed if reservation intervals do not overlap. Overdue custody flags existing following bookings for explicit staff resolution.

### 4.4 Recurrences
Ordinary users may **request** recurrence; every occurrence must be checked and the whole series requires manual approval. Authorized editors/admins may directly create/approve series. Prevent unlimited horizon, require end date or count and cap occurrences. Show all conflicts and choose an explicit all-or-nothing default on approval; no silent partial approval. Support exceptions: edit/cancel one occurrence, edit this-and-following if feasible, or whole series; preserve audit history. Approval must recheck availability transactionally. A requested series must not silently reserve time without a documented hold policy.

### 4.5 Concurrency and database enforcement
- Use PostgreSQL transactions, row/advisory locks as appropriate and **database-level exclusion constraints** for exclusive time intervals where practical. For pooled capacity and bundles use an atomic allocation strategy with locking and retry behavior. A simple `SELECT then INSERT` without locking is unacceptable.
- All booking writes and changes (including admin actions, approvals, extensions and maintenance blocks) call the same domain service; UI and API may not bypass it.
- Idempotency keys for repeated submissions and retries; duplicate browser submissions cannot create duplicate bookings.
- Prevent races between checkout, cancellation, maintenance, pool allocation and booking approval.
- Database constraints protect invariant states; application validation gives friendly explanations.
- Integration tests must issue simultaneous booking requests against real PostgreSQL and assert one winner when only one unit is available.

### 4.6 Availability result
Return structured availability with reasons: `available`, `outside_usage_hours`, `outside_booking_horizon`, `qualification_required`, `permission_denied`, `maintenance`, `reserved`, `pickup_unavailable`, `approval_required`, `capacity_exhausted`. Avoid leaking restricted resource details to unauthorized people. Include next available times only when computationally bounded and permitted.

## 5. Permissions and registration

### 5.1 Authentication
- Public local signup: email, password, email verification, privacy notice; password reset; rate limiting and anti-abuse measures; no required smartphone/MFA for public users.
- New registrations receive only a safe configurable baseline access policy/group, never privileged memberships. Admins assign additional groups. Unverified accounts cannot book.
- Optional Authentik OIDC for internal users/employees; local login always remains available. Link identities safely by explicit verified flow, never blindly merge accounts based on unverified email. Prevent OIDC callback privilege escalation.
- Session security, CSRF, secure cookies, password hashing, brute-force protections, logout and session invalidation.

### 5.2 Authorization
Define action-level permissions, e.g. `catalog.view_private`, `booking.create_own`, `booking.request_recurrence`, `booking.create_for_others`, `booking.override_policy`, `booking.approve`, `booking.manage_all`, `loan.checkout`, `loan.return`, `asset.read`, `asset.manage`, `resource.manage`, `qualification.issue`, `user.manage_groups`, `permissions.manage`, `system.configure`. Grants may scope to categories, resources and locations. Permission checks must apply server-side to list/detail/export/API and mutation paths; object-level authorization is mandatory.

**Employees do not get privileges merely from employee status.** Only system admins have protected system authority; operational staff are group-authorized editors. An admin can configure groups and grants. A non-admin with group-management permission must not grant itself administrator privileges or grant permissions above its delegated authority.

### 5.3 Effective policy examples
- External user: example 30-day advance horizon; member: example 90 days. Both are admin-editable examples, not defaults hardcoded in business logic.
- Multiple groups: deterministic conflict policy; explicit denies and mandatory qualifications prevail. Group changes affect future booking attempts immediately; decide treatment of existing confirmed bookings in ADR.
- Authorized editor can book on behalf of someone else, but the beneficiary and actor are both recorded. Whether editor overrides beneficiary eligibility must be a separate permission and always audited.

## 6. Catalog, user experience and content

### 6.1 Public pages
Home with hero/search, featured categories and featured resources; catalog grid/list with images, availability badges, categories, tags, resource type, location and filters; search by name, description, maker/model and public custom attributes. Resource detail includes rich formatted description, safety instructions, specs, gallery, included accessories, location/pickup guidance, usage terms, calendar and clear booking CTA. Anonymous visitors see public details but must log in to book.

### 6.2 Booking flow
Select dates/time → see live eligibility and availability → optional unit/accessories → review terms and pickup/return information → submit → immediate confirmation or approval pending → manage from My Bookings. Show friendly validation and timezone. Do not falsely promise an available slot before transaction commits. Support cancellations and permitted extensions.

### 6.3 User account
Profile, verified email, own bookings (upcoming/past/requested), loans and due dates, cancellation, recurrence requests, relevant unexpired-by-design qualifications, notifications preferences, personal data export/deletion request. Never expose other users' personal data.

### 6.4 Administrative UX
Separate admin navigation: Dashboard, Calendar, Bookings, Checkout/Returns, Resources, Assets, Locations, Categories, Users, Groups/Permissions, Qualifications, Maintenance, Reports, Settings. Admin calendar filters by type/location/resource; rapid actions; mobile QR scan via camera where supported with manual fallback; batch edits and CSV import/export; clear audit history. Include accessible keyboard interactions, contrast, focus indicators, descriptive errors and empty states. German first, translation-ready (English later). Avoid an IT-only look: imagery and friendly language suit a makerspace.

## 7. Inventory, maintenance and lifecycle

### 7.1 Inventory data
Create/update/archive physical assets independently of resource publishing. Unique human-readable inventory codes (configurable prefix/sequence), QR printable labels linking to authorized asset views, condition ratings, category and tags, serial number, purchase/warranty metadata, images and attachments, custodian, precise location, custom fields, notes, history and disposal state. Asset visibility and sensitive purchase data have separate permissions.

### 7.2 Locations and moves
Hierarchical organization/building/floor/room/shelf with breadcrumbs, inventory counts and history; prevent deleting locations with active children/assets without an explicit migration plan. A bookable room can link to the matching location.

### 7.3 Maintenance
Maintenance record (type, description, reported by, assignee, due date, resolution, attachments), manual or scheduled recurring inspection, status `available / maintenance / damaged / retired`, automatic booking block when unavailable. Staff are warned about already confirmed bookings affected by downtime and must resolve them. No machine telemetry required; optional manually recorded usage/maintenance notes are sufficient.

### 7.4 Kits and accessories
Track individual assets within kits; required and optional components; checkout/return checklist; partial damage/missing accessories; capacity/availability must include required components. Example: cargo bike + battery + charger + lock. Never silently allow a required component to be booked twice.

### 7.5 Inventory operations
Search/filter by condition, category, location, availability, last inspection; CSV import with preview, mapping and validation; CSV export; inventory audit/count process and discrepancy log. Bulk actions require permission and audit.

## 8. Loan workflows

- A confirmed reservation may require scheduled pickup; pickup/return windows are configured separately from room/machine use windows.
- Checkout: verify actor authorization, beneficiary identity according to policy, reservation, physical unit, included accessories, condition, expected return; mark actual custody and lock availability.
- Return: scan/select asset, verify returned components, condition, damage, time; close loan and release custody; if damaged, create maintenance block.
- Extensions: check future capacity and policies before confirmation; staff override requires explicit permission, reason and conflict visibility.
- Overdue: background task derives overdue, sends configurable reminders, displays dashboard queue; do not automatically mark returned.
- Spontaneous checkout without prior online booking is required in the scanner-supported loan phase: registered beneficiary and all ordinary rules; Booking/Allocation and Loan created atomically at explicit confirmation. No accountless lending.
- No-show: staff-marked or policy-driven after grace period; release reserved capacity and audit.
- Provide receipt/summary page; PDF printout optional later. Digital signature is not required in v1.

## 9. Notifications, calendars and reporting

**Email:** verify address, reset password, booking confirmed/requested/approved/rejected/cancelled, pickup reminder, return reminder, overdue notice, maintenance impact, qualification issuance if configured (no qualification expiry in the initial installation). Template editing/localization, delivery retries and logs, user opt-out only for non-essential messages; SMTP configured by environment. Avoid sensitive details in public email subject lines.

**Calendars:** personal booking calendar, admin resource calendar, optional private iCal feed with revocable token and minimal data; public calendar never reveals borrower identities. Recurrences rendered accurately. Later CalDAV/Nextcloud integration only after separate design.

**Reports:** current loans, overdue, asset count by location/category, booking volumes, utilization of rooms/machines, maintenance backlog. Avoid unnecessary person-level profiling. Export filtered data under authorization.

## 10. Proposed technical architecture (to validate in Phase 0)

- **Backend:** supported stable Django release + PostgreSQL; Django REST Framework for explicitly needed API surfaces; Python type hints and service-layer domain logic.
- **Frontend:** Django templates + HTMX and narrowly scoped Alpine.js/vanilla JS; Tailwind CSS with reproducible local build; accessible calendar library only after license review. Prefer a modular monolith, not a SPA by default.
- **Jobs:** initially database/management-command or Celery + Redis if actual async delivery, retries and scheduled tasks justify it; keep workers optional until needed.
- **Auth:** Django local auth plus optional OIDC via a vetted open-source package; Authentik is optional external identity provider.
- **Media:** local persistent Docker volume, safe upload validation, later S3-compatible storage optional, never mandatory.
- **Deployment:** Docker Compose app + PostgreSQL (+ worker/Redis if necessary), reverse-proxy-compatible (Caddy on VPS), environment-driven configuration, health checks, named volumes, migration commands, least-privilege container user, sensible memory footprint.
- **API:** stable versioned REST endpoints for catalog, availability, bookings and authorized administration; generate OpenAPI schema if API is exposed. Web forms and API must call the same domain services.
- **Observability:** structured logs, request IDs, health/readiness endpoints, audit events, non-sensitive error reporting, optional Prometheus later.
- **Security:** no public Django admin by default without access controls; secrets never in repository; CSRF, XSS, SSRF, upload validation, object-level permissions, rate limiting, dependency scanning, secure headers, backups.

### 10.1 Repository layout proposal
```
README.md
AGENTS.md
PROJECT_SPEC.md
ARCHITECTURE.md
DATA_MODEL.md
BOOKING_ENGINE.md
PERMISSIONS.md
UI_UX.md
DEVELOPMENT_PLAN.md
DEPENDENCIES.md
LICENSE_DECISION.md
SECURITY.md
CONTRIBUTING.md
CHANGELOG.md
docs/adr/
backend/config/
backend/apps/accounts/
backend/apps/inventory/
backend/apps/resources/
backend/apps/bookings/
backend/apps/loans/
backend/apps/qualifications/
backend/apps/notifications/
backend/apps/audit/
backend/apps/reporting/
frontend/ (only if separate asset build needed)
tests/
deploy/
.github/workflows/
```

Keep modules cohesive and avoid cyclic dependencies. Domain services, not view code or model signals, own complex workflows. Avoid speculative abstraction, generic workflow engines, unneeded plugin systems and microservices.

## 11. Privacy, security, licensing

### 11.1 Data protection
GDPR-aware data minimization; privacy notice and purpose limitation; user self-service access to their information; configurable retention for closed loans and booking records; deletion/anonymization workflow that preserves non-identifying asset history and audit integrity as legally appropriate. Document retention defaults for review, do not invent legal retention requirements. Restrict exports, log access to sensitive data where needed, and prevent public disclosure of borrower identity. Backups must be encrypted at rest where operationally feasible and retention documented.

### 11.2 Open-source dependency policy
- Every mandatory component must be open source under an OSI-approved license and legally compatible with intended AGPL-3.0-or-later distribution and deployment. MIT/BSD/Apache-2.0 may be suitable; verify exact version and conditions. GPL-only libraries, copyleft combinations, AGPL-3.0-only packages and unusual exceptions require specific legal review, not automatic approval.
- Maintain `DEPENDENCIES.md` with component, version, source, SPDX identifier, use, compatibility rationale, notices and risk; lock versions and use automated vulnerability and license checks. Generate an SBOM before release.
- Do not copy code or assets from reference projects without license, attribution and compatibility verification. Reference project ideas do not imply code reuse permission.
- The project license remains undecided until owner approval; do not insert a definitive LICENSE or falsely claim AGPL licensing. Record target compatibility and a release decision gate.
- No mandatory Google, Stripe, proprietary SaaS, hosted analytics, proprietary fonts/icons or CDN runtime dependencies. Bundle legally usable assets locally.

### 11.3 Security gates
Threat-model registration, password reset, OIDC linking, privileged group edits, object authorization, booking concurrency, uploaded media, CSV injection, calendar token leakage, email enumeration and administrative overrides. CI checks for tests, lint, type check, dependencies, secret scanning and container security where feasible. Require backups and a tested restore before production.

## 12. Acceptance scenarios — executable specifications

**AC-01 Public discovery:** anonymous visitor can search public tools/rooms, filter categories and view photos; private inventory not leaked via search or API.

**AC-02 Signup:** external person registers and verifies email; only baseline access granted; cannot add self to internal group.

**AC-03 Different horizons:** same room on day +62: member group with 90-day horizon can reserve, external with 30-day horizon cannot; values configurable.

**AC-04 Room instant booking:** free meeting room Thursday 15:00–17:00 within permitted use hours confirms immediately, no checkout required.

**AC-05 Machine qualification:** user without CNC induction is denied despite free slot; qualified user succeeds.

**AC-06 Tool loan:** drill reserved for multiple days; staff scans actual unit and records checkout; actual return closes loan; mere end of reservation does not imply return.

**AC-07 Pool:** 5 identical drills allow 5 overlapping bookings, not 6; unit selection or automatic allocation supported.

**AC-08 Bundle:** cargo bike booking atomically reserves required battery, charger and lock; unavailable required accessory blocks confirmation.

**AC-09 Concurrency:** 20 simultaneous requests for one room/slot produce exactly one confirmed allocation; others get safe conflict response.

**AC-10 Recurrent approval:** regular user requests Wednesday 18:00–20:00 weekly for 8 weeks; no binding series until editor approval; approval checks all 8 occurrences; single occurrence can later be cancelled.

**AC-11 Staff permissions:** employee marker alone cannot book for others; explicit group grant allows it and logs actor and beneficiary.

**AC-12 Schedules:** booking website accessible 24/7; external pickup offered only in pickup windows; room usage limited to its own use schedule; closure exception enforced.

**AC-13 Inventory-only:** mixing desk recorded with serial number, location, photo, warranty and maintenance but not shown in public booking catalog.

**AC-14 Maintenance:** printer blocked for maintenance cannot be newly booked; existing impacted reservations flagged for review.

**AC-15 OIDC optional:** external local account works when Authentik is unavailable; internal OIDC account may log in when configured; no unsafe auto-merge.

**AC-16 Authorization:** external user cannot read/edit another user's booking or private asset via URL, API or export.

**AC-17 Timezone:** DST transition and adjacent intervals behave deterministically; no duplicate or phantom reservations.

**AC-18 Data recovery:** clean deployment + documented restore yields consistent DB, images and attachments.

**AC-19 Mobile:** registration, booking, QR lookup and return usable on small screens with keyboard and accessible labels.

**AC-20 License:** production dependencies have documented license review; no proprietary mandatory components.

**AC-21 Idempotency:** double-click/retry on booking confirmation creates one booking.

**AC-22 Permission changes:** account suspension prevents new bookings and checkouts; existing loans remain returnable and traceable. Qualifications neither expire nor get individually revoked in the initial installation (OD-07).

**AC-23 Series conflicts:** one conflicting occurrence blocks all-or-nothing series approval and displays conflicting dates; no partial hidden series.

**AC-24 Date-only loans:** borrowing across a daylight-saving transition does not accidentally change calendar-day count.

## 13. Development phases and gates

**Phase 0 — Analysis / architecture (NO application features).** Deliver domain glossary, data model/ERD, booking state machines, policy resolution ADR, concurrency/locking ADR, timezone ADR, local+OIDC account-linking ADR, license shortlist, security threat model, component boundaries, prioritized backlog, acceptance-test mapping, realistic Docker footprint, UX wireframes and identified decisions. Write `ARCHITECTURE.md`, `DATA_MODEL.md`, `BOOKING_ENGINE.md`, `PERMISSIONS.md`, `UI_UX.md`, `DEVELOPMENT_PLAN.md`, `DEPENDENCIES.md`, `docs/adr/*`. STOP and request owner approval.

**Phase 1 — Foundation.** Initialize Django/PostgreSQL Docker Compose, settings, health checks, structured logs, migrations, CI, pytest, lint/type checks, basic layouts and demo fixtures. Done: fresh clone boots with documented commands, tests pass, no hardcoded secrets.

**Phase 2 — Accounts & groups.** Local signup/verification/reset, group CRUD, safe baseline group, action-level permission infrastructure, optional OIDC behind feature flag. Done: tests cover privilege escalation and group membership.

**Phase 3 — Asset and location registry.** Asset CRUD, category/tag/location tree, custom fields, images/attachments, visibility, lifecycle and CSV import/export. Done: inventory-only assets work without resources.

**Phase 4 — Resources and public catalog.** Resource/unit/pool models, category search, public detail, galleries, resource publishing, responsive design. Done: restricted resources hidden, inventory/resource separation maintained.

**Phase 5 — Booking engine core.** Schedules, exceptions, policy resolver, date/slot booking, exclusive allocation, concurrency locks, own bookings, cancellations, state machine. Done: AC-03/04/09/12/17/21 passing against PostgreSQL.

**Phase 6 — Physical loans.** Pickup/return appointment rules, checkout/return, due/overdue, staff actions, condition and accessories, extension. Done: booking vs loan lifecycle proven.

**Phase 7 — Machine qualifications, advanced pools/bundles.** Qualification checks, granular scope, pools, selected units, atomic bundles, maintenance blocks. Done: AC-05/07/08/14.

**Phase 8 — Approval and recurring reservations.** Request/approval flows, editor grants, bounded recurrence, conflict preview, occurrence exceptions, audit. Done: AC-10/11/23.

**Phase 9 — Notifications and calendars.** SMTP, queue/retries if necessary, reminders, calendar views, safe iCal. Done: notifications idempotent and private.

**Phase 10 — Full asset operations.** QR labels, mobile scan, moves, inventory count, maintenance workflows, bulk actions, advanced reporting. Done: complete asset history and permission tests.

**Phase 11 — API and integration hardening.** Versioned API, OpenAPI, Authentik polish, import/export, optional Nextcloud interoperability design (no mandatory integration). Done: documented auth, rate limits, object-level access.

**Phase 12 — Production readiness.** Threat review, accessibility testing, load/concurrency tests, backup/restore drill, upgrade/rollback procedures, observability, translations, dependency/SBOM review, operator handbook. Done: staging acceptance checklist signed off.

**Phase 13 — WERK pilot and release preparation.** Seed real categories and resources manually; small internal pilot; collect defects, stabilize UX, freeze release; license owner decision and public open-source release checklist. No myTurn migration required.

### 13.1 Every phase must deliver
- A scoped implementation plan and explicitly excluded items.
- Updated documentation and ADRs for any architectural change.
- Unit, integration and security/permission tests relevant to the phase.
- A migration strategy if schema changes.
- Manual acceptance steps and screenshots when UI changes.
- A summary of changed files, commands run, test results, risks and remaining issues.
- A human approval gate before starting the next phase.

## 14. Non-functional targets

- Works on a modest VPS with configurable resource limits; benchmark before promising exact hardware requirements.
- Typical catalog searches and booking interactions should feel responsive on mobile; set measured latency budgets after Phase 0 profiling rather than inventing guarantees.
- Responsive at ~320px+; WCAG 2.2 AA target; German first; translation-ready.
- Database integrity prioritized over availability of nonessential notifications; email failure must not roll back successful booking.
- No silent data loss; migration and backup/restore documented and tested.
- Clear user-facing conflict and permission messages without leaking internal details.
- All critical configuration adjustable in admin UI, with deployment secrets kept in environment/secret storage.

## 15. Open decisions for Phase 0 (not permission to stall)

1. Exact priority of conflicting group rules, explicit deny and resource override.
2. Whether requests temporarily hold inventory, and for how long.
3. Handling already-confirmed bookings after permission/qualification revocation.
4. Whether walk-in borrowers without account are in first release or subsequent phase.
5. Whether date-based borrowing uses inclusive displayed dates with exclusive internal end boundary; choose and test.
6. Whether automatic pool assignment occurs at booking or checkout, and impact on capacity.
7. Whether recurring series approval is all-or-nothing (recommended) and how exceptions are represented.
8. Whether a user can reserve a machine outside staffed hours if access is otherwise allowed.
9. How room use restrictions interact with building closures and category-specific overrides.
10. What data is legally required for loans and how long it may be retained; owner/privacy review.
11. Which calendar UI library and OIDC package are compatible with target license.
12. Which inventory data is public versus internal, including asset serial numbers and costs.
13. How administrative emergency overrides work without permitting overlapping exclusive allocations.
14. Resource-specific capacity and optional setup/cleanup buffers.
15. Initial branding/domain, email sender, production reverse-proxy settings and backup destination.

For each decision: propose a sensible default, state alternatives/tradeoffs, record in an ADR, and seek owner sign-off before implementation if the decision affects schema, security or booking invariants.

## 16. Codex operating instructions

You are the principal software architect and implementation agent for **Deelvo**. Read this entire specification before taking action. Treat requirements marked non-negotiable as binding. Never invent business requirements, never bypass authorization or booking invariants for speed, never introduce a proprietary dependency, and never start Phase 1 before Phase 0 approval.

**First response in a new repository:** inspect the repository; summarize your understanding, propose Phase 0 deliverables and file tree, list only decisions that block architectural correctness, then create documentation/ADRs only. Do not scaffold Django or write production feature code in Phase 0. You may create architecture diagrams and test plans. Present the architecture review to the owner and STOP.

**For approved later phases:** work in small reviewable changes; state scope and plan; implement domain services and tests before polishing UI; verify with actual commands; do not claim tests passed unless executed; update docs; create concise commit/PR summaries; never force-push or deploy to production without explicit instruction. Preserve existing data and migrations; never modify production databases directly. If you discover a conflict between requirements, record it and ask for resolution rather than silently picking one.

**Definition of done:** implementation and automated tests complete; authorization/security implications tested; acceptance criteria met and relevant concurrency tests pass; no unreviewed dependency; relevant user/admin handbook updated; API documentation updated for externally exposed capabilities; architecture/ADRs updated for architectural changes; migration/rollback documented; reviewer approval obtained. Applies to Phase 3 and all later phases.

---

## 17. Inspiration (feature research, not code dependency)

- leihs: inventory, reservations, handover; https://github.com/leihs/leihs
- Circulate: lending, holds, renewal and pickup appointments; https://github.com/chicago-tool-library/circulate
- Shelf: QR asset tags, kits, custom fields and hierarchical locations; https://github.com/Shelf-nu/shelf.nu
- SpaceWorks: makerspace-oriented inventory/booking; https://github.com/SpaceWorks-HQ/SpaceWorks
- Rapla: resource scheduling, repeat bookings and fine-grained permissions; https://rapla.org/

Research sources must not be copied into Deelvo without independent license and attribution review. This specification records requirements, not legal approval to reuse source code.



## 18. Owner clarification — 2026-10-14

The confirmed requirements in [docs/OWNER_DECISIONS.md](docs/OWNER_DECISIONS.md) supersede conflicting earlier draft options:

- All physical loans require a registered borrower with full name, postal address, email and phone number. BorrowerContact/accountless lending is excluded.
- Staff inspect identity documentation at the first checkout. Store checker and timestamp, not identity-document number or copy.
- The borrower must declare existing liability insurance.
- Administrators author general lending and additional item-specific agreements in the app. Multiple agreements can apply to one item; acceptance is once per immutable published version, with renewed acceptance after a version change.
- Qualifications in the initial installation neither expire nor get individually revoked. Account suspension is the operational restriction. AC-22 is replaced accordingly: a suspended account cannot create bookings or receive new checkouts; existing loans remain returnable and traceable.
- Scoped group configuration permits resource use outside staffed opening hours. Resource usage windows, hard closures and pickup/return windows remain distinct.

Implementation recommendations and remaining review gates are in docs/adr/. These owner clarifications do not authorize Phase 1 before Phase 0 review approval.


## 19. Binding Phase-0 review and Phase-1 approval — 2026-10-14

[Original owner review](docs/OWNER_REVIEW_PHASE_0.md) supersedes contrary draft recommendations. All ADR-001–010 accepted with the amendments recorded therein. Future reservations during open custody are allowed after expected return with no overlapping reservation claims; physical double checkout remains forbidden. Insurance declaration is accepted once per required text version, initially without expiry; optional future time validity. Signup only email/password; full borrower profile before binding physical-loan reservation, not ordinary room/machine slots. Series default 52 is configurable. Phase 1 technical foundation and real PostgreSQL concurrency prototype authorized after documentation update; no production deployment, real personal data, full domain implementation or automatic Phase 2.

## 20. Binding owner addition: Kiosk, scanner and inventory workflows — 2026-10-15

[Full original owner requirement](docs/OWNER_REQUIREMENT_KIOSK.md), [workflow architecture](docs/KIOSK_SCANNER.md), [ADR-011](docs/adr/011.md), and KIOSK-AC-01–22 in [acceptance matrix](docs/ACCEPTANCE_MATRIX.md) form the traceable extension. Earlier owner decisions remain binding.

- Scanner identification is read-only and workflow-independent. Assets remain identifiable without a Resource, Booking or Loan. Multiple opaque or validated legacy identifiers can resolve to one Asset or relevant Unit; internal UUID and visible code remain separate.
- HID-keyboard USB/Bluetooth scanners with Enter and manual entry are the first supported input path, without a proprietary SDK. Camera recognition and offline inventory are later optional designs.
- Staffed checkout, reservation pickup, spontaneous loans, returns/partial returns, inventory and lookup use the same centralized authorization and domain services as web/API/admin. Actor, Beneficiary, Device and Mode are distinct. No Kiosk permission bypass or unreviewed Self-Service authentication.
- Scans prepare checkout/return. A deliberate final confirmation triggers transactional writes, with current profile, agreements, insurance, first identity check, qualifications, schedules, policy and custody validation. Multiple scanned objects can belong to one Loan with independent LoanLines and preserved links to multiple original Bookings.
- Spontaneous loans require a registered account and create Booking/Allocation plus Loan atomically; existing reservations are reused. Actual custody and future reservation rules from the prior owner review remain unchanged.
- Inventory Runs have a defined scope, expected set, location observations, actor/time and reports. Duplicate and unknown scans have clear feedback. Inventory-only assets participate. Scanning never silently changes master-data location; discrepancies need explicit authorized resolution. Actual loan status is considered, so legitimately borrowed assets are not automatically treated as missing.
- Public/shared kiosks minimize displayed personal data and reset transaction context; future Self-Service needs server-side session reset, inactivity timeout and protection against previous-user data. No offline booking/checkout/return writes or blind later replay.
- Phase 1: architecture/identifier boundaries and PostgreSQL constraints documented, no full kiosk UI or domain migrations. Phase 3 implements identifier model/manual lookup; Phase 6 adds HID-supported loan workflows; Phase 10 implements scanner inventory and a separately gated kiosk UI increment before pilot. Self-Service activation requires later explicit authentication/privacy decision.

The new scenarios are planned, not implemented or passed. Phase-1 Docker/PostgreSQL-17 and GitHub-CI verification subsequently passed on 2026-10-15 (see docs/PHASE_1_REVIEW.md); this owner addition does not authorize Phase 2.

## 21. Binding Phase-2 approval, staff OIDC and Deelvo branding — 2026-10-15

Owner explicitly approved Phase 2 after Phase-1 merge. Authentik/OIDC is a required staff comfort-login feature in Phase 2, not a deferred optional implementation. Normal users register locally. Deployment activation requires configured provider credentials/endpoints; local login remains independent. No external group/admin claim import or automatic email linking. [Implementation decision](docs/adr/012.md).

Product name Deelvo; new technical identifiers use deelvo where appropriate. Superseded working names remain only in historical sources/ADRs and existing repository/data identifiers whose migration is separate. Inter, self-hosted under SIL OFL 1.1, weights 400/500/600/700. Brand palette: Blue #5590BF (primary), Orange #F79007 (deliberate accent), Ink #11140F, Charcoal #272B24, Graphite #43483E, Muted #74786F, Line #D9D9CE, Warm Paper #F6F3E9, White #FFFFFF. WCAG 2.2 AA takes precedence; darker accessible variants allowed. No approved logo mark: only plain Deelvo text in Ink on light surfaces or white/light neutral on dark. Centralized brand tokens, no external font runtime dependency. [Binding branding decision](docs/adr/013.md).

Phase 3 was subsequently authorized by the owner; see section 22. No production deployment is authorized.

## 22. Binding Phase-3 approval and additional requirements — 2026-10-15

[Phase-3 approval](docs/OWNER_APPROVAL_PHASE_3.md) accepts merged Phase 2 and authorizes the inventory foundation. [Additional owner requirements](docs/OWNER_ADDITION_DASHBOARD_API_HANDBOOK.md) are binding. Phase 3 preserves Asset ≠ Resource ≠ ResourceUnit, implements arbitrary location/category trees, permanent asset identity, namespaced aliases and read-only HID/manual lookup. Typed custom fields, restrained local media and preview/commit CSV belong to this phase. Productive resources, bookings, loans, inventory runs, full kiosk and camera scanning remain outside it. [ADR-014](docs/adr/014.md) documents concrete identity/integrity decisions.

The operational dashboard prioritizes real actionable information and permitted quick actions before counts. Phase 3 uses asset condition/lifecycle and location information only, filtered by current scopes. No fake pickups, returns, approvals, timelines or maintenance schedules. Non-operational users use their personal account area. Later phases extend attention queues and a cross-resource Today view as those domains become productive. Initial qualifications remain non-expiring: the dashboard example of expiring qualifications does not override OD-07.

The integration API uses explicit `/api/v1/` contracts, shared domain services and existing authorization. API tokens are scoped and revocable, stored hashed and bounded by the current owner's/client's rights; no global permanent key or raw model CRUD authorization bypass. Authentication, pagination, filters, errors, timestamps and rate limits are documented in [integration architecture](docs/INTEGRATIONS.md). Productive API/OpenAPI implementation is Phase 11; no API dependency is introduced in Phase 3.

Phase 9 delivers standards-compliant subscribable ICS after Booking exists: stable event UIDs, update/cancellation semantics, IANA timezone/DST correctness, privacy-aware minimal content and revocable hashed private feed credentials. Nextcloud Calendar is an acceptance client for one-way subscription, not a proprietary runtime dependency. No fake feeds or CalDAV in Phase 3. CAL acceptance scenarios remain planned until implementation.

The living [handbook](docs/handbook/README.md) is a first-class deliverable, separate from architecture, integration and deployment documents. Phase 2 account/group functionality and implemented Phase 3 operations must have actual task-oriented instructions. Feature completion requires its relevant handbook, security tests, API documentation if exposed and ADR updates. Phase 3 stops for owner review before Phase 4.

## 23. Phase-3 acceptance and Phase-4 authorization — 2026-10-15

The owner accepted the delivered Phase-3 review with “freigegeben” after the explicit next-phase gate, then confirmed Phase 3 is merged. [Conversation record](docs/OWNER_APPROVAL_PHASE_4.md). Phase 4 resources/catalog is authorized, based on Main 25f3a4c. [ADR-016](docs/adr/016.md) concretizes independent authored Resource content, configurable types, permanent optional Asset-to-Unit identity, same-resource pools, additive Unit identifiers/XOR and scoped publication.

Public catalog/Home/search/detail/gallery use explicitly published Resource fields and separate sanitized catalog images; inventory metadata and internal location paths stay private. Internal published offers require current private-catalog grants; drafts and archive are not public. A public location label is separately authored. Publication and edits to published content require explicit resource.publish alongside manage. Tree changes cannot shift Resource scopes without corresponding management/publication rights. Units/pools are configuration; no booking engine, availability promise or dummy booking action before Phase 5. The handbook covers actual resources/catalog workflows now. No new dependency is needed; existing reviewed Pillow validates separate gallery uploads. Phase 4 stops for owner review before Phase 5.

## 24. Phase-4 acceptance and Phase-5 authorization — 2026-10-15

Owner confirmed “freigegeben und merged”; [record](docs/OWNER_APPROVAL_PHASE_5.md). Main 549ca27 is the Phase-5 basis. [ADR-017](docs/adr/017.md) implements the booking core with explicit onsite/physical_loan modes, current complete grant profiles, separate schedules, UTC claims, PostgreSQL exclusion and idempotency. Physical-loan confirmation remains fail-closed until Phase-6 profile/agreement gates; no fabricated consent or physical return. Own bookings, cancellation, real operational projections and configuration are in Phase 5. Phase 6 requires a new review gate; no production authorization.

## 25. Phase-5 acceptance and Phase-6 authorization — 2026-10-16

Owner confirmed “freigegeben und merged” following the Phase-5 review/next-phase gate. [Authorization](docs/OWNER_APPROVAL_PHASE_6.md), Main 96456d3. Phase 6 implements physical reservations with required personal profile/agreements/insurance, first identity-check evidence, separate appointments, actual custody, scanner-supported staffed issue/return/partial return, extensions and overdue/no-show handling. [ADR-018](docs/adr/018.md). Phase 7, public self-service, production and real personal data remain outside this approval.


## 26. Owner/team UX review gate — 2026-10-16

The owner confirmed Phase 6 is merged but not accepted. [Binding review gate](docs/review/OWNER_UX_REVIEW_GATE.md) authorizes an isolated fictional NCtest/Tailscale review instance, explicit seed, role accounts and review material, not a speculative redesign. [Deployment](docs/deployment/REVIEW_INSTANCE.md), [team tasks](docs/review/UX_REVIEW_PHASE_6.md). Phase 7 remains blocked until explicit owner approval after team feedback. No production or real personal data is authorized.

## 27. Owner UX correction before team review — 2026-10-16

[Binding correction](docs/review/OWNER_UX_CORRECTION.md), [owner notes](docs/review/OWNER_UX_NOTES.md)
and [ADR-020](docs/adr/020.md) authorize the correction of navigation, terminology,
visible availability, scheduling administration and resource-specific agreements/
qualifications within the Phase-6 review gate. The owner confirmed one visible
Admin role, preserving protected authority and explicit operational permissions.
MyTurn is evidence for operational presentation only: its item/check-out model,
membership types, fragmented scheduling and consent-like induction labels must not
replace Deelvo's established models. Owner feedback prevails.

Only additive migration and fictional review-data enhancement are authorized on
NCtest. Existing review records, passwords and media must survive. Full regression
and review-instance verification precede the actual team review. Stop there;
Phase 7 remains unauthorized.

## 28. Binding calendar correction — 2026-10-16

[Owner instruction](docs/review/OWNER_CALENDAR_CORRECTION.md) supersedes the daily
free-slot-card presentation. [ADR-021](docs/adr/021.md): month first, visual day
timeline and continuous start/end selection; day-mode offerings retain inclusive
date ranges. Existing policy maximum duration and grid constrain selections.
Onsite rooms/machines require at least 30 minutes total transition, configurable
through existing before/after fields. Current transition applies to new allocations
without rewriting historical claims; completed onsite use still blocks remaining
transition. PostgreSQL locking and deferred conflict protection remain authoritative.
Requirements follow period selection. Additive fictional calendar examples only;
full regression and green CI before preserving-data NCtest deployment. Stop for
owner/team review; no Phase 7 authorization.
