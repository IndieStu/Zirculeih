from .models import Booking
from .services import flag_incidents


def asset_changed(asset_id):
    flag_incidents(
        Booking.objects.filter(unit__asset_id=asset_id, status__in=["confirmed", "active"]),
        "asset_changed",
    )


def resource_changed(resource_id):
    flag_incidents(
        Booking.objects.filter(resource_id=resource_id, status__in=["confirmed", "active"]),
        "resource_changed",
    )
