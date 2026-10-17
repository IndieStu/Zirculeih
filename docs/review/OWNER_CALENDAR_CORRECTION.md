# Correction: replace current availability UI with a real calendar workflow

STOP the current availability/calendar implementation direction.

The current availability UI with many individual cards such as:

    14:30–14:45 · Frei
    15:00–15:15 · Frei
    15:30–15:45 · Frei

is not usable and is NOT the intended Deelvo calendar.

Do not iterate on this grid.

Replace it with the following interaction model.


# 1. Calendar starts with a MONTH VIEW

The primary availability interface should begin with a normal visual monthly
calendar.

For example:

    Oktober 2026

    Mo  Di  Mi  Do  Fr  Sa  So
                 1   2   3   4
     5   6   7   8   9  10  11
    12  13  14  15 [16] 17  18
    19  20  21  22  23  24  25
    ...

Users should be able to:

- navigate to previous/next month where booking policy permits
- select a calendar day
- immediately understand days that cannot be booked
- see a useful indication if a day is completely unavailable
- then inspect the selected day's detailed availability

Do NOT render every possible booking interval in the month view.

The month view is for selecting a DATE.


# 2. Selecting a day opens DAY AVAILABILITY

After selecting a date, show that day's actual availability as a visual
timeline.

For example conceptually:

    Freitag, 16. Oktober

    08:00
    09:00
    10:00   █████ booked
    11:00   █████ booked
    12:00
    13:00
    14:00   ┌───────────────┐
    15:00   │ selected      │
    16:00   └───────────────┘
    17:00
    18:00   █████ booked
    19:00   █████ booked
    20:00

The exact visual design is up to the implementation.

It must however be a real visual representation of the day's timeline.

The user must be able to distinguish:

- available time
- existing bookings
- transition/buffer time
- closed/unavailable time
- blocks/maintenance where applicable
- currently selected booking period

Do NOT represent availability as dozens of separate "Frei" cards.


# 3. User selects START and END

The interaction should allow a user to select a desired continuous period.

Example:

    14:00 – 16:00

The selection may be performed by:

- clicking/tapping start and end
- selecting a free area and adjusting start/end
- accessible start/end controls associated with the timeline

Dragging may be offered as an enhancement, but must not be the only interaction.

The result should simply be understandable as:

    Gewählter Zeitraum
    14:00 – 16:00

Then:

    Reservieren

or the appropriate next action.


# 4. Booking grid is an INTERNAL CONSTRAINT, not the calendar

A Resource may still define a booking grid such as:

    15 minutes
    30 minutes
    60 minutes

This may constrain valid start/end selections.

But it must NOT result in UI cards representing every grid interval.

For example:

    grid = 30 minutes

means valid selections could be:

    14:00–15:00
    14:00–15:30
    14:00–16:00

It does NOT mean showing:

    14:00–14:30 free
    14:30–15:00 free
    15:00–15:30 free
    15:30–16:00 free

as separate booking options.


# 5. Configurable maximum booking duration

Every bookable Resource must have a configurable maximum booking duration.

This must be configurable during Resource/bookable-item administration.

Examples:

    Besprechungsraum
        maximum booking duration: 4 hours

    3D-Drucker
        maximum booking duration: 8 hours

    CNC-Fräse
        maximum booking duration: 3 hours

    Lastenrad
        maximum booking duration: 7 days

Use the existing policy/domain model where this capability already exists.
Do not create a duplicate setting if max duration is already represented.

The calendar/selection UI must enforce the configured maximum.

Example:

    max duration = 2 hours

User selects:

    14:00 start

The latest selectable end is:

    16:00

Do not let the user select an invalid period and only discover the basic
duration rule after submitting the booking.


# 6. Minimum 30-minute transition between ROOM bookings

For rooms, there must be at least:

    30 minutes

between consecutive bookings.

Example:

Existing booking:

    10:00–12:00

Then the next booking may begin no earlier than:

    12:30

