import hashlib
import json
from datetime import timedelta
from uuid import UUID

from accounts.authorization import allowed, authorization_write, require
from accounts.models import User
from accounts.services import audit
from bookings import services as bookings
from bookings.models import AllocationClaim, Booking, BookingPolicy
from bookings.time_rules import zone
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.utils import timezone
from inventory.models import Asset
from resources.models import ResourceUnit
from resources.services import resource_scope

from .agreements import required_versions
from .models import Appointment, Extension, IdentityCheck, Loan, LoanLine, Operation


def identity_check(actor, user_id):
    with authorization_write():
        require(actor, "loan.inspect_identity")
        user = User.objects.get(pk=user_id, is_active=True, email_verified_at__isnull=False)
        row, created = IdentityCheck.objects.get_or_create(user=user, defaults={"actor": actor})
        if created:
            audit(actor, "loan.identity_checked", subject=user, object_id=row.pk)
        return row


def operation(actor, kind, key, payload):
    try:
        key = UUID(str(key))
    except (ValueError, TypeError) as exc:
        raise ValidationError("Ungültiger Wiederholungsschlüssel.") from exc
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    prior = Operation.objects.filter(actor=actor, kind=kind, key=key).first()
    if prior:
        if prior.payload_hash != digest:
            raise ValidationError("Wiederholungsschlüssel hat andere Eingaben.")
        return key, digest, read_loan(actor, prior.loan_id)
    return key, digest, None


def read_loan(actor, loan_id):
    bookings.require_active_actor(actor)
    row = Loan.objects.prefetch_related("lines__booking__resource").get(pk=loan_id)
    if row.borrower_id != actor.pk:
        for line in row.lines.all():
            require(actor, "loan.read", resource_scope(line.booking.resource))
    return row


def visible_loans(actor, operational=False):
    bookings.require_active_actor(actor)
    rows = Loan.objects.prefetch_related("lines__booking__resource").order_by("-issued_at")
    if not operational:
        return rows.filter(borrower=actor)
    ids = [
        r.pk
        for r in rows
        if all(
            allowed(actor, "loan.read", resource_scope(line.booking.resource))
            for line in r.lines.all()
        )
    ]
    return rows.filter(pk__in=ids)


