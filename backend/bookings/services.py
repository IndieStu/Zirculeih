import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from accounts.authorization import allowed, authorization_write, require
from accounts.models import User
from accounts.services import audit
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from inventory.models import Category, Location
from inventory.services import tree_scope
from psycopg.types.range import Range
from resources.models import Resource, ResourceUnit
from resources.services import active_context, resource_scope, visible_resources

from . import schedules
from .models import (
    AllocationClaim,
    Booking,
    BookingIncident,
    BookingPolicy,
    IdempotencyRecord,
    ResourceBlock,
    ScheduleException,
    ScheduleWindow,
)
from .time_rules import aware_interval, interval, zone


@dataclass(frozen=True)
class Availability:
    code: str
    start: object = None
    end: object = None
    unit_id: UUID | None = None
    policy_revision: int | None = None


def policy_snapshot(policy):
    return {k: v for k, v in model_to_dict(policy).items() if k != "resource"}


def save_policy(actor, resource_id, data, expected_revision=None):
    with authorization_write():
        resource = Resource.objects.get(pk=resource_id)
        require(actor, "booking.configure", resource_scope(resource))
        policy = BookingPolicy.objects.filter(resource=resource).first()
        before = policy_snapshot(policy) if policy else None
        if policy and policy.revision != expected_revision:
            raise ValidationError("Buchungsregeln wurden inzwischen geändert.")
        policy = policy or BookingPolicy(resource=resource)
        fields = {f.name for f in BookingPolicy._meta.fields} - {"resource", "revision"}
        if set(data) - fields:
            raise ValidationError("Unbekannte Buchungsregeln.")
        for k, v in data.items():
            setattr(policy, k, v)
        if (
            policy.use_mode == "onsite"
            and policy.buffer_before_minutes + policy.buffer_after_minutes < 30
        ):
            if {"buffer_before_minutes", "buffer_after_minutes"} & set(data):
                raise ValidationError(
                    "Für Räume und Maschinen sind mindestens 30 Minuten Übergangszeit erforderlich."
                )
            policy.buffer_after_minutes = 30 - policy.buffer_before_minutes
        zone(policy.timezone)
        # Technical expansion bounds; explicit rather than unbounded schedule work.
        if (
            policy.max_days > 366
            or policy.max_duration_minutes > 366 * 1440
            or policy.max_horizon_days > 3660
            or any(
                value > 3660 * 1440
                for value in (
                    policy.lead_minutes,
                    policy.buffer_before_minutes,
                    policy.buffer_after_minutes,
                    policy.cancellation_notice_minutes,
                )
            )
        ):
            raise ValidationError("Technische Grenzen: Zeitraum 366 Tage, Horizont 3660 Tage.")
        policy.revision += 1
        policy.full_clean()
        policy.save()
        audit(
            actor,
            "booking.policy_saved",
            object_id=resource.pk,
            details={"before": before, "after": policy_snapshot(policy)},
        )
        return policy


def schedule_scope(resource_id, location_id, category_id=None, organization=False):
    if sum(map(bool, (resource_id, location_id, category_id, organization))) != 1:
        raise ValidationError("Bitte genau ein Angebot oder einen Standort wählen.")
    if organization:
        from accounts.authorization import ORGANIZATION

        return ORGANIZATION
    if category_id:
        return tree_scope(Category.objects.get(pk=category_id))
    if resource_id:
        return resource_scope(Resource.objects.get(pk=resource_id))
    return tree_scope(Location.objects.get(pk=location_id))


def affected_bookings(resource_id=None, location_id=None, category_id=None, organization=False):
    rows = Booking.objects.filter(status__in=["confirmed", "active"])
    if resource_id:
        return rows.filter(resource_id=resource_id)
    from inventory.services import descendants

    if organization:
        return rows
    if category_id:
        return rows.filter(resource__categories__in=descendants(Category, category_id)).distinct()
    return rows.filter(resource__location_id__in=descendants(Location, location_id))


def flag_incidents(bookings, code):
    for booking in bookings:
        BookingIncident.objects.get_or_create(booking=booking, code=code, is_open=True)


