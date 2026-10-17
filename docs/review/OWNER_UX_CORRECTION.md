# Owner UX correction pass before team review

The attached ZIP `Deelvouxreview.zip` contains:

- owner UX review notes
- screenshots of the current Deelvo review instance
- screenshots from myTurn used as functional UX references

Read the complete review note and inspect every screenshot before changing code.

This is an OWNER UX CORRECTION PASS on the current Phase-6 review branch.

The current NCtest build is technically functional, but it is not yet suitable
for handing to the wider team because too much domain/technical complexity is
exposed directly in the interface.

Do NOT start Phase 7.

Do NOT change the fundamental domain architecture merely to make the UI simpler.

The objective is:

    Keep the domain model rigorous.
    Make the human interface simple.

The UI must not require users to understand Deelvo's ADRs, internal models or
edge-case terminology.


# 1. Primary UX principle

Adopt this principle throughout the application:

    Concise by default, explanatory on demand.

And:

    Domain rules should primarily be enforced by application behaviour,
    not permanently explained next to ordinary controls.

Short, unambiguous labels are preferred.

Long explanations, guarantees, caveats and implementation details belong only
where they are contextually necessary:

- contextual help
- error messages
- exceptional states
- confirmation dialogs
- documentation

They should NOT permanently accompany normal objects and actions.


# 2. Remove UI over-explanation

Review all current user-facing screens for explanatory clutter.

Examples already observed include wording equivalent to:

- "enthält keine Ausleihgarantie"
- "Standort ausdrücklich ändern"
- explanations of allocation guarantees
- technical timezone explanations
- permanent descriptions of internal safety semantics

Do not blindly delete information.

Classify it:

A. necessary for the current decision -> keep concise
B. only necessary in an exceptional situation -> show conditionally
C. documentation/help -> move out of primary UI
D. implementation/domain detail -> remove from user-facing UI

Names should normally just be names.

Buttons should normally just describe their action.


# 3. Booking form: major simplification

The screenshots show an unacceptable amount of timezone/DST implementation
detail in the normal booking form.

A normal user must NOT normally see controls such as:

    Beginn bei doppelter Herbst-Uhrzeit
    Ende bei doppelter Herbst-Uhrzeit
    Abholtermin lokal bei Herbstumstellung
    Rückgabetermin lokal bei Herbstumstellung

Nor should "Europe/Berlin" need to be explained on every ordinary reservation.

Keep the existing correct IANA timezone and DST domain semantics.

Change only their presentation.


## Normal case

The normal booking UI should primarily ask for things such as:

    Von
    Bis

and, where physically relevant:

    Abholung
    Rückgabe

Prefer appropriate date/time pickers and availability/calendar interaction over
raw technical timestamp configuration.


## DST edge case

Most users must never have to think about DST ambiguity.

If a user actually selects a local time that occurs twice during the autumn DST
transition, THEN and only then ask a human-readable disambiguation such as:

    Diese Uhrzeit kommt an diesem Tag zweimal vor.
    Meinst du die frühere oder die spätere Uhrzeit?

If a selected local time does not exist because of the spring transition,
explain that specific problem and ask for another time.

Do not expose the technical mechanism pre-emptively.


# 4. Availability should become visible, not merely queried

The owner wants availability to become a central part of the catalogue UX.

For bookable items/resources, show useful current availability directly where
possible.

Do not imply guaranteed physical issue where that is not true.

But do not solve this by attaching legalistic disclaimers to every item.


## Catalogue

For a bookable catalogue entry, users should be able to understand quickly:

- what it is
- whether it is currently available / bookable
- relevant upcoming availability
- how to select a booking period


## Calendar

Add or improve a calendar/availability view for bookable resources.

The owner explicitly wants a workflow inspired by the useful aspects of myTurn:

    see availability
        ->
    click/select free period
        ->
    continue booking

Do NOT copy myTurn's visual design.

