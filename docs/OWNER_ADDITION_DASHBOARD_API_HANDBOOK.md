# Additional owner requirements for Deelvo
# Apply during Phase 3 and update the long-term project plan

These requirements are approved additions to the Deelvo product specification.

Do not expand Phase 3 into future booking/loan implementation merely to demonstrate them.
Instead:

- implement what naturally belongs to Phase 3,
- establish architectural foundations where appropriate,
- update documentation/ADRs/acceptance criteria,
- schedule future implementation in the correct phases.

The three additions are:

1. Operational dashboard
2. Public/integration API + calendar interoperability
3. Continuously maintained user/admin handbook


# 1. Operational Dashboard

Deelvo shall have a proper operational dashboard.

The dashboard is not intended to be a decorative analytics page.

Its primary purpose is:

> Show staff what currently requires attention and provide fast access to common operational actions.

myTurn's dashboard is a useful conceptual reference for information density and quick operational access, but Deelvo must NOT copy its visual design.

The dashboard should evolve with the available domains.


## Dashboard information hierarchy

Prioritize actionable information over vanity statistics.

Future examples include:

- overdue returns
- pickups due today
- returns due today
- open booking approvals
- resources currently checked out
- maintenance/inspection due
- damaged/unavailable assets
- endangered follow-up reservations
- expiring qualifications

Simple counts such as total assets or total users may be displayed, but should not dominate the primary dashboard area.


## Quick actions

Provide a prominent Quick Actions area.

Future actions may include:

- Checkout / Return
- Scan code
- Find person
- Find asset/resource
- Create booking
- Create asset

Only expose actions actually implemented and permitted for the current user.

Do not create dead buttons for future functionality.


## "Today" view

The long-term dashboard should include an operational "Today" view combining different resource types.

Example:

10:00 Cargo bike — Return
13:00 Meeting room — Booking
15:30 Power station set — Pickup
18:00–21:00 CNC — Machine booking

This is important because Deelvo manages shared resources, not merely loaned objects.

Rooms, machines, vehicles and lendable assets should ultimately be representable in the same operational timeline where appropriate.


## Attention required

Provide a conceptual dashboard section for items requiring intervention.

Future examples:

- overdue loans
- damaged assets
- unavailable resources
- approval requests
- maintenance blocks
- qualification issues
- inventory discrepancies
- at-risk reservations


## Role/scope aware

Dashboard contents must respect the existing permission and scope system.

Do NOT create one universal dashboard that exposes organization-wide information to everyone.

Examples:

Loan staff:
- pickups
- returns
- overdue loans
- scanner/checkout actions

Workshop responsible person:
- relevant machines
- bookings
- blocks
- maintenance

Inventory staff:
- asset changes
- inventory discrepancies
- identifier/location actions

Organization administrators:
- broader organization overview

Users without operational permissions should eventually receive a personal area focused on:

- my bookings
- my loans
- upcoming returns
- my qualifications
- account requirements

Do not confuse this personal user area with the staff operational dashboard.


## Phase 3 implementation

During Phase 3, implement only dashboard components supported by existing productive domains.

It is acceptable and desirable to establish:

- dashboard shell/layout
- inventory-related counts/status
- relevant asset/location attention items
- Phase-3 quick actions
- identifier lookup/scan shortcut

Do NOT fake Booking, Loan, Maintenance or Inventory Run data.

Future phases should extend the dashboard when those domains become productive.

The dashboard architecture should make these additions straightforward.


## Analytics

Charts are secondary.

Do not reserve large dashboard areas for empty or low-value charts simply because dashboards traditionally contain graphs.

Only introduce analytics where the metric provides operational or management value.


# 2. API and interoperability

Deelvo shall provide a documented integration API.

The architectural principle remains:

> Business rules live in the domain/service layer.

The API, server-rendered UI, future kiosk workflows and other interfaces must call the same domain services and permission logic.