def save_schedule(actor, data, *, exception=False):
    with authorization_write():
        data = dict(data)
        resource_id = getattr(data.get("resource"), "pk", None)
        location_id = getattr(data.get("location"), "pk", None)
        category_id = getattr(data.get("category"), "pk", None)
        organization = data.get("organization", False)
        require(
            actor,
            "booking.configure",
            schedule_scope(resource_id, location_id, category_id, organization),
        )
        model = ScheduleException if exception else ScheduleWindow
        fields = {f.name for f in model._meta.fields} - {"id"}
        if set(data) - fields:
            raise ValidationError("Unbekannte Zeitplanfelder.")
        row = model(**data)
        row.full_clean()
        if row.end_next_day and row.end_time > row.start_time:
            raise ValidationError("Ein Zeitfenster darf höchstens 24 Stunden umfassen.")
        row.save()
        # Existing promises survive configuration changes and are made visible for review.
        flag_incidents(
            affected_bookings(resource_id, location_id, category_id, organization),
            "schedule_changed",
        )
        audit(
            actor,
            "booking.schedule_exception_added" if exception else "booking.schedule_added",
            object_id=row.pk,
            details={key: str(value) for key, value in model_to_dict(row).items()},
        )
        return row


def remove_schedule(actor, row_id, *, exception=False):
    with authorization_write():
        model = ScheduleException if exception else ScheduleWindow
        row = model.objects.get(pk=row_id)
        require(
            actor,
            "booking.configure",
            schedule_scope(row.resource_id, row.location_id, row.category_id, row.organization),
        )
        flag_incidents(
            affected_bookings(row.resource_id, row.location_id, row.category_id, row.organization),
            "schedule_changed",
        )
        audit(
            actor,
            "booking.schedule_removed",
            object_id=row.pk,
            details={key: str(value) for key, value in model_to_dict(row).items()},
        )
        row.delete()


def set_block(actor, data):
    with authorization_write():
        resource_id = getattr(data.get("resource"), "pk", None)
        location_id = getattr(data.get("location"), "pk", None)
        require(actor, "booking.block", schedule_scope(resource_id, location_id))
        if set(data) - {"resource", "location", "start", "end", "reason"}:
            raise ValidationError("Unbekannte Sperrfelder.")
        aware_interval(data["start"], data["end"])
        row = ResourceBlock(**data, created_by=actor, revision=1)
        row.full_clean()
        row.save()
        impacted = affected_bookings(resource_id, location_id).filter(
            claim__during__overlap=(row.start, row.end)
        )
        flag_incidents(impacted, "hard_block")
        audit(actor, "booking.block_created", object_id=row.pk, reason=row.reason)
        return row


def lift_block(actor, block_id, revision, reason):
    with authorization_write():
        row = ResourceBlock.objects.get(pk=block_id)
        require(actor, "booking.block", schedule_scope(row.resource_id, row.location_id))
        if row.revision != revision or not reason.strip() or len(reason) > 500:
            raise ValidationError("Aktuelle Revision und Grund erforderlich.")
        row.is_active = False
        row.revision += 1
        row.save()
        audit(actor, "booking.block_lifted", object_id=row.pk, reason=reason)
        return row


def candidates(resource):
    return (
        ResourceUnit.objects.filter(resource=resource, is_active=True)
        .filter(
            Q(asset__isnull=True)
            | Q(
                asset__archived_at__isnull=True,
                asset__lifecycle="active",
                asset__condition__in=["good", "worn"],
            )
        )
        .order_by("id")
    )


