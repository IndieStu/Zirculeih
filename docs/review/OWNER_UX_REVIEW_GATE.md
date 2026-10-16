# Owner UX Review Gate — Team test instance after Phase 6

Phase 6 has reached the point where Deelvo should be reviewed as an actual application by the owner and the WERK/Zircula team.

Before starting the next normal development phase, create a dedicated:

    UX / Workflow Review Gate

The purpose is NOT to redesign Deelvo autonomously.

The purpose is to provide a realistic, safe and reproducible Deelvo test instance so the team can evaluate:

- terminology
- navigation
- information architecture
- operational workflows
- dashboard usefulness
- inventory/resource administration
- booking workflow
- checkout/return workflow
- scanner workflow
- permission-dependent UI
- mobile usability
- public catalogue usability

The team will provide explicit feedback after using the system.

Do not start Phase 7 until this owner/team review has been completed.


# 1. UX philosophy for this review

Do NOT perform a speculative visual redesign.

The current UI should be reviewed in actual use first.

The owner will provide screenshots from myTurn and other references where useful after testing Deelvo.

Those references may influence:

- information density
- navigation
- tables
- dashboard structure
- naming
- filters
- operational workflow
- status presentation

They are inspiration, not a request to clone another product.


## Admin UI priority

The Deelvo operational/admin interface does NOT need to be highly polished, decorative or marketing-oriented.

Priority order:

1. functional
2. clear
3. fast
4. information-dense where useful
5. predictable
6. accessible
7. visually coherent

Avoid:

- excessive cards
- huge whitespace
- oversized typography
- unnecessary animations
- decorative dashboards
- excessive modals
- hidden actions
- "clickibunti" SaaS UI
- turning every piece of information into a colored badge
- forcing simple workflows through many screens

Prefer:

- clear tables
- useful filters
- good search
- compact forms
- visible status
- obvious primary actions
- sensible breadcrumbs
- short operational workflows
- keyboard usability
- scanner-friendly focus handling

The public catalogue may be more visually inviting than the operational/admin interface.

Checkout/return should prioritize speed and clarity even more strongly than general administration.


# 2. Create a reproducible review environment

Prepare Deelvo so it can be deployed as an isolated test instance.

Primary target:

    NCtest test server

The server is reachable by the team through Tailscale.

This is NOT a production deployment.

Do not assume public Internet exposure.

The deployment should work on a normal Linux Docker host using the existing Docker Compose architecture.


## Target topology

Conceptually:

Team devices
      |
   Tailscale
      |
   NCtest
      |
   Deelvo review stack
      |
   PostgreSQL

The Deelvo instance should only need to be reachable through the private Tailscale environment unless the owner deliberately exposes it otherwise.


# 3. Review deployment profile

Provide a dedicated review/test deployment configuration.

Prefer extending the existing Compose setup rather than creating a completely separate deployment architecture.

For example, where appropriate:

    compose.yml
    compose.review.yml

or an equivalent maintainable approach.

Do NOT duplicate the entire production architecture just for the review.


The review deployment must have:

- Deelvo application
- PostgreSQL
- persistent database volume
- persistent media volume
- migrations on deployment/update
- static files
- healthchecks
- restart policy appropriate for a test server
- environment-based configuration
- no secrets committed to Git
- explicit review/test environment marker

Use the project's currently accepted PostgreSQL version.


# 4. Network exposure

Assume the server uses Tailscale.

Do NOT require Deelvo itself to integrate with the Tailscale API.

Deelvo should simply bind appropriately so it can be reached over the server's Tailscale network.

Document how the owner can choose between:

    http://<tailscale-hostname>:<port>

and, if already available in the server environment, a reverse-proxy hostname.

Do not require public DNS.

Do not require Let's Encrypt/public ACME for this private review deployment.

Do not weaken Django security globally merely because this is a test instance.

Configure ALLOWED_HOSTS and CSRF trusted origins through environment variables.


# 5. Reverse proxy

Keep compatibility with Caddy.

If a reverse proxy is useful, provide a small example configuration, but do not assume the owner must replace the existing server proxy setup.

Document both:

A. direct private Tailscale access

and

B. reverse-proxied private access

where practical.

Do not introduce Traefik, nginx or another infrastructure dependency merely for this review if the existing project already targets Caddy.


