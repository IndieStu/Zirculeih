# Owner UX correction verification

Application `218f712e03602194ee8f3846ff94c3205d6f4e66`.
CI and full local regression: 219 tests passed; see [handover](HANDOVER.md).

NCtest browser checks use only fictional accounts and existing credentials:

- Existing Admin sign-in succeeded without changing its password.
- Group creation form is accessible from Organisation → Gruppen.
- Dashboard contains real due/overdue, pickup, booking and attention records.
- Resource catalogue shows three distinct named Prusa models and current occupancy.
- A free Prusa calendar period opens the form with Von/Bis prefilled.
- The normal form has no visible DST ambiguity controls.
- Missing qualification is reported separately from the current agreement checkbox.
- Current-version agreement text is available on demand; no self-qualification checkbox.
- Account overview lists relevant qualification/agreement state.
- Operating-calendar administration and category links are reachable.

Only read-only navigation was used for these NCtest browser checks. No existing team
booking, loan, agreement acceptance or profile was edited. Automated tests separately
exercise writes, authorization, all requirement combinations, version changes,
immutable evidence, concurrent allocation, checkout and return.

[Dashboard screenshot](../screenshots/ux-correction-dashboard.png).
Final browser screenshots and responsive measurements are recorded below. These
checks do not constitute
team UX acceptance or a full accessibility audit.

Final deployed checks:

- Build marker `218f712e03602194ee8f3846ff94c3205d6f4e66` verified in the browser.
- A previously opened browser now loads the versioned stylesheet and renders the
  desktop operational shell as a CSS grid/sidebar without cache-clearing steps.
- Fresh Admin login lands on `/inventar/uebersicht/` (Dashboard).
- At 320px, booking document width equals viewport width (320px); navigation
  collapses and the date/time controls remain accessible.
- Operating-calendar overview shows at most 30 weekly rows; selecting Prusa MK4
  filters to its 21 weekly windows. No existing time window was edited or deleted.
- Temporary browser sessions were logged out and closed; local test servers stopped.

[Booking form](../screenshots/ux-correction-booking.png),
[320px booking form](../screenshots/ux-correction-booking-mobile.png),
[filtered operating calendar](../screenshots/ux-correction-hours.png).

## Superseding calendar correction — 2026-10-16

The previous daily free-period presentation was rejected and replaced. Application
`c0135156a74e0927988dab0ebf3daca6d34d1171`; CI 38913523571 green, 232 passed
156.51s; local 232 passed 82.55s. Earlier 219-test evidence above is historical.

Actual local and deployed NCtest browser checks:

- Month first; selecting 21 October opens the day; 22 October closure disabled.
- Room 11–12 and 14–15 booked; transitions distinctly shown on both sides.
- Timeline clicks select 15:30 then 17:30; accessible controls update the same
  overlay. At 15:30, selectable ends stop at 19:30 (four-hour maximum).
- 320px viewport: document width 320px; Von/Bis selection remains usable.
- CNC 15–16 booked, 17–18 maintenance block, transitions constrain remaining time.
- Prusa MK4 12–13 booked, 13–13:30 transition. 13:30–14:30 carries correctly to
  the booking form, which shows missing staff qualification separately from
  current agreement acceptance. No consent or booking was submitted.
- Separate day-mode cargo bike: 22–28 October valid; entering 29 October produces
  immediate maximum-seven-days feedback and disables Reservieren. Month navigation
  retains the date selection (local browser check).
- Anonymous room calendar exposes occupancy only, no email/internal claim/timezone
  labels. Existing authenticated review session logged out; temporary tab closed.
- Migration and additive scenario command succeeded on NCtest; rerun made no changes.
- All prior IDs/password digests preserved; every existing Booking/Claim/Loan/
  LoanLine/Acceptance field unchanged; both existing media files byte-identical.

[Month](../screenshots/calendar-month.png), [day](../screenshots/calendar-day.png),
[timeline selection](../screenshots/calendar-timeline.png),
[320px](../screenshots/calendar-mobile.png), [days](../screenshots/calendar-days.png).
These are operator checks, not owner/team acceptance or a comprehensive WCAG audit.