def evaluate(
    actor,
    beneficiary,
    resource,
    policy,
    start,
    end,
    *,
    unit_id=None,
    pool_id=None,
    now=None,
    lock=False,
    start_fold=None,
    end_fold=None,
    pickup_at=None,
    return_at=None,
    existing_booking=None,
    parallel_group=None,
):
    now = now or timezone.now()
    scope = resource_scope(resource)
    s, e, minutes, day_start, day_end = interval(
        policy, start, end, start_fold=start_fold, end_fold=end_fold
    )
    horizon = (
        s.astimezone(zone(policy.timezone)).date() - now.astimezone(zone(policy.timezone)).date()
    ).days
    if not User.objects.filter(
        pk=getattr(beneficiary, "pk", None), is_active=True, email_verified_at__isnull=False
    ).exists():
        return Availability("permission_denied")
    own = actor.pk == beneficiary.pk
    action = "booking.create_own" if own else "booking.create_for_others"
    if not allowed(
        actor, action, scope, horizon_days=horizon, duration_minutes=minutes
    ) or not allowed(
        beneficiary, "booking.create_own", scope, horizon_days=horizon, duration_minutes=minutes
    ):
        return Availability("permission_denied")
    if (
        not visible_resources(beneficiary).filter(pk=resource.pk).exists()
        or not active_context(resource)
        or not resource.booking_enabled
    ):
        return Availability("not_bookable")
    if e <= s or (existing_booking is None and s < now + timedelta(minutes=policy.lead_minutes)):
        return Availability("invalid_interval")
    if horizon > policy.max_horizon_days:
        return Availability("outside_booking_horizon")
    if policy.time_mode == "days":
        if not policy.min_days <= (day_end - day_start).days <= policy.max_days:
            return Availability("duration_not_allowed")
    else:
        if not policy.min_duration_minutes <= minutes <= policy.max_duration_minutes:
            return Availability("duration_not_allowed")
        local_s = s.astimezone(zone(policy.timezone))
        local_e = e.astimezone(zone(policy.timezone))
        if any(
            t.second or t.microsecond or (t.hour * 60 + t.minute) % policy.granularity_minutes
            for t in (local_s, local_e)
        ):
            return Availability("granularity_not_allowed")
    from resources.requirements import gate as requirement_gate

    try:
        problem = requirement_gate(beneficiary, resource)
    except ValidationError:
        return Availability(
            "lending_setup_required" if policy.use_mode == "physical_loan" else "agreement_required"
        )
    if problem:
        return Availability(problem)
    if policy.use_mode == "physical_loan":
        from lending.agreements import required_versions
        from lending.rules import appointments

        try:
            required_versions(resource)
        except ValidationError:
            return Availability("lending_setup_required")

        problem = appointments(resource, policy, s, e, pickup_at, return_at)
        if problem:
            return Availability(problem)
    else:
        if not schedules.covers(resource, policy, "usage", s, e):
            return Availability("outside_usage_hours")
        if not schedules.covers(resource, policy, "access", s, e):
            return Availability("outside_access_hours")
        if not allowed(
            beneficiary,
            "resource.use_unstaffed",
            scope,
            horizon_days=horizon,
            duration_minutes=minutes,
        ) and not schedules.covers(resource, policy, "opening", s, e):
            return Availability("outside_staffed_hours")
    claim_start = s - timedelta(minutes=policy.buffer_before_minutes)
    claim_end = e + timedelta(minutes=policy.buffer_after_minutes)
    if ResourceBlock.objects.filter(
        schedules.owner_filter(resource), is_active=True, start__lt=claim_end, end__gt=claim_start
    ).exists():
        return Availability("hard_block")
    from django.db.models.functions import Coalesce

    from .models import BundleMember

    same_group = (
        parallel_group
        or BundleMember.objects.filter(booking_id=getattr(existing_booking, "pk", None))
        .values_list("reservation_id", flat=True)
        .first()
    )
    parallel = Booking.objects.filter(
        beneficiary=beneficiary, status__in=["confirmed", "active"], start__lt=e, end__gt=s
    ).exclude(pk=getattr(existing_booking, "pk", None))
    if same_group:
        parallel = parallel.exclude(bundle_member__reservation_id=same_group)
    if (
        parallel.annotate(logical=Coalesce("bundle_member__reservation_id", "pk"))
        .values("logical")
        .distinct()
        .count()
        >= policy.max_parallel
    ):
        return Availability("parallel_limit")
    units = capacity_units(
        resource,
        policy,
        s,
        e,
        unit_id=unit_id,
        pool_id=pool_id,
        lock=lock,
        existing_booking=existing_booking,
    )
    for unit in units:
        if policy.use_mode == "physical_loan":
            from lending.agreements import gate

            problem = gate(beneficiary, resource, unit)
            if problem:
                return Availability(problem)
        return Availability("available", s, e, unit.pk, policy.revision)
    return Availability(
        "reserved" if candidates(resource).exists() else "capacity_exhausted",
        s,
        e,
        policy_revision=policy.revision,
    )


