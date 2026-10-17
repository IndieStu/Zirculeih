"""Atomic reservations of independent resources, preserving their ordinary gates."""

import hashlib
import json
from uuid import UUID, uuid5

from accounts.authorization import authorization_write
from django.core.exceptions import ValidationError
from resources.bundles import expansion
from resources.models import Resource

from .models import BundleMember, BundleReservation, IdempotencyRecord


def confirm(
    actor, resource_id, start, end, key, *, optional_ids=(), component_units=None, **kwargs
):
    from . import services

    beneficiary = kwargs.get("beneficiary") or actor
    try:
        key = UUID(str(key))
    except (ValueError, TypeError) as exc:
        raise ValidationError("Ungültiger Wiederholungsschlüssel.") from exc
    payload = {
        "resource": str(resource_id),
        "start": start,
        "end": end,
        "beneficiary": beneficiary.pk,
        "optional": sorted(map(str, optional_ids)),
        "component_units": {str(k): str(v) for k, v in (component_units or {}).items()},
        **kwargs,
    }
    payload["beneficiary"] = str(beneficiary.pk)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    with authorization_write():
        services.require_active_actor(actor)
        prior = IdempotencyRecord.objects.filter(
            actor=actor, operation="bundle-confirm", key=key
        ).first()
        if prior:
            if prior.payload_hash != digest:
                raise ValidationError(
                    "Dieser Schlüssel wurde für andere Bundle-Eingaben verwendet."
                )
            return services.read_booking(actor, prior.booking_id)
        root_resource = Resource.objects.get(pk=resource_id)
        entries = expansion(root_resource, optional_ids)
        selections = {str(k): v for k, v in (component_units or {}).items()}
        if set(selections) - {str(r.pk) for r, _ in entries[1:]}:
            raise ValidationError("Unbekannte Komponenten-Auswahl.")
        rows = []
        group = None
        for resource, required in entries:
            component_kwargs = dict(kwargs)
            if resource.pk != root_resource.pk:
                component_kwargs.pop("unit_id", None)
                component_kwargs.pop("pool_id", None)
                component_kwargs["unit_id"] = selections.get(str(resource.pk))
            if resource.bookingpolicy.use_mode != "physical_loan":
                component_kwargs.pop("pickup_at", None)
                component_kwargs.pop("return_at", None)
            component_kwargs["_parallel_group"] = group.pk if group else None
            row = services._confirm_single(
                actor, resource.pk, start, end, uuid5(key, str(resource.pk)), **component_kwargs
            )
            rows.append((row, required))
            if group is None and len(entries) > 1:
                group = BundleReservation.objects.create(
                    root=row, expected_resources=[str(r.pk) for r, _ in entries]
                )
            if group:
                BundleMember.objects.create(reservation=group, booking=row, required=required)
        root = rows[0][0]
        IdempotencyRecord.objects.create(
            actor=actor,
            operation="bundle-confirm",
            key=key,
            payload_hash=digest,
            booking=root,
        )
        return root


def cancel(actor, reservation_id, reason):
    from .services import _cancel_single

    with authorization_write():
        group = BundleReservation.objects.select_for_update().get(pk=reservation_id)
        for member in group.members.select_related("booking").order_by("booking_id"):
            _cancel_single(actor, member.booking_id, member.booking.revision, reason)
        return group.root


def physical_members(booking_ids):
    """Selected physical bundle members must be issued together, including chosen options."""
    groups = BundleReservation.objects.filter(members__booking_id__in=booking_ids).distinct()
    return set(
        BundleMember.objects.filter(
            reservation__in=groups, booking__policy_snapshot__use_mode="physical_loan"
        ).values_list("booking_id", flat=True)
    )