Use the supplied screenshots as functional inspiration only.

A user should not have to manually type arbitrary timestamps before seeing
whether a resource is available.


# 5. Resource / unit / asset UX problem

The owner currently does not understand the distinction between:

    Angebot
    Einheit
    Asset

This is a serious UX finding.

The internal distinction remains valid and MUST NOT simply be collapsed in the
domain model.

However, normal users must not need to understand that model.


Consider this real scenario:

    "3D-Drucker"

The organization owns:

- Prusa Mini+
- Prusa i3 MK3S
- Prusa MK4

These are NOT necessarily interchangeable from the user's perspective.

Build volume and capabilities differ.

Likewise:

    Fahrrad

may contain bicycles with different sizes/capacities/features.


## Required UX behaviour

The catalogue must make clear WHAT the user will actually reserve when concrete
units differ materially.

Do not hide materially different equipment behind an abstract pool merely
because the model supports ResourceUnits.

Use the existing model intelligently.

Possible UX patterns may include:

    3D-Drucker
      Prusa Mini+
      Prusa i3 MK3S
      Prusa MK4

or individual catalogue entries where that better represents user intent.

Equivalent units such as several truly identical cordless drills may remain a
pool where automatic assignment is appropriate.

The key distinction should be:

    interchangeable units
    versus
    user-selectable/distinct units

Investigate whether the existing model already supports this cleanly.

Prefer a presentation/configuration solution over a destructive domain-model
rewrite.

Document any actual model gap before changing architecture.


# 6. User-facing terminology

"Angebote verwalten" is confusing to the owner.

The word "Angebot" currently exposes an abstraction that is not natural in this
operational context.

Review terminology across the UI.

Potential user-facing concepts include:

    Artikel
    Räume
    Maschinen
    Fahrzeuge
    Ausstattung
    Buchbare Ressourcen

Do NOT mechanically rename the internal Resource model.

Internal code terminology and user-facing terminology may differ.


For the operational interface, investigate a clearer label such as:

    Artikel & Ressourcen

or another concise term supported by the actual contents.

For creation actions, prefer concrete wording where possible:

    Artikel anlegen
    Raum anlegen
    Maschine anlegen

rather than requiring staff to think in abstract Resource terminology.

Do not finalize ambiguous terminology silently.

Where owner choice remains necessary, document the alternatives.


# 7. Categories must be administrable

The owner could find predefined classifications such as "Fahrzeug" but could not
find where categories can be created or renamed.

Investigate the current implementation.

The organization needs to manage its own useful catalogue categories.

Examples might include:

- Räume
- Werkzeuge
- Maschinen
- Fahrzeuge
- Veranstaltungstechnik
- Elektronik
- Energie
- Druck / Digitalfertigung

Do not hardcode WERK-specific categories.

Provide an understandable admin workflow to:

- create
- rename
- order if supported/appropriate
- archive/deactivate where appropriate

categories.

If "Fahrzeug" is currently an internal Resource type rather than a category,
do not conflate the concepts.

Instead make the distinction understandable in the UI and provide the missing
category administration.


# 8. Locations: public filtering is too granular

The owner reports that public/user-facing location filtering is too detailed.

Users generally do not need catalogue filters such as:

    Außenbereich
    Lager
    Digitallabor

simply because those nodes exist in the internal inventory location tree.

Preserve the detailed hierarchical location model for inventory and operations.

Do NOT automatically expose every inventory location as a public catalogue
filter.

Introduce or use an appropriate visibility/filtering concept so public
navigation can remain useful.

Internal storage location and public catalogue classification are different
concerns.


# 9. Opening hours and closures

The owner explicitly requires organization operating calendars.

Examples:

    Wednesday-Friday 11:00-20:00

plus:

- individual closing days
- holidays
- vacation/closure periods
- temporary exceptions

These must influence availability.

The system already has concepts for usage windows / staffed windows / pickup /
return windows.

