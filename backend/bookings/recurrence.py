"""Bounded local weekly proposals and atomic approval through the ordinary allocator."""

import hashlib
import json
from datetime import date, datetime, timedelta
from uuid import UUID, uuid5

from accounts.authorization import authorization_write, require
from accounts.services import audit
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from resources.bundles import expansion
from resources.models import Resource
from resources.services import resource_scope, visible_resources

from . import services
from .models import (
    BookingPolicy,
    OccurrenceException,
    RequestAdjustment,
    RequestOccurrence,
    ReservationRequest,
)
from .time_rules import interval, zone


class Conflicts(ValidationError):
    def __init__(self, rows):
        self.rows = rows
        super().__init__("Nicht alle Termine sind verfügbar. Bitte die Terminliste prüfen.")


def expand(start, end, *, weekdays=(), count=None, until=None, limit=52):
    """Count means occurrences (not weeks); no UTC arithmetic or arbitrary RRULE."""
    if type(start) is not type(end) or type(start) not in (date, datetime):
        raise ValidationError("Lokale Tage oder Uhrzeiten erforderlich.")
    if isinstance(start, datetime) and (start.tzinfo is not None or end.tzinfo is not None):
        raise ValidationError("Lokale Uhrzeiten ohne Offset erforderlich.")
    if end < start or (isinstance(start, datetime) and end == start):
        raise ValidationError("Positiver Zeitraum erforderlich.")
    if not weekdays:
        if count is not None or until is not None:
            raise ValidationError("Wochentage für eine Serie auswählen.")
        return [(start, end)]
    days = set(weekdays)
    if any(type(d) is not int or not 0 <= d <= 6 for d in days):
        raise ValidationError("Ungültige Wochentage.")
    if (count is None) == (until is None):
        raise ValidationError("Entweder Anzahl oder Enddatum für die Serie wählen.")
    first = start.date() if isinstance(start, datetime) else start
    if count is not None and (type(count) is not int or not 1 <= count <= limit):
        raise ValidationError(f"Höchstens {limit} Termine erlaubt.")
    if until is not None and (
        type(until) is not date or until < first or (until - first).days > 3660
    ):
        raise ValidationError("Ungültiges Serienende (höchstens 3660 Tage).")
    result = []
    # The configured business cap is distinct from the bounded expansion horizon.
    try:
        for delta in range(3661):
            current = first + timedelta(days=delta)
            if until is not None and current > until:
                break
            if current.weekday() in days:
                result.append((start + timedelta(days=delta), end + timedelta(days=delta)))
                if len(result) > limit:
                    raise ValidationError(f"Höchstens {limit} Termine erlaubt.")
                if count is not None and len(result) == count:
                    return result
    except OverflowError as exc:
        raise ValidationError("Serienende außerhalb des gültigen Kalenders.") from exc
    if not result or (count is not None and len(result) != count):
        raise ValidationError("Keine begrenzte Terminfolge gefunden.")
    return result


def _serialize(options):
    return json.loads(json.dumps(options, default=str, sort_keys=True))


def _options(options):
    data = dict(options)
    for name in ("pickup_at", "return_at"):
        if data.get(name):
            data[name] = datetime.fromisoformat(data[name])
    return data


def _local(row, mode):
    parser = date.fromisoformat if mode == "days" else datetime.fromisoformat
    return parser(row.local_start), parser(row.local_end)


def _entries(resource, options):
    return expansion(resource, options.get("optional_ids", ()))


def _rights(actor, beneficiary, resource, options, start, end, *, recurring=False, approving=False):
    services.require_active_actor(actor)
    services.require_active_actor(beneficiary)
    for item, _ in _entries(resource, options):
        policy = BookingPolicy.objects.get(resource=item)
        try:
            s, _, minutes, _, _ = interval(
                policy,
                start,
                end,
                start_fold=options.get("start_fold"),
                end_fold=options.get("end_fold"),
            )
            local_date = s.astimezone(zone(policy.timezone)).date()
        except ValidationError as exc:
            if approving or exc.code not in {"ambiguous_time", "nonexistent_time"}:
                raise
            # A non-binding proposal may contain a DST conflict, never a silent shift.
            local_date = start.date()
            minutes = (end - start).total_seconds() / 60
        horizon = (local_date - timezone.now().astimezone(zone(policy.timezone)).date()).days
        context = dict(horizon_days=horizon, duration_minutes=minutes)
        scope = resource_scope(item)
        if not visible_resources(beneficiary).filter(pk=item.pk).exists():
            raise PermissionDenied("Kein zugängliches Angebot.")
        require(
            actor,
            "booking.create_own" if actor.pk == beneficiary.pk else "booking.create_for_others",
            scope,
            **context,
        )
        require(beneficiary, "booking.create_own", scope, **context)
        if recurring:
            require(beneficiary, "booking.request_recurrence", scope, **context)
        if approving:
            require(actor, "booking.approve", scope, **context)


