"""Compose occupancy projections without a second allocation model or personal data."""

from bookings.occupancy import Occupancy
from django.core.exceptions import ValidationError

from .bundles import expansion
from .services import visible_resources


class BundleOccupancy:
    def __init__(self, root, children, unavailable=False):
        self.root, self.children, self.unavailable = root, children, unavailable

    def __getattr__(self, key):
        return getattr(self.root, key)

    def free_units(self, start, end):
        if self.unavailable or any(not s.free_units(start, end) for s in self.children):
            return []
        return self.root.free_units(start, end)

    def state(self, start, end):
        if self.unavailable:
            return "closed"
        states = [s.state(start, end) for s in (self.root, *self.children)]
        for state in ("blocked", "closed", "booked", "transition"):
            if state in states:
                return state
        return "available"

    def segments(self, start, end):
        boundaries = {start, end}
        for snapshot in (self.root, *self.children):
            for lo, hi, _state in snapshot.segments(start, end):
                boundaries.update((lo, hi))
        ordered = sorted(boundaries)
        result: list[tuple] = []
        for lo, hi in zip(ordered, ordered[1:], strict=False):
            state = self.state(lo, hi)
            if result and result[-1][2] == state:
                result[-1] = (result[-1][0], hi, state)
            else:
                result.append((lo, hi, state))
        return result


def occupancy(resource, policy, start, end, actor=None):
    root = Occupancy(resource, policy, start, end, actor)
    if not resource.bundle_components.exists():
        return root
    children = []
    unavailable = False
    visible = set(visible_resources(actor).values_list("pk", flat=True))
    try:
        for component, _required in expansion(resource)[1:]:
            if (
                component.pk not in visible
                or not component.booking_enabled
                or not hasattr(component, "bookingpolicy")
            ):
                unavailable = True
                continue
            p = component.bookingpolicy
            if (p.timezone, p.time_mode) != (policy.timezone, policy.time_mode):
                unavailable = True
                continue
            children.append(Occupancy(component, p, start, end, actor))
    except ValidationError:
        unavailable = True
    return BundleOccupancy(root, children, unavailable)