Review what is currently implemented and expose a practical administration UI.


Important:

Different activity types may need different schedules.

For example:

    room booking availability
    machine usage
    item pickup
    item return

may differ.

The owner specifically wants closures/opening rules configurable according to
the relevant booking/resource category or operational context.

Do not implement a simplistic global boolean "open/closed" if the existing
domain already supports richer rules.

Do not unnecessarily redesign the scheduling engine.

Expose the existing capability coherently and fill actual gaps where required.


# 10. Groups administration

The owner cannot find where to create groups.

Investigate whether this is:

- missing functionality
- permissions
- hidden navigation
- Django-admin-only functionality

Groups are a core Deelvo concept and must have an understandable operational
administration path.

Authorized organization administrators should be able to manage groups without
needing Django Admin.


# 11. User administration

The owner cannot find how an authorized administrator can create/add a user.

Investigate the existing account architecture.

Do not compromise the verified-email/local-registration design.

But provide an appropriate organization-admin workflow where allowed by the
current security model.

Clarify the intended difference between:

- self-registration
- inviting a user
- administratively creating/adding a person/account

Choose the safe workflow that fits the existing account architecture.

If an owner decision is required, document it rather than inventing unsafe
semantics.


# 12. "Meine Buchungen" and "Meine Ausleihen"

The owner considers these unnecessarily separated for ordinary users.

Preserve Booking and Loan as separate domain lifecycles.

But investigate combining their user-facing presentation into a single area,
for example:

    Meine Vorgänge

or:

    Meine Buchungen & Ausleihen

The page can then distinguish individual entries/statuses internally.

Do not merge the underlying Booking and Loan models.

The goal is navigation simplification, not domain collapse.


# 13. Operational dashboard

Rename:

    Betriebsübersicht

to:

    Dashboard

unless a strong UX reason prevents this.

For staff/admin users, make Dashboard the natural default operational landing
page.

Use the supplied myTurn screenshots as FUNCTIONAL inspiration.

Do not copy the design.

The owner specifically values the useful information/functions of the myTurn
dashboard.

Deelvo's dashboard should prioritize operational information such as, where
implemented:

- pickups today
- returns today
- overdue returns
- bookings today
- open operational attention
- maintenance/blocks where currently relevant
- useful quick actions

Avoid vanity metrics and decorative charts.


# 14. Operational navigation

The current large horizontal navigation is becoming difficult to scan.

Move the authenticated operational/admin navigation toward a structured LEFT
SIDEBAR on desktop.

The sidebar should group related functions rather than presenting a long flat
list.

For example conceptually:

    Dashboard

    Betrieb
      Buchungen
      Ausgabe & Rückgabe

    Bestand
      Artikel / Ressourcen
      Inventar
      Standorte

    Organisation
      Personen
      Gruppen
      Vereinbarungen

    Einstellungen
      Kategorien
      Öffnungszeiten
      ...

Do not treat this exact hierarchy as mandatory.

Derive the final grouping from actually implemented functions.

Keep public/user navigation distinct from staff operational navigation.

Ensure responsive behaviour on smaller screens.


# 15. Do not over-polish the admin UI

The owner explicitly does NOT want an ultra-polished decorative admin backend.

Priority:

1. functional
2. clear
3. fast
4. compact
5. understandable

Use:

- good tables
- filters
- search
- sensible forms
- clear states
- short workflows

Avoid:

- excessive cards
- huge whitespace
- decorative widgets
- animations
- SaaS-style visual clutter

The public catalogue may be more visually inviting.


# 16. Screenshots are evidence, not specifications

Inspect every screenshot in the ZIP.

Use myTurn screenshots to understand what the owner finds useful, especially:

- immediately visible availability
- catalogue structure
- calendar-driven booking
- useful dashboard information

Do NOT:

- reproduce myTurn branding
- clone its layout pixel-for-pixel
- inherit its domain limitations
- change Deelvo back into a tool-library-centric system


# 17. Resource-specific agreements, confirmations and qualifications

The owner identified an important UX/domain requirement around agreements.

Currently agreements appear too detached from the resources they actually
govern.

Authorized administrators must be able to configure which requirements apply
to a specific Resource / bookable item.

For example:

    3D-Drucker

        required agreement:
            Nutzungsbestätigung 3D-Drucker

        required qualification:
            Einweisung 3D-Drucker

or:

    Lastenrad

        required agreement:
            Nutzungsbedingungen Lastenrad

A user should encounter these requirements naturally in the booking/use
workflow rather than having to find and accept unrelated agreements elsewhere.


## Agreements

Allow applicable agreements to be assigned to resources.

An agreement must be versioned.

Store acceptance against the exact agreement version.

Example:

    Nutzungsbestätigung 3D-Drucker
    Version 3

If the user has already accepted the currently required version, do not ask
again on every booking.

If the agreement text/version changes, the new version requires fresh
acceptance before the protected action can proceed.

Historical acceptance must remain auditable.

Do not overwrite old acceptance records when an agreement changes.


## Booking UX

When a user attempts to book a resource:

1. determine the actual requirements for that resource
2. check which requirements the user already satisfies
3. show only outstanding requirements

Example:

    3D-Drucker buchen

    Voraussetzung

    Nutzungsbestätigung 3D-Drucker

    [concise agreement text / expandable details]

    [ ] Ich habe die Nutzungsbedingungen gelesen und akzeptiere sie.

The confirmation should become part of the user's account state for that exact
agreement version.

On the next booking, do not show it again while that version remains valid.


## Do not confuse agreement with qualification

An agreement/confirmation and a qualification/instruction are different
concepts.

Example:

    Nutzungsbestätigung 3D-Drucker
        -> user can personally accept this agreement

    Einweisung 3D-Drucker
        -> qualification/instruction status
        -> normally granted/documented by an authorized person

A user must not be able to self-certify a staff-granted qualification merely
by checking a checkbox.

A resource may require:

- agreement only
- qualification only
- both
- neither


## Account UX

The user's account should provide a concise overview of relevant current
requirements/statuses.

For example:

    Einweisungen & Vereinbarungen

    3D-Drucker
        Einweisung                 gültig
        Nutzungsbestätigung v3     akzeptiert

    CNC-Fräse
        Einweisung                 fehlt

Avoid exposing internal requirement IDs or policy implementation details.


## Resource administration

When editing a resource, authorized administrators should be able to configure
requirements directly in the context of that resource.

For example conceptually:

    Voraussetzungen

    Erforderliche Vereinbarungen
        [x] Nutzungsbestätigung 3D-Drucker

    Erforderliche Einweisungen
        [x] Einweisung 3D-Drucker

Do not require administrators to maintain an external undocumented mapping.

The relationship must be stored explicitly in Deelvo.


## Requirement inheritance / reuse

Do not duplicate agreement text for every individual physical unit.

Requirements should normally be attached at the appropriate Resource level and
therefore apply to its relevant units.

The same versioned agreement or qualification type may be reusable by multiple
resources where appropriate.

If more granular unit-level requirements are genuinely needed later, do not
prematurely complicate this UX unless the current domain already supports them.


## Enforcement

These requirements are not merely informational.

Enforce them server-side at the appropriate protected action.

A UI checkbox alone must never be the security mechanism.

Do not allow API/direct requests to bypass mandatory current agreements or
qualifications.

Preserve the existing rule that mandatory consents/qualifications are hard
requirements and cannot simply be bypassed through an operational override.


## Existing architecture

Before implementing new models, inspect the existing agreement,
qualification and policy architecture.

Reuse and expose existing capabilities where they already exist.

Do not create a second parallel agreement/qualification system solely for this
UX correction.