def checkout(actor, borrower_id, booking_ids, key, *, checks, spontaneous=None):
    """All prepared scans are revalidated. One atomic loan, no scan-side writes."""
    with authorization_write():
        bookings.require_active_actor(actor)
        ids = sorted(set(str(x) for x in booking_ids))
        if len(ids) != len(booking_ids) or len(ids) + len(spontaneous or []) not in range(1, 51):
            raise ValidationError("1 bis 50 eindeutige Gegenstände auswählen.")
        key, digest, prior = operation(
            actor,
            "checkout",
            key,
            {
                "borrower": borrower_id,
                "bookings": ids,
                "checks": checks,
                "spontaneous": spontaneous or [],
            },
        )
        if prior:
            return prior
        borrower = User.objects.get(pk=borrower_id)
        if not borrower.is_active or not borrower.borrower_profile_complete:
            raise ValidationError("Vollständiges freigegebenes Ausleihprofil erforderlich.")
        if not IdentityCheck.objects.filter(user=borrower).exists():
            raise ValidationError("Erste Ausweisprüfung erforderlich.")
        for request in spontaneous or []:
            unit = ResourceUnit.objects.select_related("resource").get(pk=request["unit_id"])
            require(actor, "loan.checkout", resource_scope(unit.resource))
            row = bookings.confirm(
                actor,
                unit.resource_id,
                request["start"],
                request["end"],
                request["key"],
                beneficiary=borrower,
                unit_id=unit.pk,
                pickup_at=request["pickup_at"],
                return_at=request["return_at"],
                walk_in=True,
                start_fold=request.get("start_fold"),
                end_fold=request.get("end_fold"),
            )
            ids.append(str(row.pk))
        rows = list(
            Booking.objects.select_for_update(of=("self",))
            .filter(pk__in=ids)
            .select_related("resource__location", "unit__asset")
        )
        if len(rows) != len(ids):
            raise PermissionDenied
        now = timezone.now()
        evidence: set[str] = set()
        for row in rows:
            scope = resource_scope(row.resource)
            require(actor, "loan.checkout", scope)
            require(actor, "loan.read", scope)
            if (
                row.beneficiary_id != borrower.pk
                or row.policy_snapshot.get("use_mode") != "physical_loan"
                or row.status != "confirmed"
            ):
                raise ValidationError("Keine passende bestätigte Ausleihreservierung.")
            unit = ResourceUnit.objects.select_for_update(of=("self",)).get(pk=row.unit_id)
            if (
                LoanLine.objects.filter(unit=unit).exists()
                and LoanLine.objects.filter(booking=row).exists()
            ):
                raise ValidationError("Diese Reservierung wurde bereits ausgegeben.")
            if LoanLine.objects.filter(unit=unit, returned_at__isnull=True).exists():
                raise ValidationError("Gegenstand ist noch tatsächlich ausgegeben.")
            appointment = Appointment.objects.get(booking=row)
            if not row.start <= now < row.end or now < appointment.pickup_at:
                raise ValidationError(
                    "Die Ausgabe liegt nicht im reservierten Zeitraum/Abholtermin."
                )
            policy = BookingPolicy.objects.get(resource=row.resource)
            # Recheck current complete profiles, all gates, availability and current pickup window.
            if (
                policy.time_mode != row.policy_snapshot["time_mode"]
                or policy.timezone != row.timezone
            ):
                raise ValidationError(
                    "Zeitmodell wurde geändert; Reservierung muss geklärt werden."
                )
            start = (
                row.start_date
                if row.start_date
                else row.start.astimezone(zone(row.timezone)).replace(tzinfo=None)
            )
            end = (
                row.end_date_exclusive - timedelta(days=1)
                if row.end_date_exclusive
                else row.end.astimezone(zone(row.timezone)).replace(tzinfo=None)
            )
            result = bookings.evaluate(
                actor,
                borrower,
                row.resource,
                policy,
                start,
                end,
                unit_id=unit.pk,
                lock=True,
                existing_booking=row,
                pickup_at=now,
                return_at=appointment.return_at,
                start_fold=row.start.astimezone(zone(row.timezone)).fold,
                end_fold=row.end.astimezone(zone(row.timezone)).fold,
            )
            if result.code != "available":
                raise ValidationError(result.code)
            detail = checks.get(str(row.pk), checks.get(str(row.unit_id), {}))
            if detail.get("condition") != row.unit.asset.condition or not detail.get(
                "accessories_checked"
            ):
                raise ValidationError("Aktuellen Zustand und Zubehör bewusst prüfen.")
            if len(detail.get("accessories", "")) > 2000:
                raise ValidationError("Zubehörtext zu lang.")
            evidence.update(str(v.pk) for v in required_versions(row.resource, row.unit.asset))
        loan = Loan.objects.create(
            borrower=borrower,
            actor=actor,
            evidence={
                "versions": sorted(evidence),
                "borrower_profile_revision": borrower.profile_revision,
                "identity_check": str(IdentityCheck.objects.get(user=borrower).pk),
            },
        )
        try:
            for row in sorted(rows, key=lambda b: str(b.unit_id)):
                detail = checks.get(str(row.pk), checks.get(str(row.unit_id), {}))
                LoanLine.objects.create(
                    loan=loan,
                    booking=row,
                    unit=row.unit,
                    asset=row.unit.asset,
                    expected_return=row.appointment.return_at,
                    issue_condition=detail["condition"],
                    accessories=detail.get("accessories", ""),
                )
                row.status = "active"
                row.revision += 1
                row.updated_at = now
                row.save()
            Operation.objects.create(
                actor=actor, kind="checkout", key=key, payload_hash=digest, loan=loan
            )
            audit(
                actor,
                "loan.checked_out",
                subject=borrower,
                object_id=loan.pk,
                details={"bookings": ids, "workflow": "staffed"},
            )
        except IntegrityError as exc:
            raise ValidationError("Eine Einheit wurde inzwischen ausgegeben.") from exc
        return loan


