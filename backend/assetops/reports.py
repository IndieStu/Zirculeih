"""Minimal aggregates, never a person-level utilization profile."""

from datetime import UTC, datetime, time, timedelta
from typing import Any

from accounts.authorization import allowed
from bookings.services import visible_bookings
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from inventory.services import asset_scope, visible_assets
from lending.models import LoanLine
from lending.services import visible_loans

from .models import MaintenanceTask


def aggregate(actor, start_date, end_date, *, location_id=None, category_id=None, export=False):
    if not 0 <= (end_date - start_date).days <= 365:
        raise ValidationError("Berichtszeitraum: 1–366 Tage.")
    assets = visible_assets(actor).filter(archived_at__isnull=True)
    from inventory.models import Category, Location
    from inventory.services import descendants

    if location_id:
        assets = assets.filter(location_id__in=descendants(Location, location_id))
    if category_id:
        assets = assets.filter(category_id__in=descendants(Category, category_id))
    rows = list(assets)
    if not rows:
        raise PermissionDenied
    if export and any(not allowed(actor, "asset.export", asset_scope(a)) for a in rows):
        raise PermissionDenied
    locations: dict[str, int] = {}
    categories: dict[str, int] = {}
    for asset in rows:
        for mapping, value in [
            (locations, asset.location.breadcrumb),
            (categories, asset.category.breadcrumb),
        ]:
            mapping[value] = mapping.get(value, 0) + 1
    maintenance = MaintenanceTask.objects.filter(
        asset__in=assets, status__in=["planned", "in_progress"]
    )
    tasks = [
        t
        for t in maintenance.select_related("asset__location", "asset__category")
        if allowed(actor, "maintenance.manage", asset_scope(t.asset))
    ]
    tz = timezone.get_current_timezone()
    begin = datetime.combine(start_date, time(), tzinfo=tz)
    end = datetime.combine(end_date + timedelta(days=1), time(), tzinfo=tz)
    bookings = visible_bookings(actor, operational=True, start=begin, end=end).exclude(
        status__in=["cancelled", "rejected", "no_show"]
    )
    if location_id:
        bookings = bookings.filter(resource__location_id__in=descendants(Location, location_id))
    if category_id:
        bookings = bookings.filter(
            resource__categories__in=descendants(Category, category_id)
        ).distinct()
    volumes: dict[str, dict[str, Any]] = {}
    for booking in bookings.select_related("resource"):
        if export:
            from resources.services import resource_scope

            if not allowed(actor, "booking.read_all", resource_scope(booking.resource)):
                raise PermissionDenied
        value = volumes.setdefault(booking.resource.title, {"count": 0, "reserved_hours": 0.0})
        value["count"] += 1
        value["reserved_hours"] += (
            min(booking.end, end).astimezone(UTC) - max(booking.start, begin).astimezone(UTC)
        ).total_seconds() / 3600
    lines = LoanLine.objects.filter(
        loan__in=visible_loans(actor, operational=True), returned_at__isnull=True, asset__in=assets
    )
    return dict(
        asset_count=len(rows),
        by_location=sorted(locations.items()),
        by_category=sorted(categories.items()),
        maintenance_open=len(tasks),
        maintenance_overdue=sum(t.due_date < timezone.localdate() for t in tasks),
        open_loans=lines.count(),
        overdue=lines.filter(expected_return__lt=timezone.now()).count(),
        bookings=sorted(volumes.items()),
    )