def capacity_units(
    resource, policy, start, end, *, unit_id=None, pool_id=None, lock=False, existing_booking=None
):
    """Shared capacity calculation for anonymous occupancy and binding allocation.

    This does not grant eligibility. Confirmation separately checks the actor,
    beneficiary, requirements, schedules and appointments under allocation locks.
    """
    units = candidates(resource)
    if pool_id:
        units = units.filter(
            pool_membership__pool_id=pool_id,
            pool_membership__pool__resource=resource,
            pool_membership__pool__is_active=True,
        )
    if unit_id:
        units = units.filter(pk=unit_id)
    if lock:
        units = units.select_for_update(of=("self",))
    units = list(units)
    claim_start = start - timedelta(minutes=policy.buffer_before_minutes)
    claim_end = end + timedelta(minutes=policy.buffer_after_minutes)
    if ResourceBlock.objects.filter(
        schedules.owner_filter(resource), is_active=True, start__lt=claim_end, end__gt=claim_start
    ).exists():
        return []
    from .occupancy import blocking_claims, padded_claim

    claims = (
        blocking_claims()
        .filter(
            unit__in=units,
            during__overlap=(
                claim_start - timedelta(minutes=policy.buffer_after_minutes),
                claim_end + timedelta(minutes=policy.buffer_before_minutes),
            ),
        )
        .exclude(booking_id=getattr(existing_booking, "pk", None))
        .select_related("booking")
    )
    blocked = {
        claim.unit_id
        for claim in claims
        if padded_claim(claim, policy)[0] < claim_end
        and padded_claim(claim, policy)[1] > claim_start
    }
    if policy.use_mode == "physical_loan":
        from lending.models import LoanLine

        blocked.update(
            LoanLine.objects.filter(
                unit__in=units, returned_at__isnull=True, expected_return__gt=start
            )
            .exclude(booking_id=getattr(existing_booking, "pk", None))
            .values_list("unit_id", flat=True)
        )
    return [u for u in units if u.pk not in blocked]


def _availability_single(
    actor,
    resource_id,
    start,
    end,
    *,
    beneficiary=None,
    unit_id=None,
    pool_id=None,
    start_fold=None,
    end_fold=None,
    pickup_at=None,
    return_at=None,
    existing_booking=None,
):
    require_active_actor(actor)
    resource = visible_resources(beneficiary or actor).filter(pk=resource_id).first()
    if resource is None:
        return Availability("permission_denied")
    policy = BookingPolicy.objects.filter(resource=resource).first()
    if policy is None:
        return Availability("not_configured")
    return evaluate(
        actor,
        beneficiary or actor,
        resource,
        policy,
        start,
        end,
        unit_id=unit_id,
        pool_id=pool_id,
        start_fold=start_fold,
        end_fold=end_fold,
        pickup_at=pickup_at,
        return_at=return_at,
        existing_booking=existing_booking,
    )


def read_booking(actor, booking_id):
    booking = Booking.objects.select_related("resource__location", "beneficiary", "unit").get(
        pk=booking_id
    )
    require_active_actor(actor)
    if actor.pk != booking.beneficiary_id:
        require(actor, "booking.read_all", resource_scope(booking.resource))
    return booking


def require_active_actor(actor):
    if not User.objects.filter(
        pk=getattr(actor, "pk", None), is_active=True, email_verified_at__isnull=False
    ).exists():
        raise PermissionDenied("Konto nicht freigegeben.")


