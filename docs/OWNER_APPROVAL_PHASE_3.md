# Owner approval: Phase 2 accepted — start Phase 3

Phase 2 has been reviewed by the owner and is APPROVED.

The Phase 2 branch has already been merged into `main`.

Treat the current `main` branch as the authoritative baseline. Do not repeat the Phase 2 review and do not recreate or re-merge the old Phase 2 branch.

Before implementation:
1. Update/sync from current `main`.
2. Verify that the merged Phase 2 state is present.
3. Run the existing test suite.
4. Preserve all accepted ADRs, acceptance criteria and architectural decisions.
5. Then create a new branch for Phase 3.

Proceed with:

# Phase 3 — Inventory, locations, assets and identifiers

The goal of Phase 3 is to establish Deelvo's productive inventory foundation.

This is NOT yet the booking/loan implementation.

The design must remain consistent with the central domain principle:

> Deelvo manages resources, not merely "things".

A physical Asset and a bookable Resource are different concepts.
An Asset may exist purely as inventory.
A Resource may later represent a room, machine, vehicle, pool or other usable/bookable capability without necessarily being a physical Asset.

Do not collapse these concepts merely because Phase 3 initially focuses on inventory.

## 1. Location hierarchy

Implement a proper hierarchical location model suitable for organizations such as makerspaces, cultural centres, repair cafés and open workshops.

It must support structures such as:

Organization
→ Building
→ Floor
→ Room
→ Storage location

Do NOT hard-code these five levels as mandatory fixed database columns.

The model should support a hierarchy/tree so that real organizations can use shallower or deeper structures.

Examples:

WERK
→ Main building
→ Ground floor
→ Wood workshop
→ Cabinet 3

or simply:

External storage
→ Shelf A

Requirements:

- stable IDs
- human-readable name
- optional description
- parent/child hierarchy
- active/inactive state
- deterministic path/breadcrumb representation
- safe movement/re-parenting
- no cyclic hierarchies
- permissions must be compatible with the existing scoped permission architecture
- deleting locations with existing inventory/history must not silently destroy historical information

Design for later inventory runs scoped to a location and its descendants.

## 2. Asset model

Implement the productive Asset model.

An Asset represents an individually inventoried physical object.

Examples:

- drill
- battery
- charger
- 3D printer
- CNC machine
- bicycle
- cargo bike
- projector
- table
- chair
- power station
- cable drum
- screen-printing frame

An Asset is NOT automatically lendable or bookable.

Initial Asset fields/domain concepts should include at least:

- stable internal ID
- inventory number
- name
- description
- category
- manufacturer
- model
- serial number
- acquisition date
- acquisition value where appropriate
- current location
- condition
- lifecycle/status
- internal notes
- created/updated timestamps
- archival/decommissioning support

Do not over-model procurement/accounting in Phase 3.

Ownership/funding/accounting can remain future concerns unless already required by accepted architecture.

Avoid destructive deletion where historical references would later matter.

## 3. Categories

Implement configurable asset categories.

Do not hard-code categories such as "tool", "machine" or "vehicle".

Categories should support future filtering, inventory views and policy/resource integration.

Prefer a structure that can evolve without requiring schema changes for organization-specific categories.

Do not turn categories into a generic rules engine.

## 4. Asset condition and lifecycle

Condition and lifecycle/status must remain conceptually distinct.

Examples:

Condition:
- good
- worn
- damaged
- needs inspection

Lifecycle/status:
- active
- temporarily unavailable
- maintenance
- retired
- lost

Do not assume these exact values must all be hard-coded if the existing architecture indicates a configurable approach.

Document the chosen model and its implications.

A later Loan return must be able to update/report condition without confusing that with lifecycle state.

## 5. Generic Identifier model — IMPORTANT

Implement the generic identifier concept established by the kiosk/scanner architecture and ADR-011.

Do NOT add only a `barcode` field to Asset.

A scannable object may have multiple identifiers.

Examples:

- Deelvo-generated QR code
- Deelvo-generated barcode
- existing organization inventory number
- manufacturer barcode
- organization-specific barcode
- manually assigned external code

Identifiers need at least:

- stable identity
- identifier type/kind
- normalized value
- human-readable/raw representation where necessary
- target object
- active/inactive state
- provenance/source where useful
- timestamps

Identifier values that participate in scan resolution must have database-enforced uniqueness appropriate to their namespace/type.

Do not rely solely on application-level uniqueness.

The resolver must be workflow-independent:

    scan/input
        ↓
    identifier resolution
        ↓
    identified domain object
        ↓
    active workflow decides what the scan means

Examples:

Checkout workflow:
Asset X → add/validate for checkout

Return workflow:
Asset X → locate open LoanLine

Inventory workflow:
Asset X → mark seen / detect location discrepancy

Lookup workflow:
Asset X → show details

The identifier resolver itself MUST NOT contain checkout, return, booking or inventory-run business logic.

Unknown identifiers must result in a clean explicit "not found/unknown identifier" result, not an exception-driven or ambiguous workflow.