Likewise, a new booking ending before an existing booking must leave the
required transition period.

This transition/buffer must be included in conflict and availability
calculation, not merely drawn in the UI.


# 7. Minimum 30-minute transition between MACHINE bookings

Machines must likewise have at least:

    30 minutes

transition/buffer time between consecutive bookings.

Example:

    CNC booking:
    14:00–16:00

The next machine booking may begin no earlier than:

    16:30

The buffer may represent setup, cleanup, checking, preparation or handover.

It must block availability even though it is not itself another user's booking.


# 8. Make transition time configurable, with 30 minutes as the required default

Do not hardcode this solely into the frontend.

Use the existing booking-policy/buffer architecture where possible.

For rooms and machines:

    default transition/buffer = 30 minutes

An authorized administrator should be able to configure the value for the
Resource where appropriate.

Examples:

    Besprechungsraum
        transition: 30 minutes

    CNC
        transition: 45 minutes

    simple machine
        transition: 30 minutes

The default for rooms and machines must be at least the owner-requested
30-minute configuration in the review dataset.

The booking engine remains the authoritative enforcement point.


# 9. Visualize buffers differently from bookings

A user should not mistake transition time for another person's booking.

The day view should visually distinguish:

    BOOKED
    BUFFER / transition
    CLOSED / unavailable
    AVAILABLE

The exact visual style is up to Deelvo.

Do not expose technical terms such as AllocationClaim.

A simple presentation might communicate:

    Belegt
    Übergangszeit
    Nicht verfügbar

Do not show personal information belonging to the person who made another
booking.


# 10. Opening hours constrain the calendar

The month/day calendar must respect the configured operating rules.

For example, if the resource can be used:

    Wednesday-Friday
    11:00-20:00

then Tuesday should not present ordinary selectable time.

Friday's day view should only make the permitted period selectable.

Closures, holidays and temporary blocks must likewise affect the visual
availability.

Do not generate "free" periods outside allowed usage time.


# 11. Different resource types may need different calendar behaviour

The month -> day timeline interaction described above is the primary model for:

- rooms
- machines
- other time-slot resources

Do not force an hourly timeline onto resources whose natural booking unit is
multiple days.

For example:

    Lastenrad
    Powerstation
    event equipment

may use the month calendar to select:

    start date -> end date

where the configured booking mode is date-range/day based.

Preserve Deelvo's existing booking modes.

Do not reduce everything to the room/machine model.


# 12. Remove the current unnecessary data/privacy explanation

Remove permanent text such as:

    "Belegung ohne persönliche Daten. Berechtigung, Abholung und Rückgabe
    werden beim Reservieren geprüft."

This information does not need to appear in the ordinary availability UI.

The calendar should simply show occupancy without exposing personal data.

That is expected behaviour, not something that needs a permanent disclaimer.


# 13. Do not show personal booking data

Existing bookings shown in the public/user-facing availability calendar should
normally reveal only the occupancy state.

For example:

    Belegt

NOT:

    Gebucht von Max Mustermann
    Workshop von Gruppe XYZ
    user@example.org

unless a separate authorized operational view intentionally provides additional
information.

The normal availability calendar needs to answer:

    Can I use this resource at this time?

not:

    Who is using it?


# 14. Remove unnecessary timezone presentation

Do not permanently display:

    Europe/Berlin

next to every selected date.

Deelvo must continue to use its correct IANA timezone internally.

Only surface timezone information where it is genuinely relevant.

DST correctness remains mandatory but must not clutter ordinary calendar use.


# 15. Booking requirements come AFTER period selection where appropriate

The normal user flow should become:

    Resource
        ↓
    Month calendar
        ↓
    Select day
        ↓
    See day availability
        ↓
    Select 14:00–16:00
        ↓
    Check booking requirements
        ↓
    Show only missing requirements
        ↓
    Confirm booking

For example, only after the user has selected a valid period does Deelvo need
to show:

    Nutzungsbestätigung 3D-Drucker erforderlich