Do NOT duplicate booking, loan, inventory or permission logic in API serializers/views.


## API purpose

The API should eventually support integrations such as:

- Nextcloud
- websites
- internal dashboards
- automation systems
- other open-source tools
- future mobile clients
- organization-specific integrations

Do not implement an enormous CRUD API prematurely.

Expose stable, useful domain capabilities as the relevant domains become available.


## API versioning

Design the external API with explicit versioning from the beginning.

Preferred conceptual namespace:

    /api/v1/

Do not expose unstable internal model structure as a permanent public API contract.

Document:

- authentication
- authorization
- scopes/capabilities
- versioning
- pagination
- filtering
- error semantics
- date/time representation
- rate limiting where appropriate


## API authentication

Do not invent insecure long-lived global API keys.

Design an authentication approach suitable for:

- authenticated users
- organization integrations/service clients
- read-only integrations
- future scoped automation

API permissions must integrate with Deelvo's existing authorization model.

A token must not grant more capability than its owner/client is explicitly allowed.

Secrets/tokens must never be stored in plaintext where avoidable.

If the full token/client model belongs to a later phase, document the intended architecture now rather than prematurely implementing it.


# 3. Calendar interoperability

Calendar integration is an explicit Deelvo requirement.

A primary target is:

Nextcloud Calendar

but the implementation must use open standards and not be Nextcloud-specific.


## iCalendar / ICS

Deelvo should provide standards-compliant iCalendar feeds for relevant calendar data.

Future useful feed scopes include:

- personal bookings
- individual resource
- resource category
- location
- organization-wide operational calendar where authorized

Example:

A Nextcloud user should be able to subscribe to an authorized Deelvo calendar feed without requiring:

- email parsing
- scraping
- proprietary middleware


## Calendar semantics

Calendar events should ultimately include appropriate information such as:

- resource name
- booking start/end
- booking status where relevant
- location
- safe description
- stable event UID
- last-modified/update information

Do not leak private borrower/user information into public or broadly shared feeds.

Calendar visibility must respect permissions and privacy.


## Stable event identity

ICS events must use stable UIDs so that calendar clients update existing events instead of creating duplicates whenever Deelvo changes a booking.


## Time handling

Reuse the accepted Deelvo time model:

- IANA time zones
- correct DST handling
- [start, end) semantics internally

Export standards-compliant calendar timestamps.


## Feed security

Support safe authenticated/private feed concepts.

If subscription URLs use secret tokens:

- generate cryptographically strong opaque tokens
- allow revocation/regeneration
- do not contain sequential database IDs or PII
- treat possession of the URL as a credential
- document privacy implications

Do not expose organization-wide booking data through an unauthenticated predictable URL.


## CalDAV

Do NOT implement CalDAV in Phase 3.

Document it as a possible future enhancement.

For the initial one-way interoperability goal:

    Deelvo → Nextcloud Calendar

standards-compliant subscribable ICS feeds are sufficient and preferred.

Later evaluate whether bidirectional CalDAV synchronization provides enough value to justify its significantly greater complexity.


## Phase placement

Do not implement fake calendar feeds before the Booking domain exists.

During Phase 3:

- document the calendar architecture
- define acceptance criteria
- preserve suitable API/domain boundaries

Implement actual booking calendar feeds in the phase where productive Booking/calendar functionality exists.


# 4. Continuously maintained Deelvo handbook

Deelvo must have a proper user and administrator handbook.

This is separate from developer/architecture documentation.

The handbook is a first-class project deliverable.


## Documentation principle

> A feature is not complete until its user-facing and administrative documentation is updated.

Documentation must evolve alongside implementation, not be written at the end of the project.


## Repository structure

Create a maintainable documentation structure such as:

    docs/
      handbook/
        README.md
        getting-started.md
        concepts.md
        users-and-groups.md
        inventory.md
        locations.md
        identifiers-and-scanning.md
        resources.md
        bookings.md
        loans.md
        checkout-return.md
        qualifications.md
        maintenance.md
        inventory-runs.md
        calendar-integration.md
        api.md
        administration.md
        backup-restore.md
        troubleshooting.md