def return_lines(actor, loan_id, selections, key):
    with authorization_write():
        bookings.require_active_actor(actor)
        key, digest, prior = operation(
            actor, "return", key, {"loan": loan_id, "selections": selections}
        )
        if prior:
            return prior
        loan = Loan.objects.select_for_update(of=("self",)).get(pk=loan_id)
        rows = list(
            LoanLine.objects.select_for_update(of=("self",))
            .filter(loan=loan, pk__in=selections)
            .select_related("booking__resource", "asset")
        )
        if not rows or len(rows) != len(selections):
            raise PermissionDenied
        now = timezone.now()
        for line in rows:
            require(actor, "loan.return", resource_scope(line.booking.resource))
            if line.returned_at:
                raise ValidationError("Gegenstand ist bereits zurückgenommen.")
            data = selections[str(line.pk)]
            if data.get("condition") not in {
                "good",
                "worn",
                "damaged",
                "inspection",
            } or not data.get("accessories_checked"):
                raise ValidationError("Rückgabezustand und Zubehörprüfung erforderlich.")
            note = data.get("note", "")
            if len(note) > 2000:
                raise ValidationError("Notiz zu lang.")
            ResourceUnit.objects.select_for_update(of=("self",)).get(pk=line.unit_id)
            line.returned_at, line.returned_by = now, actor
            line.return_condition, line.return_note = data["condition"], note
            line.revision += 1
            line.save()
            asset = Asset.objects.select_for_update(of=("self",)).get(pk=line.asset_id)
            before_condition, before_lifecycle = asset.condition, asset.lifecycle
            asset.condition = line.return_condition
            if asset.condition in {"damaged", "inspection"}:
                asset.lifecycle = "maintenance"
            asset.revision += 1
            asset.updated_at = now
            asset.save(update_fields=["condition", "lifecycle", "revision", "updated_at"])
            booking = Booking.objects.select_for_update(of=("self",)).get(pk=line.booking_id)
            booking.status = "completed"
            booking.revision += 1
            booking.updated_at = now
            booking.save()
            AllocationClaim.objects.filter(booking=booking).update(is_active=False)
            if (before_condition, before_lifecycle) != (asset.condition, asset.lifecycle):
                from bookings.integrity import asset_changed

                asset_changed(asset.pk)
            audit(
                actor,
                "asset.return_condition",
                subject=loan.borrower,
                object_id=asset.pk,
                details={
                    "loan_line": str(line.pk),
                    "before_condition": before_condition,
                    "after_condition": asset.condition,
                    "before_lifecycle": before_lifecycle,
                    "after_lifecycle": asset.lifecycle,
                },
            )
            audit(
                actor,
                "loan.line_returned",
                subject=loan.borrower,
                object_id=line.pk,
                details={"condition": line.return_condition, "note": note},
            )
        if not loan.lines.filter(returned_at__isnull=True).exists():
            loan.closed_at = now
            loan.save(update_fields=["closed_at"])
        Operation.objects.create(
            actor=actor, kind="return", key=key, payload_hash=digest, loan=loan
        )
        return loan


def mark_overdue():
    with authorization_write():
        now = timezone.now()
        rows = LoanLine.objects.filter(returned_at__isnull=True, expected_return__lt=now)
        for line in rows:
            endangered = Booking.objects.filter(
                unit=line.unit, status__in=["confirmed", "active"]
            ).exclude(pk=line.booking_id)
            bookings.flag_incidents(endangered, "overdue_custody")
        return rows.count()


