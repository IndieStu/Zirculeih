"""Transactional mail outbox. No SMTP runs during a booking/domain mutation."""

import base64
import hashlib
import json
import logging
from datetime import timedelta
from string import Template
from uuid import uuid4

from accounts.authorization import authorization_write, require
from accounts.models import ActionToken, User
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import Delivery, NotificationPreference, NotificationSettings, NotificationTemplate

TITLES = {
    "booking.confirmed": "Reservierung bestätigt",
    "booking.cancelled": "Reservierung storniert",
    "booking.requested": "Antrag eingegangen",
    "booking.request_approved": "Antrag genehmigt",
    "booking.request_rejected": "Antrag abgelehnt",
    "booking.request_cancelled": "Antrag zurückgezogen / storniert",
    "booking.occurrence_exception": "Reservierung geändert",
    "booking.request_adjusted": "Angefragter Termin geändert",
    "pickup": "Erinnerung an die Abholung",
    "return": "Erinnerung an die Rückgabe",
    "overdue": "Rückgabe überfällig",
    "maintenance": "Reservierung bitte mit dem Team klären",
    "qualification.issued": "Einweisung dokumentiert",
    "loan.extended": "Ausleihe verlängert",
    "loan.checked_out": "Ausgabe bestätigt",
    "loan.returned": "Rückgabe erfasst",
    "auth.verify": "E-Mail bestätigen",
    "auth.reset": "Passwort zurücksetzen",
    "auth.invite": "Einladung zu Deelvo",
}