Only create meaningful content for implemented features.

Future chapter files may be omitted until needed rather than filled with speculative instructions.


## Audience

Clearly distinguish where necessary between:

### Regular users
People booking/borrowing resources.

### Operational staff
People performing checkout, return, inventory, approvals etc.

### Organization administrators
People configuring Deelvo.

### System administrators
People deploying, updating, backing up and operating the software.

Do not assume these roles are identical.


## Writing style

The handbook should be:

- task-oriented
- concise but complete
- understandable without reading architecture documents
- written for actual operators/users
- based on the real UI
- versioned with the application
- suitable for later rendering as an integrated documentation/help site


## Screenshots

Design the documentation workflow so screenshots can later be included where they materially improve instructions.

Do not add brittle screenshots for every trivial UI state.

Where screenshots are used, ensure they correspond to the current UI/version.


## Phase 3 handbook requirements

At minimum document the Phase 3 functionality actually implemented, including as applicable:

- inventory overview
- creating an asset
- editing an asset
- categories
- condition/lifecycle
- locations and location hierarchy
- moving an asset
- identifiers
- manually looking up/scanning an identifier
- archiving/retiring assets
- permissions relevant to inventory
- administrator configuration

Also document the already implemented Phase 2 user/account/group functionality if no proper handbook documentation currently exists for it.

Do not merely link users to ARCHITECTURE.md or PROJECT_SPEC.md.


# 5. Developer/API documentation

Keep user handbook and developer documentation conceptually separate.

The project should eventually include:

- user/admin handbook
- deployment/operations documentation
- API documentation
- architecture/developer documentation

For the API, prefer machine-readable OpenAPI documentation once productive endpoints exist.

Any DRF/OpenAPI dependency must go through the existing open-source dependency/license review.


# 6. Update project planning

Update:

- PROJECT_SPEC.md
- ARCHITECTURE.md
- UI_UX.md
- DEVELOPMENT_PLAN.md
- SECURITY.md
- PERMISSIONS.md where relevant
- acceptance/test matrix
- relevant ADRs

to make these requirements explicit.

Add acceptance criteria covering at least:

DASH:
- dashboard respects permissions/scopes
- only implemented actions are shown
- actionable information prioritized
- Phase 3 inventory dashboard works without fake future data

API:
- API uses shared domain services
- explicit API versioning
- permission enforcement
- no internal-model authorization bypass

CAL:
- standards-compliant ICS
- stable event UIDs
- timezone/DST correctness
- privacy-aware feed content
- revocable private feed access
- Nextcloud-compatible subscription workflow

DOC:
- handbook exists
- Phase 2 functionality documented
- Phase 3 functionality documented
- documentation updated as part of feature completion


# 7. Definition of Done change

From this point forward, update Deelvo's Definition of Done:

A user-facing or administrator-facing feature is NOT complete unless:

1. implementation is complete,
2. automated tests are complete,
3. authorization/security implications are tested,
4. relevant handbook documentation is updated,
5. relevant API documentation is updated if the feature is externally exposed,
6. architecture/ADR documentation is updated if architectural behavior changed.

Apply this rule to Phase 3 and all future phases.


# 8. Preserve Phase 3 scope

These additions must not cause uncontrolled Phase 3 scope expansion.

Implement the dashboard portions supported by Phase 3.

Establish/document API and calendar architecture now.

Implement productive APIs only where useful for existing domains and consistent with the development plan.

Do not implement booking ICS feeds until Booking exists.

Create/update the handbook now for functionality that already exists.

Do not implement CalDAV now.

Do not start Phase 4.

At Phase 3 completion, include dashboard, API/calendar planning, and handbook status in the Phase 3 review report.