def extend_line(actor, line_id, end, return_at, revision, reason, *, end_fold=None):
    from bookings.time_rules import interval
    from psycopg.types.range import Range

    with authorization_write():
        line = (
            LoanLine.objects.select_for_update(of=("self",))
            .select_related("booking__resource", "loan__borrower")
            .get(pk=line_id)
        )
        row = Booking.objects.select_for_update(of=("self",)).get(pk=line.booking_id)
        require(actor, "loan.extend", resource_scope(row.resource))
        if line.returned_at or row.revision != revision or not reason.strip() or len(reason) > 500:
            raise ValidationError("Aktuelle offene Ausleihe, Revision und Grund erforderlich.")
        policy = BookingPolicy.objects.get(resource=row.resource)
        if policy.time_mode != row.policy_snapshot["time_mode"] or policy.timezone != row.timezone:
            raise ValidationError("Geändertes Zeitmodell muss geklärt werden.")
        start = (
            row.start_date
            if row.start_date
            else row.start.astimezone(zone(row.timezone)).replace(tzinfo=None)
        )
        s, e, _, _, end_date = interval(
            policy,
            start,
            end,
            start_fold=row.start.astimezone(zone(row.timezone)).fold,
            end_fold=end_fold,
        )
        if e <= row.end or return_at <= line.expected_return or return_at <= timezone.now():
            raise ValidationError("Verlängerung muss die Rückgabe in die Zukunft verschieben.")
        result = bookings.evaluate(
            actor,
            line.loan.borrower,
            row.resource,
            policy,
            start,
            end,
            unit_id=line.unit_id,
            lock=True,
            existing_booking=row,
            pickup_at=row.appointment.pickup_at,
            return_at=return_at,
            start_fold=row.start.astimezone(zone(row.timezone)).fold,
            end_fold=end_fold,
        )
        if result.code != "available":
            raise ValidationError(result.code)
        Extension.objects.create(
            booking=row,
            actor=actor,
            before_end=row.end,
            after_end=e,
            before_date=row.end_date_exclusive,
            after_date=end_date,
            booking_revision=row.revision + 1,
            reason=reason,
            policy_snapshot=bookings.policy_snapshot(policy),
        )
        row.end, row.end_date_exclusive = e, end_date
        row.revision += 1
        row.updated_at = timezone.now()
        row.save()
        claim = AllocationClaim.objects.select_for_update(of=("self",)).get(booking=row)
        claim.during = Range(
            claim.during.lower,
            e + timedelta(minutes=row.policy_snapshot["buffer_after_minutes"]),
            "[)",
        )
        claim.save()
        Appointment.objects.filter(booking=row).update(return_at=return_at)
        line.expected_return = return_at
        line.revision += 1
        line.save()
        audit(actor, "loan.extended", subject=line.loan.borrower, object_id=line.pk, reason=reason)
        return line


def pickup_bookings(actor):
    bookings.require_active_actor(actor)
    rows = Booking.objects.filter(
        status="confirmed", policy_snapshot__use_mode="physical_loan", loan_line__isnull=True
    ).select_related("resource", "appointment")
    ids = [
        row.pk
        for row in rows
        if allowed(actor, "loan.read", resource_scope(row.resource))
        and allowed(actor, "loan.checkout", resource_scope(row.resource))
    ]
    return rows.filter(pk__in=ids)


def no_show(actor, booking_id, revision, reason):
    with authorization_write():
        row = (
            Booking.objects.select_for_update(of=("self",))
            .select_related("resource", "appointment")
            .get(pk=booking_id)
        )
        require(actor, "booking.manage_all", resource_scope(row.resource))
        require(actor, "loan.checkout", resource_scope(row.resource))
        if (
            row.policy_snapshot.get("use_mode") != "physical_loan"
            or row.status != "confirmed"
            or row.revision != revision
            or not reason.strip()
            or len(reason) > 500
        ):
            raise ValidationError("Aktuelle bestätigte Ausleihreservierung und Grund erforderlich.")
        if (
            timezone.now() < row.appointment.pickup_at
            or LoanLine.objects.filter(booking=row).exists()
        ):
            raise ValidationError("Abholtermin noch nicht erreicht oder bereits ausgegeben.")
        row.status = "no_show"
        row.revision += 1
        row.updated_at = timezone.now()
        row.save()
        AllocationClaim.objects.filter(booking=row).update(is_active=False)
        audit(actor, "loan.no_show", subject=row.beneficiary, object_id=row.pk, reason=reason)
        return row