def submit(
    actor,
    resource_id,
    start,
    end,
    key,
    *,
    beneficiary=None,
    weekdays=(),
    count=None,
    until=None,
    **options,
):
    beneficiary = beneficiary or actor
    forbidden = set(options) - {
        "unit_id",
        "pool_id",
        "optional_ids",
        "component_units",
        "start_fold",
        "end_fold",
        "pickup_at",
        "return_at",
    }
    if forbidden:
        raise ValidationError("Unbekannte Antragsoptionen.")
    try:
        key = UUID(str(key))
    except (ValueError, TypeError) as exc:
        raise ValidationError("Ungültiger Wiederholungsschlüssel.") from exc
    payload = _serialize(
        dict(
            resource=str(resource_id),
            beneficiary=str(beneficiary.pk),
            start=start.isoformat(),
            end=end.isoformat(),
            weekdays=sorted(set(weekdays)),
            count=count,
            until=until,
            options=options,
        )
    )
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    with authorization_write():
        services.require_active_actor(actor)
        previous = ReservationRequest.objects.filter(actor=actor, key=key).first()
        if previous:
            if previous.payload_hash != digest:
                raise ValidationError("Schlüssel wurde für andere Eingaben verwendet.")
            return read(actor, previous.pk)
        resource = visible_resources(beneficiary).get(pk=resource_id)
        policy = BookingPolicy.objects.get(resource=resource)
        entries = _entries(resource, options)
        cap = min(BookingPolicy.objects.get(resource=r).max_occurrences for r, _ in entries)
        times = expand(start, end, weekdays=weekdays, count=count, until=until, limit=cap)
        for a, b in times:
            _rights(actor, beneficiary, resource, options, a, b, recurring=bool(weekdays))
        proposal = ReservationRequest.objects.create(
            actor=actor,
            beneficiary=beneficiary,
            resource=resource,
            timezone=policy.timezone,
            time_mode=policy.time_mode,
            key=key,
            payload_hash=digest,
            options=_serialize(options),
            rule=_serialize(dict(weekdays=sorted(set(weekdays)), count=count, until=until)),
            expected_occurrences=len(times),
            resources_snapshot=[str(r.pk) for r, _ in entries],
        )
        for index, (a, b) in enumerate(times):
            current_options = dict(options)
            shift = (a.date() if isinstance(a, datetime) else a) - (
                start.date() if isinstance(start, datetime) else start
            )
            for name in ("pickup_at", "return_at"):
                value = current_options.get(name)
                if value is not None:
                    # Preserve appointment wall time separately across DST.
                    wall = value.astimezone(zone(policy.timezone)).replace(tzinfo=None) + shift
                    from .time_rules import local_instant

                    try:
                        current_options[name] = local_instant(wall, policy.timezone)
                    except ValidationError as exc:
                        if exc.code not in {"ambiguous_time", "nonexistent_time"}:
                            raise
                        # Keep the unresolved wall time; strict appointment validation rejects
                        # approval until an explicit occurrence adjustment supplies an instant.
                        current_options[name] = wall
            RequestOccurrence.objects.create(
                request=proposal,
                position=index,
                local_start=a.isoformat(),
                local_end=b.isoformat(),
                options=_serialize(current_options),
            )
        audit(
            actor,
            "booking.requested",
            subject=beneficiary,
            object_id=proposal.pk,
            details={"occurrences": len(times), "non_blocking": True},
        )
        return proposal


def _scope_access(actor, proposal, action):
    for item in Resource.objects.filter(pk__in=proposal.resources_snapshot):
        require(actor, action, resource_scope(item))


def read(actor, request_id):
    services.require_active_actor(actor)
    proposal = ReservationRequest.objects.select_related("resource", "beneficiary").get(
        pk=request_id
    )
    if actor.pk not in (proposal.actor_id, proposal.beneficiary_id):
        _scope_access(actor, proposal, "booking.read_all")
    return proposal


def visible(actor, *, queue=False):
    services.require_active_actor(actor)
    rows = ReservationRequest.objects.select_related("resource", "beneficiary")
    if not queue:
        return rows.filter(beneficiary=actor)
    ids = []
    for row in rows.filter(status="requested"):
        try:
            _scope_access(actor, row, "booking.read_all")
            _scope_access(actor, row, "booking.approve")
        except (PermissionDenied, ValidationError):
            continue
        ids.append(row.pk)
    return rows.filter(pk__in=ids)


