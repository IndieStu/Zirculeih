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