def _confirm_single(
    actor,
    resource_id,
    start,
    end,
    key,
    *,
    beneficiary=None,
    unit_id=None,
    pool_id=None,
    start_fold=None,
    end_fold=None,
    pickup_at=None,
    return_at=None,
    walk_in=False,
    _parallel_group=None,
):
    beneficiary = beneficiary or actor
    try:
        key = UUID(str(key))
    except (ValueError, TypeError) as exc:
        raise ValidationError("Ungültiger Idempotenzschlüssel.") from exc
    payload = {
        "resource": str(resource_id),
        "beneficiary": str(beneficiary.pk),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "unit": str(unit_id) if unit_id else None,
        "start_fold": start_fold,
        "end_fold": end_fold,
    }
    if pool_id:
        payload["pool"] = str(pool_id)
    if pickup_at is not None or return_at is not None:
        payload.update(
            pickup_at=pickup_at.isoformat() if pickup_at else None,
            return_at=return_at.isoformat() if return_at else None,
        )
    if walk_in:
        payload["walk_in"] = True
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    with authorization_write():
        require_active_actor(actor)
        prior = IdempotencyRecord.objects.filter(actor=actor, operation="confirm", key=key).first()
        if prior:
            if prior.payload_hash != digest:
                raise ValidationError("Dieser Schlüssel wurde für andere Eingaben verwendet.")
            return read_booking(actor, prior.booking_id)
        resource = visible_resources(beneficiary).filter(pk=resource_id).first()
        if resource is None:
            raise PermissionDenied("Kein zugängliches Angebot.")
        policy = BookingPolicy.objects.select_for_update().filter(resource=resource).first()
        if policy is None:
            raise ValidationError("Buchung noch nicht konfiguriert.")
        existing = None
        if walk_in:
            require(actor, "loan.checkout", resource_scope(resource))
            s0, e0, _, _, _ = interval(policy, start, end, start_fold=start_fold, end_fold=end_fold)
            now = timezone.now()
            if policy.use_mode != "physical_loan" or policy.lead_minutes != 0 or not s0 <= now < e0:
                raise ValidationError(
                    "Spontanausgabe benötigt aktuellen Zeitraum und Vorlauf null."
                )
            if (
                s0.astimezone(zone(policy.timezone)).date()
                != now.astimezone(zone(policy.timezone)).date()
            ):
                raise ValidationError("Spontanausgabe muss heute beginnen.")
            from types import SimpleNamespace

            existing = SimpleNamespace(pk=None)
        result = evaluate(
            actor,
            beneficiary,
            resource,
            policy,
            start,
            end,
            unit_id=unit_id,
            pool_id=pool_id,
            lock=True,
            start_fold=start_fold,
            end_fold=end_fold,
            pickup_at=pickup_at,
            return_at=return_at,
            existing_booking=existing,
            parallel_group=_parallel_group,
        )
        if result.code != "available":
            raise ValidationError(result.code)
        s, e, _, day_start, day_end = interval(
            policy, start, end, start_fold=start_fold, end_fold=end_fold
        )
        try:
            with transaction.atomic():
                booking = Booking.objects.create(
                    actor=actor,
                    beneficiary=beneficiary,
                    resource=resource,
                    unit_id=result.unit_id,
                    start=s,
                    end=e,
                    start_date=day_start,
                    end_date_exclusive=day_end,
                    timezone=policy.timezone,
                    policy_snapshot=policy_snapshot(policy),
                )
                AllocationClaim.objects.create(
                    booking=booking,
                    unit_id=result.unit_id,
                    during=Range(
                        s - timedelta(minutes=policy.buffer_before_minutes),
                        e + timedelta(minutes=policy.buffer_after_minutes),
                        "[)",
                    ),
                )
                if policy.use_mode == "physical_loan":
                    from lending.models import Appointment

                    Appointment.objects.create(
                        booking=booking, pickup_at=pickup_at, return_at=return_at
                    )
                IdempotencyRecord.objects.create(
                    actor=actor, operation="confirm", key=key, payload_hash=digest, booking=booking
                )
                audit(
                    actor,
                    "booking.confirmed",
                    subject=beneficiary,
                    object_id=booking.pk,
                    details={"resource_id": str(resource.pk), "unit_id": str(result.unit_id)},
                )
        except IntegrityError as exc:
            raise ValidationError(
                "Der Zeitraum wurde inzwischen belegt. Bitte erneut prüfen."
            ) from exc
        return booking


def _cancel_single(actor, booking_id, revision, reason):
    with authorization_write():
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        require_active_actor(actor)
        scope = resource_scope(booking.resource)
        if actor.pk == booking.beneficiary_id:
            require(actor, "booking.cancel_own", scope)
        else:
            require(actor, "booking.manage_all", scope)
        if booking.revision != revision or not reason.strip() or len(reason) > 500:
            raise ValidationError("Aktuelle Revision und Grund erforderlich.")
        if booking.status not in {"confirmed", "active"}:
            raise ValidationError("Dieser Vorgang kann nicht mehr storniert werden.")
        deadline = booking.start - timedelta(
            minutes=booking.policy_snapshot["cancellation_notice_minutes"]
        )
        if timezone.now() >= deadline:
            raise ValidationError("Stornofrist abgelaufen.")
        ResourceUnit.objects.select_for_update().get(pk=booking.unit_id)
        booking.status = "cancelled"
        booking.revision += 1
        booking.updated_at = timezone.now()
        booking.save()
        AllocationClaim.objects.filter(booking=booking).update(is_active=False)
        audit(
            actor,
            "booking.cancelled",
            subject=booking.beneficiary,
            object_id=booking.pk,
            reason=reason,
        )
        return booking