# 6. Explicit TEST INSTANCE indication

The review deployment must be visually unmistakable as a non-production instance.

Add a restrained but clearly visible environment indicator such as:

    TESTINSTANZ

or:

    UX REVIEW

in the authenticated operational UI.

It must not make the interface unusable.

This indicator should be configuration-driven and absent from normal production mode.


# 7. Demo / seed dataset

Provide a deterministic, explicitly invoked demo-data command.

For example conceptually:

    python manage.py seed_review_data

Do NOT automatically inject demo data on normal application startup.

The command must be safe for a dedicated review database.

If re-running it is supported, make its behavior deterministic/idempotent where practical.

If it intentionally resets review data, require an explicit flag and make the destructive behavior unmistakable.


# 8. Representative WERK-like demo data

Create realistic but entirely fictional test data.

Do NOT use real personal data.

The dataset should exercise Deelvo's domain model rather than merely populate random rows.


## Locations

Create representative locations such as:

WERK
├── Erdgeschoss
│   ├── Holzwerkstatt
│   ├── Metallwerkstatt
│   ├── Fahrradwerkstatt
│   └── Lager
├── Obergeschoss
│   ├── Digitalwerkstatt
│   ├── Besprechungsraum
│   └── Siebdruck
└── Außenbereich


Exact naming may be adjusted to the actual model.


## Inventory examples

Include representative Assets such as:

- cordless drill
- drill battery
- charger
- Prusa 3D printer
- CNC machine
- projector
- power station
- bicycle
- cargo bike
- cable drum
- screen-printing equipment
- ordinary non-bookable inventory item

Include examples of:

- active asset
- damaged asset
- maintenance/unavailable asset
- retired/archive example if useful
- asset with multiple identifiers
- asset with image
- asset with custom fields
- asset that is inventory-only
- asset linked to a ResourceUnit


## Resources

Create examples demonstrating that Deelvo is not merely a tool library.

Include:

### Room

    Besprechungsraum

Bookable time-slot Resource without physical Asset/Loan.


### Machine

    CNC-Fräse

Bookable on-site Resource backed by relevant inventory where appropriate.


### Machine / digital fabrication

    3D-Drucker

Use the currently implemented booking semantics.


### Pool

    Akkuschrauber

Multiple physical units if the current model supports this at the review stage.


### Vehicle

    Lastenrad

Physical resource suitable for booking/loan workflow if Phase 6 supports it.


### Equipment set

    Powerstation-Set

Use bundle/accessory semantics only if implemented by Phase 6.

Do not fake unsupported functionality.


# 9. Review users

Create fictional review accounts representing different permission profiles.

At minimum:

## Normal user

Can:

- browse catalogue
- view own account
- make permitted bookings
- view own bookings

Cannot access operational administration.


## Loan desk / operational staff

Can perform the Phase-6 operational loan workflow but should not automatically have full system administration.


## Workshop responsible person

Scoped access to relevant workshop/resources where the permission model supports it.


## Inventory staff

Can work with inventory/identifiers/locations but should not automatically receive unrelated administrative powers.


## Organization administrator

Broader Deelvo configuration permissions.


## System administrator

Only where needed for system-level review.


Use obvious fictional names such as:

    Test Nutzer
    Test Ausleihe
    Test Werkstatt
    Test Inventar
    Test Admin

Do not use real team-member names or emails.

Provide a safe mechanism for setting review passwords locally.

Do not commit passwords to Git.


# 10. Predefined operational states

The review dataset should contain realistic states so the dashboard and workflows are meaningful immediately after deployment.

Where supported by the Phase-6 implementation, include examples such as:

- booking today
- booking tomorrow
- upcoming pickup
- item currently checked out
- return due today
- overdue loan
- available item
- unavailable item
- damaged item
- open operational attention item

Only seed states supported by actual productive domains.

Do NOT invent fake future domain records merely to make the dashboard look populated.


# 11. Barcode / QR review material

Because scanner workflows are important, provide a simple way to obtain the demo identifiers.

If visual barcode/QR rendering is already supported safely, provide printable review labels.

If not, provide a simple page/list showing the identifier strings so the owner can:

- type them
- paste them
- test them with an HID scanner where possible