def _allocate(actor, proposal, row):
    effective = row.adjustments.last() or row
    if getattr(effective, "cancelled", False):
        return None
    start, end = _local(effective, proposal.time_mode)
    options = _options(effective.options)
    if {str(r.pk) for r, _ in _entries(proposal.resource, options)} != set(
        proposal.resources_snapshot
    ):
        raise ValidationError("Bundle-Konfiguration geändert. Neuen Antrag erstellen.")
    _rights(
        actor,
        proposal.beneficiary,
        proposal.resource,
        options,
        start,
        end,
        recurring=bool(proposal.rule.get("weekdays")),
        approving=True,
    )
    for item, _ in _entries(proposal.resource, options):
        policy = BookingPolicy.objects.get(resource=item)
        if policy.timezone != proposal.timezone or policy.time_mode != proposal.time_mode:
            raise ValidationError("Zeitmodus oder Zeitzone geändert. Neuen Antrag erstellen.")
        if proposal.occurrences.count() > policy.max_occurrences:
            raise ValidationError("Das aktuelle Serienlimit ist überschritten.")
    return services.confirm(
        actor,
        proposal.resource_id,
        start,
        end,
        uuid5(proposal.pk, str(row.pk)),
        beneficiary=proposal.beneficiary,
        approval=True,
        **options,
    )


def preview(actor, request_id):
    """Uncommitted simulation includes conflicts between occurrences and real pool choice."""
    with authorization_write():
        proposal = read(actor, request_id)
        _scope_access(actor, proposal, "booking.approve")
        if proposal.status != "requested":
            raise ValidationError("Nur offene Anträge können geprüft werden.")
        result = []
        with transaction.atomic():
            for row in proposal.occurrences.all():
                try:
                    with transaction.atomic():
                        allocated = _allocate(actor, proposal, row)
                    code = "available" if allocated else "omitted"
                except ValidationError as exc:
                    code = " ".join(exc.messages)
                result.append({"occurrence": row, "code": code})
            transaction.set_rollback(True)
        return result


def approve(actor, request_id, revision, reason):
    with authorization_write():
        proposal = read(actor, request_id)
        _scope_access(actor, proposal, "booking.approve")
        if (
            proposal.status == "approved"
            and proposal.decided_by_id == actor.pk
            and proposal.reason == reason
        ):
            return proposal
        _pending(proposal, revision, reason)
        # Exact simulation reports all dates. The actual allocation repeats every check.
        conflicts = preview(actor, proposal.pk)
        if any(r["code"] not in {"available", "omitted"} for r in conflicts):
            raise Conflicts(conflicts)
        if not any(
            not getattr(row.adjustments.last(), "cancelled", False)
            for row in proposal.occurrences.all()
        ):
            raise ValidationError("Die Serie enthält keinen aktiven Termin mehr.")
        for row in proposal.occurrences.all():
            row.booking = _allocate(actor, proposal, row)
            if row.booking is not None:
                row.save(update_fields=["booking"])
        _decide(actor, proposal, "approved", reason)
        return proposal


def _pending(proposal, revision, reason):
    if proposal.status != "requested" or proposal.revision != revision:
        raise ValidationError("Antrag wurde inzwischen bearbeitet.")
    if not reason.strip() or len(reason) > 500:
        raise ValidationError("Bitte einen Grund (höchstens 500 Zeichen) angeben.")


def _decide(actor, proposal, state, reason):
    proposal.status = state
    proposal.reason = reason
    proposal.decided_by = actor
    proposal.decided_at = timezone.now()
    proposal.revision += 1
    proposal.save()
    audit(
        actor,
        "booking.request_" + state,
        subject=proposal.beneficiary,
        object_id=proposal.pk,
        reason=reason,
    )


def reject(actor, request_id, revision, reason):
    with authorization_write():
        proposal = read(actor, request_id)
        _scope_access(actor, proposal, "booking.approve")
        _pending(proposal, revision, reason)
        _decide(actor, proposal, "rejected", reason)
        return proposal


def current_booking(row):
    booking = row.booking
    changes = {
        change.previous_id: change.replacement
        for change in row.exceptions.select_related("replacement")
    }
    while booking is not None and booking.pk in changes:
        booking = changes.pop(booking.pk)
    return booking