if the current version has not already been accepted.

Do not surround the calendar with permanent explanations of every possible
requirement.


# 16. Immediate feedback

The user should receive immediate understandable feedback while selecting.

Examples:

If the selected period exceeds max duration:

    Maximal 2 Stunden buchbar.

If transition time makes 16:00 unavailable:

    Wegen einer vorherigen Buchung ab 16:30 verfügbar.

If the resource is closed:

    An diesem Tag nicht verfügbar.

If an existing booking conflicts:

    Dieser Zeitraum ist bereits belegt.

Keep messages short and contextual.


# 17. Manual time input may remain as an accessible alternative

A compact alternative may exist:

    Von    [14:00]
    Bis    [16:00]

This is useful for:

- keyboard users
- accessibility
- precise adjustment

But it must remain synchronized with the visual timeline.

It must NOT become the primary replacement for the calendar.


# 18. Administration

In Resource/bookable-item administration, make the relevant booking settings
easy to find together.

For example:

    Buchung

    Buchungsart
        Zeitfenster

    Zeitraster
        30 Minuten

    Mindestdauer
        30 Minuten

    Maximale Dauer
        4 Stunden

    Übergangszeit
        30 Minuten

    Nutzungszeiten
        [configured schedule]

Use existing domain concepts and models where they already exist.

Do not create parallel settings merely for this screen.


# 19. Preserve booking-engine guarantees

This is a UX correction plus exposure of appropriate existing policy settings.

Do NOT weaken:

- PostgreSQL conflict protection
- AllocationClaim semantics
- [start,end) intervals
- buffers
- opening/usage windows
- hard blocks
- maintenance blocks
- authorization
- qualification requirements
- agreement requirements
- transaction-safe unit allocation
- concurrency protection
- IANA timezone/DST correctness

The visual calendar must represent the booking engine's truth.

Do not implement a frontend-only availability model.


# 20. Test cases

Add/update tests for at least:

- month navigation
- day selection
- occupied periods visible
- no personal booking data leaked
- valid continuous period selection
- max duration enforced
- 30-minute room buffer enforced
- 30-minute machine buffer enforced
- configurable buffer respected
- buffer represented as unavailable
- closed days unavailable
- opening hours respected
- hard block reflected
- existing booking reflected
- booking grid constrains selection without generating free-slot cards
- manual start/end remains synchronized
- DST edge cases remain correct
- concurrent booking protection remains correct
- mobile interaction remains usable


# 21. Review dataset

Update the NCtest review dataset so this can be meaningfully tested.

Include examples such as:

Besprechungsraum:
    opening/use window with meaningful hours
    max booking duration: 4 hours
    transition: 30 minutes
    at least two existing bookings on one review day

3D-Drucker:
    max booking duration: meaningful test value
    transition: 30 minutes
    existing booking so free/busy/buffer states are visible

CNC:
    max booking duration
    transition: at least 30 minutes
    existing booking

Also include at least:

- one closed day
- one temporary blocked period

so the calendar states can actually be reviewed.


# 22. NCtest

After implementation and green tests, update the existing isolated NCtest
review deployment.

Do not destroy team-entered review data without owner approval.

If the existing review seed data can be safely extended, do so.

If a destructive reset is required, STOP and ask first.


# 23. Acceptance criterion

This correction is NOT complete merely because a user can technically create a
booking.

It is complete when a normal user can open a resource and answer visually:

    Which days can I book?
    What is already occupied?
    When is this resource free on the selected day?
    What continuous period do I want?
    How long am I allowed to book it?

without understanding:

- booking grids
- AllocationClaims
- IANA timezone names
- DST internals
- internal permission evaluation
- privacy implementation details

The calendar should feel like choosing a time, not querying a scheduling
database.

After implementing this correction, run the full regression suite, deploy the
updated review build to NCtest, report the result, and STOP for owner review.

Do not start Phase 7.