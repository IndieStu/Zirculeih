from collections import defaultdict
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import ScheduleException, ScheduleWindow
from .time_rules import local_instant, zone


def owner_filter(resource, *, calendar=False):
    location_ids = [n.pk for n in resource.location.lineage]
    result = Q(resource=resource) | Q(location_id__in=location_ids)
    if calendar:
        categories = {n.pk for c in resource.categories.all() for n in c.lineage}
        result |= Q(category_id__in=categories) | Q(organization=True)
    return result


def subtract(segments, start, end):
    result = []
    for s, e in segments:
        if e <= start or s >= end:
            result.append((s, e))
        else:
            if s < start:
                result.append((s, start))
            if e > end:
                result.append((end, e))
    return result


def segment(row, day, tz):
    try:
        s = local_instant(datetime.combine(day, row.start_time), tz, 0)
        e = local_instant(
            datetime.combine(day + timedelta(days=bool(row.end_next_day)), row.end_time), tz, 1
        )
        return [(s, e)] if s < e else []
    except ValidationError:
        return []  # Never shift invalid local schedule boundaries.


def covers(resource, policy, purpose, start, end, *, window_rows=None, exception_rows=None):
    """Intersect owner schedules; date exceptions also replace overnight carry-over."""
    tz = zone(policy.timezone)
    first = start.astimezone(tz).date() - timedelta(days=1)
    last = end.astimezone(tz).date()
    windows = (
        list(ScheduleWindow.objects.filter(owner_filter(resource, calendar=True), purpose=purpose))
        if window_rows is None
        else [r for r in window_rows if r.purpose == purpose]
    )
    exceptions = (
        list(
            ScheduleException.objects.filter(
                owner_filter(resource, calendar=True),
                purpose=purpose,
                date__gte=first,
                date__lte=last,
            )
        )
        if exception_rows is None
        else [r for r in exception_rows if r.purpose == purpose and first <= r.date <= last]
    )
    owners: dict[tuple, dict[str, list]] = defaultdict(lambda: {"windows": [], "exceptions": []})
    for kind, rows in (("windows", windows), ("exceptions", exceptions)):
        for row in rows:
            owners[(row.resource_id, row.location_id, row.category_id, row.organization)][
                kind
            ].append(row)
    if not owners or (
        purpose == "usage"
        and not any(rid == resource.pk or cid or org for rid, _, cid, org in owners)
    ):
        return False
    for data in owners.values():
        segments = [] if data["windows"] else [(start, end)]
        day = first
        while day <= last:
            for row in data["windows"]:
                if row.weekday == day.weekday():
                    segments.extend(segment(row, day, policy.timezone))
            day += timedelta(days=1)
        special_days = {row.date for row in data["exceptions"]}
        closed = []
        replacements = []
        for day in special_days:
            lo = local_instant(datetime.combine(day, datetime.min.time()), policy.timezone)
            hi = local_instant(
                datetime.combine(day + timedelta(days=1), datetime.min.time()), policy.timezone
            )
            segments = subtract(segments, lo, hi)
            rows = [r for r in data["exceptions"] if r.date == day]
            if any(r.is_closed for r in rows):
                closed.append((lo, hi))
            else:
                for row in rows:
                    replacements.extend(segment(row, day, policy.timezone))
        segments += replacements
        for lo, hi in closed:
            segments = subtract(segments, lo, hi)
        cursor = start
        for s, e in sorted(segments):
            if s > cursor:
                break
            cursor = max(cursor, e)
            if cursor >= end:
                break
        if cursor < end:
            return False
    return True