def withdraw(actor, request_id, revision, reason):
    with authorization_write():
        proposal = read(actor, request_id)
        action = (
            "booking.cancel_own" if actor.pk == proposal.beneficiary_id else "booking.manage_all"
        )
        _scope_access(actor, proposal, action)
        if proposal.revision != revision or proposal.status not in {"requested", "approved"}:
            raise ValidationError("Antrag wurde inzwischen bearbeitet.")
        if not reason.strip() or len(reason) > 500:
            raise ValidationError("Bitte einen Grund angeben.")
        if proposal.status == "approved":
            for row in proposal.occurrences.all():
                booking = current_booking(row)
                if booking and booking.status not in {"cancelled", "no_show", "completed"}:
                    services.cancel(actor, booking.pk, booking.revision, reason)
        _decide(actor, proposal, "cancelled", reason)
        return proposal


def exception(actor, occurrence_id, revision, reason, *, start=None, end=None, **options):
    with authorization_write():
        row = RequestOccurrence.objects.select_related("request__resource").get(pk=occurrence_id)
        proposal = read(actor, row.request_id)
        if proposal.status != "approved":
            raise ValidationError("Nur genehmigte Termine haben Ausnahmen.")
        booking = current_booking(row)
        if booking is None or booking.revision != revision:
            raise ValidationError("Termin wurde inzwischen bearbeitet.")
        if start is None and end is None:
            replacement = None
        else:
            if start is None or end is None:
                raise ValidationError("Beginn und Ende erforderlich.")
            _scope_access(actor, proposal, "booking.approve")
            options = {**_options(row.options), **options}
            _rights(
                actor,
                proposal.beneficiary,
                proposal.resource,
                options,
                start,
                end,
                recurring=bool(proposal.rule.get("weekdays")),
                approving=True,
            )
        services.cancel(actor, booking.pk, revision, reason)
        if start is not None:
            replacement = services.confirm(
                actor,
                proposal.resource_id,
                start,
                end,
                uuid5(row.pk, str(booking.pk)),
                beneficiary=proposal.beneficiary,
                approval=True,
                **options,
            )
        change = OccurrenceException.objects.create(
            occurrence=row, previous=booking, replacement=replacement, actor=actor, reason=reason
        )
        audit(
            actor,
            "booking.occurrence_exception",
            subject=proposal.beneficiary,
            object_id=row.pk,
            reason=reason,
            details={
                "previous": str(booking.pk),
                "replacement": str(replacement.pk) if replacement else None,
            },
        )
        return change


def adjust(actor, occurrence_id, revision, reason, *, start=None, end=None, **options):
    """Correct one pending occurrence, retaining its original local key and audit."""
    with authorization_write():
        row = RequestOccurrence.objects.select_related("request__resource").get(pk=occurrence_id)
        proposal = read(actor, row.request_id)
        _pending(proposal, revision, reason)
        if actor.pk != proposal.beneficiary_id:
            _scope_access(actor, proposal, "booking.approve")
        else:
            _scope_access(
                actor,
                proposal,
                "booking.request_recurrence"
                if proposal.rule.get("weekdays")
                else "booking.create_own",
            )
        effective = row.adjustments.last() or row
        if start is None or end is None:
            if start is not None or end is not None:
                raise ValidationError("Beginn und Ende erforderlich.")
            start, end = _local(effective, proposal.time_mode)
            cancelled = True
        else:
            cancelled = False
        merged = {**_options(effective.options), **options}
        # Strict conversion requires explicit fold/gap correction before approval.
        policy = BookingPolicy.objects.get(resource=proposal.resource)
        if not cancelled:
            interval(
                policy,
                start,
                end,
                start_fold=merged.get("start_fold"),
                end_fold=merged.get("end_fold"),
            )
        if not cancelled:
            _rights(
                actor,
                proposal.beneficiary,
                proposal.resource,
                merged,
                start,
                end,
                recurring=bool(proposal.rule.get("weekdays")),
            )
        change = RequestAdjustment.objects.create(
            occurrence=row,
            revision=proposal.revision,
            local_start=start.isoformat(),
            local_end=end.isoformat(),
            options=_serialize(merged),
            cancelled=cancelled,
            actor=actor,
            reason=reason,
        )
        proposal.revision += 1
        proposal.save(update_fields=["revision"])
        audit(
            actor,
            "booking.request_adjusted",
            subject=proposal.beneficiary,
            object_id=row.pk,
            reason=reason,
            details={"cancelled": cancelled},
        )
        return change


def create_approved(actor, resource_id, start, end, key, *, reason, **kwargs):
    with authorization_write():
        proposal = submit(actor, resource_id, start, end, key, **kwargs)
        return approve(actor, proposal.pk, proposal.revision, reason)
