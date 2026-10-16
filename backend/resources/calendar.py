"""Bounded public occupancy, with no booking identities or personal eligibility."""

from datetime import datetime, time, timedelta
from urllib.parse import urlencode

from bookings import schedules
from bookings.models import BookingPolicy, ScheduleException, ScheduleWindow
from bookings.services import capacity_units
from bookings.time_rules import local_instant, zone
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone


def calendar(resource, selected=None):
    policy = BookingPolicy.objects.filter(resource=resource).first()
    if not resource.booking_enabled or policy is None:
        return None
    now = timezone.now()
    today = now.astimezone(zone(policy.timezone)).date()
    try:
        day = datetime.strptime(selected or "", "%Y-%m-%d").date()
    except ValueError:
        day = today
    day = max(today, min(day, today + timedelta(days=policy.max_horizon_days)))
    owner = schedules.owner_filter(resource, calendar=True)
    windows = list(ScheduleWindow.objects.filter(owner))
    exceptions = list(
        ScheduleException.objects.filter(
            owner, date__gte=day - timedelta(days=1), date__lte=day + timedelta(days=1)
        )
    )
    rows = []
    granularity = policy.granularity_minutes
    step = ((29 // granularity) + 1) * granularity
    duration = ((policy.min_duration_minutes - 1) // granularity + 1) * granularity
    starts = [0] if policy.time_mode == "days" else range(0, 1440, step)
    for minute in starts:
        local = datetime.combine(day, time()) + timedelta(minutes=minute)
        local_end = (
            local + timedelta(days=policy.min_days)
            if policy.time_mode == "days"
            else local + timedelta(minutes=duration)
        )
        try:
            start = local_instant(local, policy.timezone)
            end = local_instant(local_end, policy.timezone)
        except ValidationError:
            # An ambiguous hour is selected explicitly in the normal form.
            continue
        status = "Frei"
        if start < now + timedelta(minutes=policy.lead_minutes):
            status = "Vergangen"
        elif policy.use_mode == "onsite" and not all(
            schedules.covers(
                resource,
                policy,
                purpose,
                start,
                end,
                window_rows=windows,
                exception_rows=exceptions,
            )
            for purpose in ("usage", "access")
        ):
            status = "Geschlossen"
        elif not capacity_units(resource, policy, start, end):
            status = "Belegt / gesperrt"
        params = {
            "start": local.isoformat(timespec="minutes"),
            "end": local_end.isoformat(timespec="minutes"),
        }
        if policy.time_mode == "days":
            params = {
                "start": day.isoformat(),
                "end": (local_end.date() - timedelta(days=1)).isoformat(),
            }
        rows.append(
            {
                "label": "Ganzer Tag"
                if policy.time_mode == "days"
                else f"{local:%H:%M}–{local_end:%H:%M}",
                "status": status,
                "free": status == "Frei",
                "url": reverse("booking_create", args=[resource.pk]) + "?" + urlencode(params),
            }
        )
    return {
        "day": day,
        "today": today,
        "previous": day - timedelta(days=1),
        "next": day + timedelta(days=1),
        "rows": [r for r in rows if r["status"] not in {"Geschlossen", "Vergangen"}],
        "timezone": policy.timezone,
        "physical": policy.use_mode == "physical_loan",
    }


def current_status(resource):
    policy = BookingPolicy.objects.filter(resource=resource).first()
    if not resource.booking_enabled or policy is None:
        return "Nicht online buchbar"
    start = timezone.now()
    end = start + timedelta(minutes=1)
    if policy.use_mode == "onsite" and not all(
        schedules.covers(resource, policy, purpose, start, end) for purpose in ("usage", "access")
    ):
        return "Zurzeit geschlossen"
    return (
        "Zurzeit frei"
        if capacity_units(resource, policy, start, end)
        else "Zurzeit belegt / gesperrt"
    )