Document any actual model gap before introducing a new domain concept.


# 18. Preserve architecture

The following remain fundamental:

- Asset != Resource != ResourceUnit
- Booking != Loan
- Actor != Beneficiary
- agreement/consent != qualification/instruction
- PostgreSQL remains transactional truth
- conflict checking remains transaction-safe
- [start,end) semantics remain
- IANA timezone/DST correctness remains
- full grant profiles remain
- authorization remains server-side
- scanner Identifier architecture remains
- public/private information boundaries remain

UX simplification must NOT weaken these guarantees.


# 19. Scope discipline

This correction pass happens BEFORE wider team review.

Implement the changes needed to make the existing Phase-6 application
understandable enough for that review.

Do NOT start Phase 7.

Do not implement speculative future features merely because they appear in
navigation concepts.

Where an owner request clearly belongs to a later planned phase but is necessary
for understanding the current UX, provide the smallest appropriate groundwork
or document it for the owner rather than silently expanding scope.


# 20. Tests

Update/add tests for all changed behaviour.

Especially preserve coverage for:

- booking conflicts
- timezone/DST semantics
- permissions
- group scoping
- public/private data
- availability
- checkout/return
- responsive critical workflows where existing browser tests apply

Add tests for newly exposed administration workflows where applicable.

Also test resource-specific requirement behaviour, including:

- current agreement version already accepted -> no repeated prompt
- changed agreement version -> new acceptance required
- historical acceptance retained
- missing mandatory agreement blocks protected action
- missing qualification blocks protected action
- user cannot self-grant a qualification
- agreement-only resource
- qualification-only resource
- resource requiring both
- resource requiring neither
- server-side/API path cannot bypass requirements


# 21. NCtest update

After implementation and green CI:

Update the existing isolated NCtest review deployment.

Preserve the review deployment architecture.

Because this is still a disposable test instance, database migration is
acceptable.

Do NOT delete team-entered review data unless migration requires it.

If reseeding/reset is genuinely required, explain why and STOP for owner
approval before destroying the current review state.


# 22. Review dataset

Where useful, update the fictional review dataset so the new UX can actually be
tested.

In particular, provide representative examples such as:

    Besprechungsraum
        no agreement
        no qualification

    3D-Drucker
        current usage agreement
        required instruction/qualification

    CNC-Fräse
        required instruction/qualification

    Lastenrad
        current usage agreement

    Akkuschrauber pool
        no unnecessary agreement

Use only fictional review users and data.

Create at least:

- one user who already satisfies the 3D printer requirements
- one user who accepted an older agreement version
- one user missing the qualification
- one user with no requirements satisfied

This should make the different booking states testable immediately.

Do not add artificial requirements merely to make every resource complicated.


# 23. Documentation

Update the handbook for all changed user-facing workflows.

The handbook should explain the human concepts, not require users to understand
the internal Django/domain model.

Update relevant sections for:

- catalogue
- booking
- availability/calendar
- inventory/resource administration
- categories
- locations
- opening hours
- users
- groups
- agreements
- qualifications/instructions
- checkout/return where affected
- dashboard/navigation

Update the terminology review document after implementing the approved UX
changes.

Clearly distinguish remaining owner decisions from already resolved terms.


# 24. Handover

When finished, provide:

1. commit
2. CI status/test count
3. NCtest deployment status
4. concise list of UX changes
5. terminology changes
6. navigation changes
7. booking/calendar changes
8. category/group/user administration changes
9. opening-hours implementation/status
10. agreement/qualification implementation and booking behaviour
11. account presentation of agreements/qualifications
12. anything deliberately deferred
13. any owner decisions still required
14. any domain-model gap discovered for distinct vs interchangeable units
15. any architecture/domain-model gap discovered while implementing
    resource-specific agreements or qualifications

Then STOP.

Do not start Phase 7.

The next step is the actual WERK/Zircula TEAM UX REVIEW.