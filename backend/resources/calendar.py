"""Month/date selection and day timelines from shared booking-engine truth."""

import calendar as month_calendar
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from accounts.authorization import _grants_allow
from bookings.models import BookingPolicy
from bookings.time_rules import interval, local_instant, zone
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from .bundle_calendar import occupancy as Occupancy

LABELS = {
    "available": "Frei",
    "booked": "Belegt",
    "transition": "Übergangszeit",
    "closed": "Nicht verfügbar",
    "blocked": "Gesperrt / Wartung",
}
MONTHS = [
    "",
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def midnight(day, policy):
    return local_instant(datetime.combine(day, time()), policy.timezone)


def parse_date(raw, default=None):
    try:
        return date.fromisoformat(raw or "")
    except (ValueError, TypeError):
        return default


def validate_period(snapshot, start, end, *, start_fold=None, end_fold=None):
    p = snapshot.policy
    try:
        s, e, minutes, ds, de = interval(p, start, end, start_fold=start_fold, end_fold=end_fold)
    except ValidationError as exc:
        return str(exc.messages[0])
    horizon = (
        s.astimezone(zone(p.timezone)).date() - snapshot.now.astimezone(zone(p.timezone)).date()
    ).days
    if (
        e <= s
        or s < snapshot.now + timedelta(minutes=p.lead_minutes)
        or horizon > p.max_horizon_days
    ):
        return "Dieser Zeitraum ist nicht buchbar."
    if p.time_mode == "days":
        if not p.min_days <= (de - ds).days <= p.max_days:
            return f"Zwischen {p.min_days} und {p.max_days} Tagen buchbar."
        for purpose, day in (("pickup", ds), ("return", de - timedelta(days=1))):
            if not appointment_day(snapshot, day, purpose):
                return "An diesem Tag ist kein passender Abhol- oder Rückgabetermin möglich."
        if ds == de - timedelta(days=1) and min(appointment_points(snapshot, ds, "pickup")) >= max(
            appointment_points(snapshot, ds, "return")
        ):
            return "Abholung und Rückgabe passen an diesem Tag nicht zusammen."
    else:
        if not p.min_duration_minutes <= minutes <= p.max_duration_minutes:
            return f"Maximal {duration_label(p.max_duration_minutes)} buchbar."
        if any(
            t.second or t.microsecond or (t.hour * 60 + t.minute) % p.granularity_minutes
            for t in (s.astimezone(zone(p.timezone)), e.astimezone(zone(p.timezone)))
        ):
            return "Bitte eine passende Start- und Endzeit wählen."
        if p.use_mode == "physical_loan":
            pickups: list[datetime] = []
            returns: list[datetime] = []
            day = s.astimezone(zone(p.timezone)).date()
            last = e.astimezone(zone(p.timezone)).date()
            while day <= last:
                pickups.extend(t for t in appointment_points(snapshot, day, "pickup") if s <= t < e)
                returns.extend(t for t in appointment_points(snapshot, day, "return") if s < t <= e)
                day += timedelta(days=1)
            if not pickups or not returns or min(pickups) >= max(returns):
                return "In diesem Zeitraum sind keine passenden Abhol- und Rückgabetermine möglich."
        else:
            if not snapshot.covers("usage", s, e) or not snapshot.covers("access", s, e):
                return "An diesem Tag oder zu dieser Uhrzeit nicht verfügbar."
            if not _grants_allow(
                snapshot.unstaffed_grants, snapshot.scope, horizon, minutes
            ) and not snapshot.covers("opening", s, e):
                return "Außerhalb der betreuten Öffnung nicht verfügbar."
    if not snapshot.free_units(s, e):
        return "Dieser Zeitraum ist belegt oder benötigt zusätzliche Übergangszeit."
    for child in getattr(snapshot, "children", ()):
        if validate_period(child, start, end, start_fold=start_fold, end_fold=end_fold):
            return "Eine benötigte Komponente ist in diesem Zeitraum nicht verfügbar."
    return None


def appointment_points(snapshot, day, purpose):
    cache = getattr(snapshot, "appointment_days", {})
    snapshot.appointment_days = cache
    key = (day, purpose)
    if key not in cache:
        p = snapshot.policy
        lo = midnight(day, p)
        hi = midnight(day + timedelta(days=1), p)
        cache[key] = [
            t
            for t in time_points(p, lo, hi, include_end=False)
            if snapshot.covers(purpose, t, t + timedelta(microseconds=1))
            and snapshot.covers("access", t, t + timedelta(microseconds=1))
        ]
    return cache[key]


def appointment_day(snapshot, day, purpose):
    return bool(appointment_points(snapshot, day, purpose))


def duration_label(minutes):
    if minutes % 1440 == 0:
        return f"{minutes // 1440} Tag" + ("e" if minutes != 1440 else "")
    if minutes % 60 == 0:
        return f"{minutes // 60} Stunde" + ("n" if minutes != 60 else "")
    return f"{minutes} Minuten"


def time_points(policy, start, end, *, include_end=True):
    # Iterate real instants: spring skips nonexistent wall time; autumn keeps both folds.
    point = start
    while point < end or (include_end and point == end):
        local = point.astimezone(zone(policy.timezone))
        if (local.hour * 60 + local.minute) % policy.granularity_minutes == 0:
            yield point
        point += timedelta(minutes=1)


def day_options(snapshot, day, *, all_ends=False):
    p = snapshot.policy
    lo = midnight(day, p)
    hi = midnight(day + timedelta(days=1), p)
    points = list(time_points(p, lo, hi))
    starts = []
    ends = {}
    for i, s in enumerate(points[:-1]):
        if snapshot.state(s, s + timedelta(minutes=p.min_duration_minutes)) != "available":
            continue
        valid = []
        for e in points[i + 1 :]:
            minutes = (e - s).total_seconds() / 60
            if minutes < p.min_duration_minutes:
                continue
            if minutes > p.max_duration_minutes:
                break
            if (
                validate_period(
                    snapshot,
                    s.astimezone(zone(p.timezone)).replace(tzinfo=None),
                    e.astimezone(zone(p.timezone)).replace(tzinfo=None),
                    start_fold=s.astimezone(zone(p.timezone)).fold,
                    end_fold=e.astimezone(zone(p.timezone)).fold,
                )
                is None
            ):
                valid.append(int(e.timestamp() * 1000))
                if not all_ends:
                    return True
        if valid:
            starts.append(int(s.timestamp() * 1000))
            ends[str(int(s.timestamp() * 1000))] = valid
    if not all_ends:
        return False
    rendered = []
    local_counts: dict[str, int] = {}
    for point in points:
        label = point.astimezone(zone(p.timezone)).strftime("%H:%M")
        local_counts[label] = local_counts.get(label, 0) + 1
    for point in points:
        local = point.astimezone(zone(p.timezone))
        label = local.strftime("%H:%M")
        if point == hi:
            label = "24:00"
        elif local_counts[label] > 1:
            label += " (später)" if local.fold else " (früher)"
        rendered.append(
            {
                "value": int(point.timestamp() * 1000),
                "label": label,
                "local": local.replace(tzinfo=None).isoformat(timespec="minutes"),
                "fold": local.fold,
            }
        )
    return {"points": rendered, "starts": starts, "ends": ends}


def calendar(resource, selected=None, *, month=None, actor=None, query=None):
    p = BookingPolicy.objects.filter(resource=resource).first()
    if not resource.booking_enabled or p is None:
        return None
    loan_slots = p.use_mode == "physical_loan" and p.time_mode == "slots"
    today = timezone.now().astimezone(zone(p.timezone)).date()
    latest = today + timedelta(days=p.max_horizon_days)
    day = parse_date(selected)
    day = day if day and today <= day <= latest else None
    first = parse_date((month or "") + "-01", day or today).replace(day=1)
    first = max(today.replace(day=1), min(first, latest.replace(day=1)))
    next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    previous = (first - timedelta(days=1)).replace(day=1)
    requested = parse_date((query or {}).get("start")) if p.time_mode == "days" else None
    requested = requested if requested and today <= requested <= latest else None
    snapshot = Occupancy(
        resource,
        p,
        midnight(min(first, day or first, requested or first), p),
        midnight(next_month + timedelta(days=p.max_days + 1), p),
        actor,
    )
    weeks = []
    for week in month_calendar.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month):
        cells = []
        for d in week:
            bookable = False
            if d.month == first.month and today <= d <= latest:
                if p.time_mode == "days":
                    bookable = (
                        validate_period(snapshot, d, d + timedelta(days=p.min_days - 1)) is None
                    )
                elif loan_slots:
                    bookable = any(
                        t >= snapshot.now + timedelta(minutes=p.lead_minutes)
                        and snapshot.free_units(t, t + timedelta(minutes=p.min_duration_minutes))
                        for t in appointment_points(snapshot, d, "pickup")
                    )
                else:
                    bookable = day_options(snapshot, d)
            cells.append(
                {
                    "date": d,
                    "number": d.day,
                    "inside": d.month == first.month,
                    "bookable": bookable,
                    "selected": d == day,
                    "today": d == today,
                    "url": "?"
                    + urlencode({"month": first.strftime("%Y-%m"), "day": d.isoformat()})
                    + (
                        "#resource-calendar"
                        if p.time_mode == "days"
                        else "#calendar-selection"
                        if loan_slots
                        else "#day-availability"
                    ),
                }
            )
        weeks.append(cells)
    data = {
        "mode": "loan-slots" if loan_slots else p.time_mode,
        "minDate": today.isoformat(),
        "maxStartDate": latest.isoformat(),
        "day": day.isoformat() if day else None,
        "maxMinutes": p.max_duration_minutes,
        "maxDays": p.max_days,
        "minDays": p.min_days,
        "action": reverse("calendar_select", args=[resource.slug]),
        "ticks": [],
        "points": [],
        "starts": [],
        "ends": {},
        "segments": [],
    }
    segments = []
    if loan_slots and day:
        first_pickup = next(
            (
                t
                for t in appointment_points(snapshot, day, "pickup")
                if t >= snapshot.now + timedelta(minutes=p.lead_minutes)
                and snapshot.free_units(t, t + timedelta(minutes=p.min_duration_minutes))
            ),
            None,
        )
        if first_pickup:
            data["initialStart"] = (
                first_pickup.astimezone(zone(p.timezone))
                .replace(tzinfo=None)
                .isoformat(timespec="minutes")
            )
    if day and p.time_mode != "days" and not loan_slots:
        lo = midnight(day, p)
        hi = midnight(day + timedelta(days=1), p)
        data.update(day_options(snapshot, day, all_ends=True))
        data.update(dayStart=int(lo.timestamp() * 1000), dayEnd=int(hi.timestamp() * 1000))
        raw_segments = snapshot.segments(lo, hi)
        useful = [(s, e) for s, e, state in raw_segments if state != "closed"]
        view_lo, view_hi = lo, hi
        if useful:
            first_minute = int((useful[0][0] - lo).total_seconds() // 3600)
            last_minute = int((useful[-1][1] - lo).total_seconds() / 3600 + 0.999999)
            view_lo = max(lo, lo + timedelta(hours=first_minute - 1))
            view_hi = min(hi, lo + timedelta(hours=last_minute + 1))
        data.update(
            viewStart=int(view_lo.timestamp() * 1000), viewEnd=int(view_hi.timestamp() * 1000)
        )
        tick = view_lo
        while tick <= view_hi:
            data["ticks"].append(
                {
                    "top": (tick - view_lo).total_seconds()
                    / (view_hi - view_lo).total_seconds()
                    * 100,
                    "label": tick.astimezone(zone(p.timezone)).strftime("%H:%M")
                    if tick < hi
                    else "24:00",
                }
            )
            tick += timedelta(hours=1)
        for s, e, state in raw_segments:
            if e <= view_lo or s >= view_hi:
                continue
            s = max(s, view_lo)
            e = min(e, view_hi)
            label = (
                f"{s.astimezone(zone(p.timezone)):%H:%M}–"
                f"{e.astimezone(zone(p.timezone)):%H:%M} · {LABELS[state]}"
            )
            row = {
                "start": int(s.timestamp() * 1000),
                "end": int(e.timestamp() * 1000),
                "state": state,
                "label": label,
                "top": (s - view_lo).total_seconds() / (view_hi - view_lo).total_seconds() * 100,
                "height": (e - s).total_seconds() / (view_hi - view_lo).total_seconds() * 100,
            }
            segments.append(row)
            data["segments"].append(row)
    if p.time_mode == "days":
        data["dateEnds"] = {}
        requested = parse_date((query or {}).get("start"))
        starts = {c["date"] for w in weeks for c in w if c["bookable"]}
        if requested and today <= requested <= latest:
            starts.add(requested)
        for s in starts:
            data["dateEnds"][s.isoformat()] = [
                e.isoformat()
                for i in range(p.min_days, p.max_days + 1)
                if validate_period(snapshot, s, (e := s + timedelta(days=i - 1))) is None
            ]
    return {
        "weeks": weeks,
        "month": first,
        "month_label": f"{MONTHS[first.month]} {first.year}",
        "previous_month": previous.strftime("%Y-%m") if previous >= today.replace(day=1) else None,
        "next_month": next_month.strftime("%Y-%m") if next_month <= latest.replace(day=1) else None,
        "day": day,
        "days_mode": p.time_mode == "days",
        "loan_slots": loan_slots,
        "step_seconds": p.granularity_minutes * 60,
        "segments": segments,
        "data": data,
        "duration": f"{p.max_days} Tage"
        if p.time_mode == "days"
        else duration_label(p.max_duration_minutes),
        "snapshot": snapshot,
    }


def current_status(resource):
    from bookings import schedules
    from bookings.services import capacity_units
    from lending.models import LoanLine

    p = BookingPolicy.objects.filter(resource=resource).first()
    if not resource.booking_enabled or p is None:
        return "Nicht online buchbar"
    s = timezone.now()
    e = s + timedelta(minutes=1)
    if p.use_mode == "onsite" and not all(
        schedules.covers(resource, p, purpose, s, e) for purpose in ("usage", "access")
    ):
        return "Zurzeit geschlossen"
    if resource.bundle_components.exists():
        from .bundles import expansion

        try:
            for component, _required in expansion(resource)[1:]:
                if component.visibility != "public":
                    return "Verfügbarkeit im Kalender prüfen"
                from .services import active_context

                if (
                    component.archived_at
                    or not component.published_at
                    or not active_context(component)
                ):
                    return "Zurzeit belegt / gesperrt"
                cp = BookingPolicy.objects.filter(resource=component).first()
                if cp is None or not component.booking_enabled:
                    return "Zurzeit belegt / gesperrt"
                if cp.use_mode == "onsite" and not all(
                    schedules.covers(component, cp, purpose, s, e)
                    for purpose in ("usage", "access")
                ):
                    return "Zurzeit geschlossen"
                cu = capacity_units(component, cp, s, e)
                held = set(
                    LoanLine.objects.filter(unit__in=cu, returned_at__isnull=True).values_list(
                        "unit_id", flat=True
                    )
                )
                if not cu or all(u.pk in held for u in cu):
                    return "Zurzeit belegt / gesperrt"
        except ValidationError:
            return "Zurzeit belegt / gesperrt"
    units = capacity_units(resource, p, s, e)
    custody = set(
        LoanLine.objects.filter(unit__in=units, returned_at__isnull=True).values_list(
            "unit_id", flat=True
        )
    )
    if units and all(u.pk in custody for u in units):
        return "Zurzeit ausgeliehen"
    return "Zurzeit frei" if units else "Zurzeit belegt / gesperrt"