## 6. Asset vs ResourceUnit boundary

This must be explicitly resolved/documented before or during implementation.

The accepted architecture already distinguishes:

Asset
→ Resource
→ ResourceUnit
→ AllocationClaim

Do not accidentally redefine Asset as ResourceUnit.

Phase 3 does not need to implement the complete productive Resource/Booking domain if that belongs to a later phase.

However, the model must make the future relationship possible without destructive migration.

Consider:

- an Asset may later back a ResourceUnit
- a ResourceUnit may represent an allocatable unit
- an Asset remains the inventory/custody/lifecycle object
- not every Asset becomes a ResourceUnit
- some Resources (e.g. rooms) may have no Asset at all

Document the intended mapping clearly.

If ResourceUnit is not implemented productively in Phase 3, Identifier architecture must still be designed so that direct ResourceUnit identifiers can be supported later without replacing the model.

Do not introduce premature generic polymorphism merely to anticipate every future object type. Prefer an explicit, maintainable domain design.

## 7. Identifier generation

Provide a safe foundation for Deelvo-owned identifiers.

Requirements:

- opaque/stable public code
- do not expose sequential database IDs
- do not encode personal or sensitive information
- suitable for QR/barcode representation
- collision-safe generation
- database-enforced uniqueness
- human/manual entry must remain possible

Actual visual QR/barcode generation may be implemented if it is small, dependency-safe and appropriate to Phase 3.

If it would introduce unnecessary scope/dependencies, implement the identifier/code foundation now and schedule rendering/printing for the later scanner/inventory phase.

Document the decision.

Any new dependency requires the existing dependency/license review process.

## 8. Asset detail and inventory UI

Implement an operational UI appropriate for actual staff use.

Do not rely on Django Admin as the primary interface.

Django Admin may remain a superuser/emergency interface.

At minimum provide:

- asset list
- search
- useful filtering
- asset detail
- create/edit asset
- location display
- category display
- identifiers
- condition/status
- archive/retire behavior where applicable

The UI must remain:

- server-rendered Django + HTMX where useful
- mobile-friendly
- keyboard accessible
- WCAG 2.2 AA target
- compatible with future barcode scanner/HID workflows

Do NOT build the full kiosk UI yet.

## 9. Fast identifier lookup

Provide an operational lookup path where an authorized user can enter/scan an identifier and immediately resolve the Asset.

This is the first useful scanner-compatible workflow.

It should work well with ordinary USB/Bluetooth HID barcode scanners, which behave like keyboards.

Requirements:

- autofocus where appropriate
- Enter submits
- fast response
- clear success
- clear unknown-code response
- no scanner-specific proprietary SDK
- no camera scanning yet
- no checkout/return action yet

This validates the identifier architecture without pulling the later kiosk workflows into Phase 3.

## 10. Images and attachments

Assets will eventually need images, documents and maintenance-related files.

For Phase 3, implement the smallest sound foundation needed for asset images/attachments if consistent with the existing development plan.

Requirements if implemented:

- local/self-hosted media storage compatible with Docker deployment
- no mandatory proprietary object-storage/SaaS dependency
- safe upload validation
- sensible file size/type restrictions
- authorization
- no executable uploads
- privacy/security considerations documented
- backup/restore documentation includes media

Do not build a document-management system.

## 11. Auditability

Use the existing audit infrastructure.

Important inventory mutations should be auditable, including at least:

- asset creation
- significant asset edits
- identifier assignment/removal
- location changes
- lifecycle/status changes
- archival/retirement

Audit actor and relevant before/after information where appropriate.

Pure asset viewing/lookup does not need to generate noisy audit events unless security requirements demand it.

## 12. Permissions

Integrate with the Phase 2 permission architecture.

Do not create a second inventory-specific authorization system.

Define explicit capabilities/scopes for operations such as:

- view inventory
- create assets
- edit assets
- manage identifiers
- move assets
- manage categories/locations
- archive/retire assets

Respect explicit denies and existing scoped grants.

System admin/staff status alone must not magically grant operational inventory permissions unless that is already an explicitly accepted platform rule.

Test IDOR and scope boundaries.

## 13. Inventory history

Current location alone is not enough for the long-term system.

Provide a maintainable basis for tracking important asset movement/history.

At minimum, location changes must not simply erase all knowledge of previous placement.

Avoid a full event-sourcing architecture.

A straightforward movement/history record or existing audit/history mechanism is preferred.

The later inventory-run feature must be able to report discrepancies without silently rewriting master location.

Do NOT implement full Inventory Runs yet unless already explicitly scheduled for Phase 3.

## 14. Custom fields

Asset management will eventually need organization-specific metadata.

Examples:

- electrical inspection date
- internal cost centre
- workshop-specific classification
- dimensions
- donor reference

Do not create dozens of WERK-specific database fields.

If the accepted development plan places custom fields in Phase 3, implement a restrained typed custom-field mechanism.

If not, document the extension point and defer the full implementation.

Do not build a generic low-code database or arbitrary rules engine.

## 15. Import/export

Do not expand Phase 3 unnecessarily.