Do not add a large new barcode dependency solely for this review unless clearly justified and license-reviewed.


# 12. UX review checklist

Add a dedicated document:

    docs/review/UX_REVIEW_PHASE_6.md

The document should guide non-developer team members through realistic tasks.

It should not require understanding the Deelvo architecture.


Include scenarios such as:


## Public catalogue

1. Find the meeting room.
2. Find the CNC.
3. Understand whether/how each can be booked.
4. Determine where the resource is located.
5. Determine any requirements.


Ask reviewers:

- Did you understand the terminology?
- Did you know what to click?
- Was important information missing?
- Was anything unnecessarily technical?


## Booking

1. Log in as normal user.
2. Book the meeting room.
3. Find the booking afterwards.
4. Cancel it if permitted.

Review:

- wording
- calendar/time selection
- confirmation
- status terminology
- navigation


## Inventory

1. Log in as inventory staff.
2. Find a drill.
3. Find its current location.
4. Find its identifier.
5. Move/edit it if permitted.
6. Find an inventory-only item.

Review:

- search
- filters
- table density
- naming
- number of clicks


## Resource administration

1. Find the CNC Resource.
2. Understand its relationship to inventory/units.
3. Edit permitted information.
4. Determine whether it is published/bookable.

Review whether Asset / Resource / Unit distinctions leak unnecessary technical terminology into normal operational UI.


## Checkout

If Phase 6 supports it:

1. Log in as loan staff.
2. Select a borrower.
3. process a reservation pickup.
4. scan/select the relevant item.
5. review eligibility checks.
6. confirm checkout.

Review:

- speed
- clarity
- errors
- number of clicks
- terminology


## Spontaneous loan

If supported:

1. select borrower
2. scan/select item
3. complete spontaneous checkout

Compare this workflow with reservation pickup.


## Return

If supported:

1. scan an item
2. find its open LoanLine
3. record condition
4. perform a partial return where supported
5. complete the loan later

Review whether return is possible quickly without navigating through unrelated screens.


## Dashboard

Ask each role:

- Is the first screen useful?
- What information do you immediately need but cannot see?
- What is shown that you do not care about?
- Which actions should be one click away?
- Is the page too sparse or too busy?


# 13. Feedback template

Create:

    docs/review/UX_FEEDBACK_TEMPLATE.md

Use a simple structure that team members can fill in.

For example:

    Screen / workflow:
    Role used:
    What I tried to do:
    What worked:
    What confused me:
    Missing information:
    Wording I would change:
    Too many clicks:
    Severity:
      [ ] cosmetic
      [ ] annoying
      [ ] workflow problem
      [ ] blocker

Also include:

    Suggested wording:
    Screenshot/reference:


# 14. Terminology review

Explicitly flag terminology for owner review.

Do NOT assume internal domain terminology belongs in the UI.

Internal terms such as:

- Asset
- Resource
- ResourceUnit
- AllocationClaim
- Beneficiary
- Actor
- LoanLine

may be correct domain/code terminology while being inappropriate UI labels.

During this review, identify where internal terminology is exposed to normal users or staff.

Create:

    docs/review/TERMINOLOGY_REVIEW.md

List:

- current UI term
- internal domain term
- screen/context
- intended meaning
- owner decision required

Do not autonomously rename core domain models based on UX preference.

UI terminology may differ from code/domain terminology.


# 15. Navigation review

Document the current navigation separately for:

- anonymous/public user
- authenticated normal user
- operational staff
- organization admin

Identify:

- duplicate paths
- dead ends
- excessive nesting
- features difficult to discover
- actions only reachable through Django Admin

Do not redesign everything before owner review.

Record observations and wait for feedback.


# 16. Responsive/mobile review

The team may access the review instance from:

- desktop
- notebook
- tablet
- phone

Ensure currently implemented workflows remain usable at relevant widths.

Pay particular attention to:

- tables
- filters
- forms
- navigation
- scanner input
- checkout/return
- dashboard

Do not turn desktop operational tables into visually elaborate card grids merely to satisfy mobile design.

Horizontal scrolling for genuinely dense operational tables can be preferable to hiding important information.


# 17. Browser/manual verification

Before handing the instance to the owner:

Perform a manual browser review of the seeded test instance.

Verify at least:

- public catalogue
- login
- dashboard
- inventory list/detail
- identifier lookup
- resource detail
- booking flow
- own bookings
- operational booking view
- Phase-6 checkout/return workflows if implemented
- permission differences between review accounts
- mobile-width layout

Record any known UX issues.

Do not silently redesign around every issue discovered.

The owner/team review is the purpose of this gate.


# 18. Review deployment documentation

Create:

    docs/deployment/REVIEW_INSTANCE.md

It must explain, step-by-step:

1. prerequisites
2. copying/cloning Deelvo to NCtest
3. selecting the correct commit/tag
4. creating review environment configuration
5. generating secrets
6. starting the stack
7. running migrations
8. creating/initializing review accounts
9. seeding demo data
10. accessing via Tailscale
11. viewing logs
12. restarting services
13. updating to a newer review build
14. backing up review data if desired
15. resetting the entire review environment
16. removing the review deployment

Commands should be copy/pasteable where practical.

Do not assume production DevOps knowledge.


# 19. Safe reset

Provide a clearly documented method for resetting the test environment.

For example conceptually:

    docker compose ... down
    remove ONLY the explicitly named review volumes
    start again
    migrate
    seed review data

The reset process must be designed so it cannot accidentally delete unrelated Docker volumes on NCtest.

Never recommend commands such as broad Docker pruning as the standard reset procedure.


# 20. Backups

This is a review instance, so elaborate production backup infrastructure is unnecessary.

However, document a simple PostgreSQL + media backup/restore method so useful team review state can be preserved.

This also serves as an early practical validation of Deelvo's backup/restore architecture.


# 21. Email behavior

A test instance must not accidentally email real people.

Configure review mode so outgoing email is either:

- captured locally,
- logged safely,
- or routed to an explicit test mailbox/backend.

Do not allow seeded review users to trigger mail to real addresses.

Document the behavior.


# 22. Security

Although this is a test instance, preserve normal security boundaries.

Do NOT:

- disable CSRF
- disable authorization
- make all review users admins
- expose secrets in Git
- use DEBUG=True as a substitute for deployment configuration unless specifically justified
- expose PostgreSQL publicly
- expose the instance to the public Internet by default

The purpose is to test the real application, including its permission model.


# 23. Data privacy

Use fictional/demo data only.

Do not copy the current myTurn database.

Do not use real member/customer addresses, phone numbers or loan history.

The team should be able to deliberately enter additional fictional test data during review.


# 24. Test-instance version information

Expose enough version information for feedback to identify the tested build.

For example:

    Deelvo review
    commit: abc1234

This may be placed on an About/System page or restrained footer/admin area.

Do not expose sensitive infrastructure information.


# 25. Feedback workflow

Do not build an issue tracker into Deelvo.

The owner will collect:

- screenshots
- comments
- myTurn references
- terminology feedback
- workflow observations

After the review, these will be supplied back to Codex.

Prepare the repository documentation so feedback can be translated into concrete UX tasks.


# 26. Git workflow

Create a dedicated branch for the review-environment work if appropriate.

Do not mix unrelated Phase 7 functionality into this gate.

Commit:

- deployment profile
- seed command/data
- review docs
- necessary small UX fixes required to make the instance testable

Do not undertake a broad UI redesign without owner approval.


# 27. Definition of done for this gate

The UX Review Gate is ready when:

- current Phase-6 functionality runs on the isolated review deployment
- NCtest/Tailscale deployment is documented
- fictional representative data can be seeded
- role-specific review accounts can be created
- dashboard contains real seeded states
- scanner-compatible identifier lookup can be tested
- booking can be tested
- Phase-6 checkout/return can be tested if completed
- permissions can be compared between roles
- test email cannot accidentally reach real recipients
- review/reset/update procedure is documented
- handbook remains current
- UX review checklist exists
- feedback template exists
- terminology review exists
- full automated regression suite remains green
- Docker/PostgreSQL deployment validation remains green

Then STOP.

Do not begin Phase 7.

Report:

- branch
- commit
- CI status
- exact deployment procedure
- review URL pattern
- seeded roles
- seeded resources/assets
- known limitations
- known UX issues
- owner decisions needed

The next step is OWNER/TEAM UX REVIEW, not another implementation phase.