from datetime import timedelta

from bookings import schedules
from bookings.time_rules import aware_interval
from django.core.exceptions import ValidationError


def appointments(resource, policy, start, end, pickup_at, return_at):
    try:
        aware_interval(pickup_at, return_at)
    except ValidationError:
        return "pickup_unavailable"
    if not start <= pickup_at < return_at <= end:
        return "pickup_unavailable"
    for purpose, moment in (("pickup", pickup_at), ("return", return_at)):
        if not schedules.covers(
            resource, policy, purpose, moment, moment + timedelta(microseconds=1)
        ):
            return "pickup_unavailable" if purpose == "pickup" else "return_unavailable"
        if not schedules.covers(
            resource, policy, "access", moment, moment + timedelta(microseconds=1)
        ):
            return "outside_access_hours"
    return None