CSV import/export is desired for Deelvo, but follow the accepted DEVELOPMENT_PLAN phase assignment.

If it belongs to a later phase, ensure the Phase 3 model uses stable identifiers and clean field semantics so future import/export can be added without redesign.

## 16. Branding

The product is now named:

Deelvo

Use:
- `Deelvo` for user-facing naming
- `deelvo` for technical identifiers where appropriate

Previous names `Zirculeih` and `Lendry` are historical only.

Current approved branding foundation:

Primary Blue:
#5590BF

Secondary Orange:
#F79007

Warm Paper:
#F6F3E9

Ink:
#11140F

Typography:
Inter, self-hosted, SIL Open Font License 1.1.

No final Deelvo logo has been approved.

Do NOT invent or generate a logo.

Use the plain text wordmark where branding is required.

Keep brand/design tokens centralized.

## 17. Explicitly out of scope for Phase 3

Do NOT implement prematurely:

- full Resource booking
- booking engine
- AllocationClaim production model unless required by the accepted phase plan
- Loan/LoanLine workflows
- checkout
- return
- reservation pickup
- spontaneous loan
- recurring bookings
- full kiosk mode
- camera barcode scanning
- self-service kiosk
- inventory runs/full stocktake workflow
- maintenance scheduling system
- notifications
- billing/payments
- multi-tenancy
- mobile app
- offline mode
- Redis/Celery unless independently justified by an actual Phase 3 requirement

Do not weaken architecture to fake these features either.

## 18. Tests

Phase 3 must include meaningful automated tests, not only model smoke tests.

At minimum test:

### Locations
- hierarchy creation
- cycle prevention
- movement/re-parenting
- scoped access
- assets retain valid/history-aware location behavior

### Assets
- create/edit/archive
- category/condition/status behavior
- inventory-number constraints
- permission boundaries
- IDOR protection

### Identifiers
- multiple identifiers per supported object
- database uniqueness
- normalization rules
- active/inactive identifiers
- unknown identifier
- deterministic resolution
- concurrent attempts to claim the same identifier
- identifier reassignment rules
- no sequential DB ID leakage in Deelvo-generated public identifiers

### Scanner-compatible lookup
- keyboard/manual input
- Enter-submit workflow
- known code
- unknown code
- unauthorized lookup
- rapid repeated lookup where relevant

### Audit/history
- location movement history
- identifier changes
- lifecycle changes
- actor attribution

### Security
- CSRF
- authorization
- IDOR
- upload validation if attachments are implemented
- malicious/oversized identifier input
- appropriate rate limiting if lookup is exposed in a way that creates enumeration risk

Run the full existing Phase 1 + Phase 2 suite as regression tests.

The existing PostgreSQL concurrency prototype must remain intact unless replaced by a demonstrably equivalent or better implementation with preserved acceptance coverage.

## 19. Documentation

Update the relevant project documentation as implementation decisions are made:

- README
- PROJECT_SPEC
- ARCHITECTURE
- DATA_MODEL
- PERMISSIONS
- UI_UX
- DEVELOPMENT_PLAN
- SECURITY
- DEPENDENCIES
- test/acceptance matrix
- ADRs where an architectural decision is needed

In particular document:

1. Location hierarchy design
2. Asset/category/condition/lifecycle design
3. Identifier architecture and normalization
4. Identifier uniqueness semantics
5. Asset ↔ future ResourceUnit relationship
6. Scanner-compatible lookup boundary
7. Inventory/location history approach
8. Any new dependency and license
9. Any consciously deferred Phase 3 item

Do not rewrite historical ADRs merely to make them look as though Deelvo was always the project name. Preserve historical integrity where relevant.

## 20. Phase 3 completion report

When implementation is complete, stop before Phase 4.

Provide a review report containing:

- branch name
- commit(s)
- PR URL if creation is available
- summary of implemented domain model
- migrations created
- UI/screens implemented
- permission capabilities added
- identifier design
- location/history design
- dependencies added/removed
- security considerations
- tests added
- full test results
- Docker/PostgreSQL test environment used
- CI result
- documentation/ADR changes
- known limitations
- deferred work
- any owner decisions still required

If GitHub integration prevents PR creation, push the branch if possible and report the exact limitation. Do not claim a PR exists when it does not.

Do not start Phase 4 without owner review.

# Quality bar

Prefer correctness and maintainability over feature count.

This phase establishes Deelvo's long-term inventory identity.

Especially avoid these shortcuts:

- Asset == Resource
- Asset == ResourceUnit
- one barcode column on Asset
- hard-coded WERK locations/categories
- authorization in templates/views instead of domain/service layer
- scanner-specific business logic
- silent location changes
- destructive history loss
- sequential database IDs in public QR/barcodes
- Django Admin as the operational product UI

When an implementation detail conflicts with an accepted ADR or existing architecture, preserve the accepted architecture and document the conflict rather than silently changing it.

Start from current `main`, verify the baseline, create the Phase 3 branch, implement Phase 3, test it, update documentation, and stop for owner review.