def visible_bookings(actor, *, operational=False):
    require_active_actor(actor)
    rows = Booking.objects.select_related("resource__location", "beneficiary").order_by(
        "start", "id"
    )
    if not operational:
        return rows.filter(beneficiary=actor)
    from accounts.authorization import allowed_many

    records = list(rows)
    decisions = allowed_many(
        actor, "booking.read_all", [resource_scope(b.resource) for b in records]
    )
    return rows.filter(pk__in=[b.pk for b, ok in zip(records, decisions, strict=True) if ok])


def resolve_incident(actor, incident_id, reason):
    with authorization_write():
        row = BookingIncident.objects.select_related("booking__resource__location").get(
            pk=incident_id
        )
        require_active_actor(actor)
        require(actor, "booking.manage_all", resource_scope(row.booking.resource))
        if not reason.strip() or len(reason) > 500:
            raise ValidationError("Bitte einen Grund bis 500 Zeichen angeben.")
        row.is_open = False
        row.save(update_fields=["is_open"])
        audit(
            actor,
            "booking.incident_resolved",
            object_id=row.booking_id,
            reason=reason,
            details={"incident_id": str(row.pk)},
        )


def advance_onsite_bookings():
    """Explicit operator job; no loan/custody or invented physical return."""
    changed = 0
    with authorization_write():
        now = timezone.now()
        for row in Booking.objects.select_for_update().filter(
            status__in=["confirmed", "active"], start__lte=now
        ):
            if row.policy_snapshot.get("use_mode") != "onsite":
                continue
            next_state = "completed" if row.end <= now else "active"
            if row.status == next_state:
                continue
            row.status = next_state
            row.revision += 1
            row.updated_at = now
            row.save()
            if next_state == "completed":
                AllocationClaim.objects.filter(booking=row).update(is_active=False)
            audit(None, "booking." + next_state, object_id=row.pk)
            changed += 1
    return changed


def availability(actor, resource_id, start, end, *, optional_ids=(), **kwargs):
    result = _availability_single(actor, resource_id, start, end, **kwargs)
    if result.code != "available" or kwargs.get("existing_booking") is not None:
        return result
    from resources.bundles import expansion

    for resource, _required in expansion(Resource.objects.get(pk=resource_id), optional_ids)[1:]:
        component_kwargs = dict(kwargs)
        component_kwargs.pop("unit_id", None)
        component_kwargs.pop("pool_id", None)
        if resource.bookingpolicy.use_mode != "physical_loan":
            component_kwargs.pop("pickup_at", None)
            component_kwargs.pop("return_at", None)
        component_result = _availability_single(actor, resource.pk, start, end, **component_kwargs)
        if component_result.code != "available":
            return Availability("bundle_component_unavailable")
    return result


def confirm(actor, resource_id, start, end, key, *, optional_ids=(), **kwargs):
    if any(k.startswith("_") for k in kwargs):
        raise ValidationError("Unbekannte Buchungseingabe.")
    from resources.models import BundleComponent

    if (
        BundleComponent.objects.filter(resource_id=resource_id).exists()
        or optional_ids
        or IdempotencyRecord.objects.filter(
            actor=actor, operation="bundle-confirm", key=key
        ).exists()
    ):
        from .bundles import confirm as confirm_bundle

        return confirm_bundle(
            actor, resource_id, start, end, key, optional_ids=optional_ids, **kwargs
        )
    return _confirm_single(actor, resource_id, start, end, key, **kwargs)


def cancel(actor, booking_id, revision, reason):
    from .models import BundleMember

    with authorization_write():
        row = read_booking(actor, booking_id)
        if row.revision != revision:
            raise ValidationError("Buchung wurde inzwischen geändert.")
        member = BundleMember.objects.filter(booking=row).first()
        if member:
            from .bundles import cancel as cancel_bundle

            cancel_bundle(actor, member.reservation_id, reason)
            return Booking.objects.get(pk=booking_id)
        return _cancel_single(actor, booking_id, revision, reason)
