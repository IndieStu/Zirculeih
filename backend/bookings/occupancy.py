"""Read-side occupancy projection of authoritative schedules and allocation evidence."""

from datetime import timedelta

from accounts.authorization import _grants_allow
from accounts.models import Grant, User
from django.db.models import Q
from django.utils import timezone
from resources.services import resource_scope

from . import schedules
from .models import AllocationClaim, ResourceBlock, ScheduleException, ScheduleWindow
from .time_rules import zone


def blocking_claims():
    return AllocationClaim.objects.filter(
        Q(is_active=True)
        | Q(booking__status="completed", booking__policy_snapshot__use_mode="onsite")
    )


def padded_claim(claim, policy):
    """Retain historical claims and apply current transition to new attempts."""
    return (
        min(
            claim.during.lower,
            claim.booking.start - timedelta(minutes=policy.buffer_before_minutes),
        ),
        max(claim.during.upper, claim.booking.end + timedelta(minutes=policy.buffer_after_minutes)),
    )


def transition_extent(claim, policy):
    lo, hi = padded_claim(claim, policy)
    return (
        lo - timedelta(minutes=policy.buffer_after_minutes),
        hi + timedelta(minutes=policy.buffer_before_minutes),
    )


class Occupancy:
    def __init__(self, resource, policy, start, end, actor=None):
        from lending.models import LoanLine

        from .services import candidates

        self.resource, self.policy, self.actor = resource, policy, actor
        self.now = timezone.now()
        self.scope = resource_scope(resource)
        valid_actor = (
            User.objects.filter(
                pk=getattr(actor, "pk", None), is_active=True, email_verified_at__isnull=False
            ).exists()
            if getattr(actor, "is_authenticated", False)
            else False
        )
        self.unstaffed_grants = (
            list(
                Grant.objects.filter(
                    action="resource.use_unstaffed",
                    group__is_active=True,
                    group__archived_at__isnull=True,
                    group__membership__user=actor,
                    group__membership__removed_at__isnull=True,
                )
            )
            if valid_actor
            else []
        )
        self.units = list(candidates(resource))
        owners = schedules.owner_filter(resource, calendar=True)
        self.windows = list(ScheduleWindow.objects.filter(owners))
        self.exceptions = list(
            ScheduleException.objects.filter(
                owners,
                date__gte=(start - timedelta(days=2)).date(),
                date__lte=(end + timedelta(days=2)).date(),
            )
        )
        self.blocks = list(
            ResourceBlock.objects.filter(
                schedules.owner_filter(resource),
                is_active=True,
                start__lt=end + timedelta(minutes=policy.buffer_after_minutes),
                end__gt=start - timedelta(minutes=policy.buffer_before_minutes),
            )
        )
        self.claims = list(
            blocking_claims()
            .filter(
                unit__in=self.units,
                during__overlap=(
                    start
                    - timedelta(minutes=policy.buffer_after_minutes + policy.buffer_before_minutes),
                    end
                    + timedelta(minutes=policy.buffer_before_minutes + policy.buffer_after_minutes),
                ),
            )
            .select_related("booking")
        )
        self.custody = list(LoanLine.objects.filter(unit__in=self.units, returned_at__isnull=True))

    def covers(self, purpose, start, end):
        return schedules.covers(
            self.resource,
            self.policy,
            purpose,
            start,
            end,
            window_rows=self.windows,
            exception_rows=self.exceptions,
        )

    def state(self, start, end):
        p = self.policy
        if p.use_mode == "onsite":
            if not self.covers("usage", start, end) or not self.covers("access", start, end):
                return "closed"
            horizon = (
                start.astimezone(zone(p.timezone)).date()
                - self.now.astimezone(zone(p.timezone)).date()
            ).days
            unstaffed = _grants_allow(
                self.unstaffed_grants, self.scope, horizon, (end - start).total_seconds() / 60
            )
            if not unstaffed and not self.covers("opening", start, end):
                return "closed"
        if any(b.start < end and b.end > start for b in self.blocks):
            return "blocked"
        if any(
            b.start - timedelta(minutes=p.buffer_after_minutes) < end
            and b.end + timedelta(minutes=p.buffer_before_minutes) > start
            for b in self.blocks
        ):
            return "transition"
        if not self.units:
            return "blocked"
        reasons = []
        for unit in self.units:
            reason = None
            if p.use_mode == "physical_loan" and any(
                line.unit_id == unit.pk and line.expected_return > start for line in self.custody
            ):
                reason = "booked"
            for claim in self.claims:
                if claim.unit_id != unit.pk:
                    continue
                lo, hi = transition_extent(claim, p)
                if lo < end and hi > start:
                    if claim.booking.start < end and claim.booking.end > start:
                        reason = "booked"
                        break
                    reason = reason or "transition"
            if reason is None:
                return (
                    "closed"
                    if start < self.now + timedelta(minutes=p.lead_minutes)
                    else "available"
                )
            reasons.append(reason)
        return "booked" if "booked" in reasons else "transition"

    def free_units(self, start, end):
        p = self.policy
        lo = start - timedelta(minutes=p.buffer_before_minutes)
        hi = end + timedelta(minutes=p.buffer_after_minutes)
        if any(b.start < hi and b.end > lo for b in self.blocks):
            return []
        result = []
        for unit in self.units:
            if any(
                c.unit_id == unit.pk and padded_claim(c, p)[0] < hi and padded_claim(c, p)[1] > lo
                for c in self.claims
            ):
                continue
            if p.use_mode == "physical_loan" and any(
                line.unit_id == unit.pk and line.expected_return > start for line in self.custody
            ):
                continue
            result.append(unit.pk)
        return result

    def segments(self, start, end):
        from datetime import datetime, time

        from .time_rules import local_instant, zone

        boundaries = {start, end, self.now + timedelta(minutes=self.policy.lead_minutes)}
        day = start.astimezone(zone(self.policy.timezone)).date() - timedelta(days=1)
        last = end.astimezone(zone(self.policy.timezone)).date()
        while day <= last:
            boundaries.add(local_instant(datetime.combine(day, time()), self.policy.timezone))
            for row in self.windows:
                if row.weekday == day.weekday():
                    for lo, hi in schedules.segment(row, day, self.policy.timezone):
                        boundaries.update((lo, hi))
            for row in self.exceptions:
                if row.date == day and not row.is_closed:
                    for lo, hi in schedules.segment(row, day, self.policy.timezone):
                        boundaries.update((lo, hi))
            day += timedelta(days=1)
        for claim in self.claims:
            lo, hi = transition_extent(claim, self.policy)
            boundaries.update(
                (
                    lo,
                    hi,
                    claim.booking.start,
                    claim.booking.end,
                )
            )
        for block in self.blocks:
            boundaries.update(
                (
                    block.start,
                    block.end,
                    block.start - timedelta(minutes=self.policy.buffer_after_minutes),
                    block.end + timedelta(minutes=self.policy.buffer_before_minutes),
                )
            )
        for line in self.custody:
            boundaries.add(line.expected_return)
        ordered = sorted({start, end, *[t for t in boundaries if start < t < end]})
        result: list[tuple] = []
        for lo, hi in zip(ordered, ordered[1:], strict=False):
            state = self.state(lo, hi)
            if result and result[-1][2] == state:
                result[-1] = (result[-1][0], hi, state)
            else:
                result.append((lo, hi, state))
        return result