def _cipher(secret=None):
    key = hashlib.sha256(
        b"deelvo-mail-outbox-v1\0" + (secret or settings.SECRET_KEY).encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def decrypt(payload):
    for secret in [settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS]:
        try:
            return json.loads(_cipher(secret).decrypt(bytes(payload)))
        except InvalidToken:
            continue
    raise ValidationError("outbox_key_unavailable")


def configuration():
    return NotificationSettings.objects.get_or_create(pk=1)[0]


def validate_template(kind, locale, subject, body):
    if kind not in TITLES or locale not in {"de", "en"}:
        raise ValidationError("Unbekannter Nachrichtentyp oder Sprache.")
    if not subject.strip() or len(subject) > 200 or any(c in subject for c in "\r\n$"):
        raise ValidationError("Betreff als kurze feste Textzeile ohne Variablen eingeben.")
    if not body.strip() or len(body) > 10000:
        raise ValidationError("Nachrichtentext fehlt oder ist zu lang.")
    template = Template(body)
    if not template.is_valid() or set(template.get_identifiers()) - {"url", "when"}:
        raise ValidationError("Erlaubte Platzhalter: ${url}, ${when}.")
    if "url" not in template.get_identifiers():
        raise ValidationError("Der Link ${url} muss enthalten sein.")


def save_template(actor, kind, locale, subject, body, revision=None):
    with authorization_write():
        require(actor, "system.configure")
        validate_template(kind, locale, subject, body)
        row = NotificationTemplate.objects.filter(kind=kind, locale=locale).first()
        if row and row.revision != revision:
            raise ValidationError("Vorlage wurde inzwischen geändert.")
        row = row or NotificationTemplate(kind=kind, locale=locale)
        row.subject, row.body = subject, body
        row.revision += 1
        row.full_clean()
        row.save()
        from accounts.services import audit

        audit(actor, "notification.template_saved", object_id=row.pk)
        return row


def enqueue(
    user, kind, key, *, url, when="", booking=None, request=None, token_digest="", context=None
):
    if kind not in TITLES:
        raise ValidationError("Unbekannter Nachrichtentyp.")
    pref = NotificationPreference.objects.get_or_create(user=user)[0]
    template = NotificationTemplate.objects.filter(kind=kind, locale=pref.locale).first()
    english = {
        "auth.verify": "Verify your email",
        "auth.reset": "Reset your password",
        "auth.invite": "Invitation to Deelvo",
        "pickup": "Pickup reminder",
        "return": "Return reminder",
        "overdue": "Return overdue",
        "maintenance": "Please contact the team about your reservation",
        "qualification.issued": "Qualification recorded",
        "booking.confirmed": "Reservation confirmed",
        "booking.cancelled": "Reservation cancelled",
        "booking.requested": "Request received",
        "booking.request_approved": "Request approved",
        "booking.request_rejected": "Request rejected",
        "booking.request_cancelled": "Request withdrawn / cancelled",
        "booking.request_adjusted": "Requested occurrence changed",
        "booking.occurrence_exception": "Reservation changed",
        "loan.extended": "Loan extended",
        "loan.checked_out": "Checkout recorded",
        "loan.returned": "Return recorded",
    }
    title = english.get(kind, "Reservation update") if pref.locale == "en" else TITLES[kind]
    subject = template.subject if template else "Deelvo · " + title
    body = (
        template.body
        if template
        else title
        + (
            ".\n${when}\n\nDetails in your account:\n${url}\n"
            if pref.locale == "en"
            else ".\n${when}\n\nDetails in deinem Konto:\n${url}\n"
        )
    )
    # Every rendered message is bounded and encrypted; no raw account/feed token in SQL/logs.
    payload = dict(
        recipient=user.email,
        subject=subject,
        body=Template(body).substitute(url=url, when=when),
        context=context or {},
    )
    if kind == "booking.requested":
        payload["body"] += (
            "\nYour request has not reserved capacity.\n"
            if pref.locale == "en"
            else "\nDer Antrag reserviert noch keine Kapazität.\n"
        )
    encrypted = _cipher().encrypt(json.dumps(payload).encode())
    return Delivery.objects.get_or_create(
        key=key,
        defaults=dict(
            user=user,
            kind=kind,
            payload=encrypted,
            booking=booking,
            request=request,
            action_token_digest=token_digest,
            next_attempt=timezone.now(),
            created_at=timezone.now(),
        ),
    )[0]


def absolute(path):
    return settings.PUBLIC_BASE_URL + path


def from_event(event):
    """Explicit allowlist consumes only domain-service audit events in the same transaction."""
    kind = event.action
    if kind not in TITLES or not event.subject_id or kind.startswith("auth."):
        return
    booking = proposal = None
    path = "/buchungen/"
    if kind in {"booking.confirmed", "booking.cancelled", "loan.extended"}:
        from bookings.models import Booking

        if kind == "loan.extended":
            from lending.models import LoanLine

            line = LoanLine.objects.get(pk=event.object_id)
            booking = line.booking
        else:
            booking = Booking.objects.get(pk=event.object_id)
        path = reverse("booking_detail", args=[booking.pk])
    elif kind.startswith("booking.request") or kind == "booking.occurrence_exception":
        from bookings.models import RequestOccurrence, ReservationRequest

        if kind in {"booking.request_adjusted", "booking.occurrence_exception"}:
            proposal = RequestOccurrence.objects.get(pk=event.object_id).request
        else:
            proposal = ReservationRequest.objects.get(pk=event.object_id)
        path = reverse("request_detail", args=[proposal.pk])
    elif kind == "qualification.issued":
        path = "/konto/"
    elif kind.startswith("loan."):
        path = reverse("loan_detail", args=[event.object_id])
    enqueue(
        event.subject,
        kind,
        "audit:" + str(event.pk),
        url=absolute(path),
        booking=booking,
        request=proposal,
    )


def _relevant(row, payload):
    user = User.objects.get(pk=row.user_id)
    if not user.is_active or payload["recipient"] != user.email:
        return False
    if row.action_token_digest:
        return ActionToken.objects.filter(
            digest=row.action_token_digest,
            user=user,
            password_hash=user.password,
            expires_at__gt=timezone.now(),
        ).exists()
    if not user.email_verified_at:
        return False
    if row.kind == "qualification.issued":
        return (
            configuration().qualification_enabled
            and NotificationPreference.objects.get_or_create(user=user)[0].qualification_email
        )
    if row.booking_id:
        from bookings.services import read_booking

        read_booking(user, row.booking_id)
        from bookings.models import BundleMember, RequestOccurrence

        if row.kind == "booking.cancelled":
            member = BundleMember.objects.filter(booking=row.booking).first()
            if member and member.reservation.root_id != row.booking_id:
                return False
            occurrence = RequestOccurrence.objects.filter(booking=row.booking).first()
            if occurrence and occurrence.request.status == "cancelled":
                return False
            from bookings.models import OccurrenceException

            if OccurrenceException.objects.filter(previous=row.booking).exists():
                return False
        if row.kind == "booking.confirmed":
            if row.booking.status not in {"confirmed", "active"}:
                return False
            member = BundleMember.objects.filter(booking=row.booking).first()
            if member and member.reservation.root_id != row.booking_id:
                return False
            if RequestOccurrence.objects.filter(booking=row.booking).exists():
                return False  # One approval summary instead of one message per occurrence.
        if row.kind == "pickup":
            return (
                row.booking.status == "confirmed"
                and row.booking.appointment.pickup_at > timezone.now()
                and row.booking.appointment.pickup_at.isoformat()
                == payload["context"].get("moment")
            )
        if row.kind in {"return", "overdue"}:
            from lending.models import LoanLine

            line = LoanLine.objects.filter(
                booking=row.booking,
                returned_at__isnull=True,
                expected_return=payload["context"].get("moment"),
            ).first()
            if line is None:
                return False
            if row.kind == "return":
                return line.expected_return > timezone.now()
            bucket = int(
                (timezone.now() - line.expected_return).total_seconds()
                // (configuration().overdue_repeat_hours * 3600)
            )
            return line.expected_return <= timezone.now() and bucket == payload["context"].get(
                "bucket"
            )
    if row.request_id:
        from bookings.recurrence import read

        read(user, row.request_id)
    return True


def deliver_one(delivery_id, *, sender=None):
    """Lease/attempt limit prevents concurrent workers sending the same message."""
    now = timezone.now()
    with transaction.atomic():
        row = Delivery.objects.select_for_update().get(pk=delivery_id)
        if row.status not in {"pending", "sending"} or row.next_attempt > now:
            return False
        if row.status == "sending" and row.lease_until and row.lease_until > now:
            return False
        cap = configuration().max_attempts
        if row.attempts >= cap:
            row.status = "failed"
            row.lease_id = row.lease_until = None
            row.save(update_fields=["status", "lease_id", "lease_until"])
            return False
        row.status, row.lease_id, row.lease_until = "sending", uuid4(), now + timedelta(minutes=2)
        row.attempts += 1
        row.save(update_fields=["status", "lease_id", "lease_until", "attempts"])
        lease = row.lease_id
    with authorization_write():
        row = Delivery.objects.select_for_update().get(pk=delivery_id)
        if row.lease_id != lease:
            return False
        try:
            payload = decrypt(row.payload)
            if not _relevant(row, payload):
                row.status = "skipped"
            else:
                headers = {"Message-ID": f"<deelvo-{row.pk}@notifications.invalid>"}
                if sender:
                    sender(
                        payload["subject"],
                        payload["body"],
                        settings.DEFAULT_FROM_EMAIL,
                        [payload["recipient"]],
                    )
                else:
                    EmailMessage(
                        payload["subject"],
                        payload["body"],
                        settings.DEFAULT_FROM_EMAIL,
                        [payload["recipient"]],
                        headers=headers,
                    ).send(fail_silently=False)
                row.status, row.sent_at = "sent", timezone.now()
        except PermissionDenied:
            row.status = "skipped"
        except Exception:
            # Never persist SMTP responses, addresses, credentials, tokens or raw exception text.
            row.error_code = "delivery_failed"
            row.status = "failed" if row.attempts >= configuration().max_attempts else "pending"
            row.next_attempt = timezone.now() + timedelta(minutes=min(360, 2**row.attempts))
            logging.getLogger("deelvo.mail").warning(
                "mail_delivery_failed", extra={"event": "mail_delivery_failed"}
            )
        row.lease_id = row.lease_until = None
        row.save()
        return row.status == "sent"


def deliver_due(limit=100):
    if not 1 <= limit <= 1000:
        raise ValidationError("Batchgröße 1–1000 erforderlich.")
    now = timezone.now()
    ids = Delivery.objects.filter(
        Q(status="pending", next_attempt__lte=now) | Q(status="sending", lease_until__lte=now)
    ).values_list("pk", flat=True)[:limit]
    return sum(deliver_one(pk) for pk in list(ids))


def retry(actor, delivery_id):
    with authorization_write():
        require(actor, "system.configure")
        row = Delivery.objects.select_for_update().get(pk=delivery_id)
        if not row.payload:
            raise ValidationError("Nachrichteninhalt wurde bereits entfernt; Vorgang neu anstoßen.")
        if row.status != "failed":
            raise ValidationError(
                "Nur fehlgeschlagene Zustellungen können erneut freigegeben werden."
            )
        row.status, row.attempts, row.next_attempt, row.error_code = (
            "pending",
            0,
            timezone.now(),
            "",
        )
        row.save()
        from accounts.services import audit

        audit(actor, "notification.retry", object_id=row.pk)


def save_settings(actor, data):
    with authorization_write():
        require(actor, "system.configure")
        row = configuration()
        fields = {
            "pickup_hours",
            "return_hours",
            "overdue_repeat_hours",
            "max_attempts",
            "qualification_enabled",
        }
        if set(data) - fields:
            raise ValidationError("Unbekannte Nachrichteneinstellung.")
        for key, value in data.items():
            setattr(row, key, value)
        row.full_clean()
        row.save()
        from accounts.services import audit

        audit(actor, "notification.settings_saved", object_id=row.pk)
        return row


def purge_payloads(days=30):
    if not 1 <= days <= 3660:
        raise ValidationError("Aufbewahrungsfrist zwischen 1 und 3660 Tagen angeben.")
    return (
        Delivery.objects.filter(
            status__in=["sent", "skipped", "failed"],
            created_at__lt=timezone.now() - timedelta(days=days),
        )
        .exclude(payload=b"")
        .update(payload=b"")
    )
