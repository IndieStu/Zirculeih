from django.core.exceptions import PermissionDenied
from inventory.services import asset_scope
from lending.services import read_loan
from resources.services import resource_scope

from .transport import iso


def check(ceiling, scope):
    if not ceiling.includes(scope):
        raise PermissionDenied


def asset(row, ceiling):
    check(ceiling, asset_scope(row))
    return dict(
        id=str(row.pk),
        inventory_number=row.inventory_number,
        name=row.name,
        condition=row.condition,
        lifecycle=row.lifecycle,
        location_id=str(row.location_id),
        category_id=str(row.category_id),
        revision=row.revision,
    )


def resource(row, ceiling):
    check(ceiling, resource_scope(row))
    return dict(
        id=str(row.pk),
        title=row.title,
        slug=row.slug,
        summary=row.summary,
        location_label=row.location_label,
        resource_type=row.type.key,
        time_mode=row.bookingpolicy.time_mode,
        timezone=row.bookingpolicy.timezone,
        revision=row.revision,
    )


def booking(row, ceiling):
    check(ceiling, resource_scope(row.resource))
    return dict(
        id=str(row.pk),
        resource_id=str(row.resource_id),
        unit_id=str(row.unit_id),
        status=row.status,
        start=iso(row.start),
        end=iso(row.end),
        start_date=iso(row.start_date),
        end_date_exclusive=iso(row.end_date_exclusive),
        timezone=row.timezone,
        revision=row.revision,
    )


def loan(actor, pk, ceiling):
    row = read_loan(actor, pk)
    lines = []
    for line in row.lines.select_related("booking__resource__location"):
        check(ceiling, resource_scope(line.booking.resource))
        lines.append(
            dict(
                id=str(line.pk),
                booking_id=str(line.booking_id),
                resource_id=str(line.booking.resource_id),
                asset_id=str(line.asset_id),
                expected_return=iso(line.expected_return),
                returned_at=iso(line.returned_at),
                revision=line.revision,
            )
        )
    return dict(
        id=str(row.pk), issued_at=iso(row.issued_at), closed_at=iso(row.closed_at), lines=lines
    )
