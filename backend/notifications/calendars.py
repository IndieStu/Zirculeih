"""Minimal RFC-5545 subscriptions from current authorized booking projections."""

import hashlib
import json
import secrets
from datetime import UTC, timedelta

from accounts.authorization import authorization_write, require
from bookings.models import RequestOccurrence
from bookings.recurrence import current_booking
from bookings.services import require_active_actor, visible_bookings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone
from inventory.models import Category, Location
from inventory.services import descendants, tree_scope
from resources.services import resource_scope, visible_resources

from .models import CalendarFeed, CalendarRevision


def authorize(owner, scope, scope_id):
    require_active_actor(owner)
    if scope == "personal" and scope_id is None:
        return
    if scope == "organization" and scope_id is None:
        require(owner, "booking.read_all")
    elif scope == "resource" and scope_id:
        resource = visible_resources(owner).get(pk=scope_id)
        require(owner, "booking.read_all", resource_scope(resource))
    elif scope in {"category", "location"} and scope_id:
        model = Category if scope == "category" else Location
        node = model.objects.get(pk=scope_id, is_active=True)
        require(owner, "booking.read_all", tree_scope(node))
    else:
        raise PermissionDenied("Kein freigegebener Kalenderbereich.")


def create(owner, label, scope, scope_id=None, *, days=90):
    with authorization_write():
        authorize(owner, scope, scope_id)
        if not label.strip() or len(label) > 100 or not 1 <= days <= 366:
            raise ValidationError("Name und Gültigkeit zwischen 1 und 366 Tagen erforderlich.")
        if (
            CalendarFeed.objects.filter(
                owner=owner, revoked_at=None, expires_at__gt=timezone.now()
            ).count()
            >= 20
        ):
            raise ValidationError("Höchstens 20 aktive Kalenderzugänge je Konto.")
        raw = secrets.token_urlsafe(32)
        feed = CalendarFeed.objects.create(
            owner=owner,
            label=label,
            scope=scope,
            scope_id=scope_id,
            digest=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(days=days),
        )
        from accounts.services import audit

        audit(owner, "calendar.created", object_id=feed.pk)
        return feed, raw


def revoke(owner, feed_id):
    with authorization_write():
        require_active_actor(owner)
        feed = CalendarFeed.objects.get(pk=feed_id, owner=owner)
        feed.revoked_at = timezone.now()
        feed.save(update_fields=["revoked_at"])
        from accounts.services import audit

        audit(owner, "calendar.revoked", object_id=feed.pk)
        return feed


def regenerate(owner, feed_id):
    with authorization_write():
        feed = CalendarFeed.objects.get(pk=feed_id, owner=owner)
        authorize(owner, feed.scope, feed.scope_id)
        if feed.revoked_at or feed.expires_at <= timezone.now():
            raise ValidationError("Abgelaufenen Zugang neu anlegen.")
        raw = secrets.token_urlsafe(32)
        feed.digest = hashlib.sha256(raw.encode()).hexdigest()
        feed.save(update_fields=["digest"])
        from accounts.services import audit

        audit(owner, "calendar.regenerated", object_id=feed.pk)
        return feed, raw


def rows(owner, scope="personal", scope_id=None, *, start=None, end=None):
    authorize(owner, scope, scope_id)
    start = start or timezone.now() - timedelta(days=90)
    end = end or timezone.now() + timedelta(days=366)
    if end <= start or end - start > timedelta(days=732):
        raise ValidationError("Kalenderzeitraum ist zu groß.")
    result = visible_bookings(owner, operational=scope != "personal", start=start, end=end).filter(
        end__gt=start, start__lt=end, resource__in=visible_resources(owner)
    )
    if scope == "resource":
        result = result.filter(resource_id=scope_id)
    elif scope == "category":
        result = result.filter(resource__categories__in=descendants(Category, scope_id)).distinct()
    elif scope == "location":
        result = result.filter(resource__location_id__in=descendants(Location, scope_id))
    if result.count() > 5000:
        raise ValidationError("Zu viele Termine. Einen engeren Kalenderbereich wählen.")
    return result.select_related("resource").order_by("start", "id")


def logical_events(owner, scope, scope_id, *, start=None, end=None):
    bookings = list(rows(owner, scope, scope_id, start=start, end=end))
    ids = [b.pk for b in bookings]
    occurrences = RequestOccurrence.objects.filter(
        Q(booking_id__in=ids) | Q(exceptions__replacement_id__in=ids)
    ).distinct()
    mapping = {}
    for occurrence in occurrences:
        current = current_booking(occurrence)
        if current is None:
            current = occurrence.booking
            changes = {
                change.previous_id: change.replacement
                for change in occurrence.exceptions.select_related("replacement")
            }
            while current is not None and current.pk in changes:
                replacement = changes.pop(current.pk)
                if replacement is None:
                    break
                current = replacement
        members = [
            occurrence.booking_id,
            *occurrence.exceptions.values_list("replacement_id", flat=True),
        ]
        for pk in members:
            if pk:
                mapping[pk] = (occurrence.pk, current)
    result, seen = [], set()
    # Re-authorization of each replacement protects changed resource visibility and scope.
    permitted = {b.pk for b in rows(owner, scope, scope_id, start=start, end=end)}
    for booking in bookings:
        source, current = mapping.get(booking.pk, (booking.pk, booking))
        if source in seen or current is None or current.pk not in permitted:
            continue
        seen.add(source)
        result.append((source, current))
    return result


def escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold(line):
    """75 octets, preserving multibyte UTF-8 characters, including continuation space."""
    parts, current = [], b""
    for char in line:
        raw = char.encode("utf-8")
        if len(current) + len(raw) > 75:
            parts.append(current)
            current = b" "
        current += raw
    parts.append(current)
    return b"\r\n".join(parts)


def stamp(value):
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def serialize(owner, scope="personal", scope_id=None):
    with authorization_write():
        authorize(owner, scope, scope_id)
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Deelvo//Booking Calendar//DE",
            "CALSCALE:GREGORIAN",
        ]
        for source, booking in logical_events(owner, scope, scope_id):
            cancelled = booking.status in {"cancelled", "no_show"}
            properties = [
                "UID:" + str(source) + "@deelvo.invalid",
                "SUMMARY:" + escape(booking.resource.title),
                "LOCATION:" + escape(booking.resource.location_label),
                "STATUS:" + ("CANCELLED" if cancelled else "CONFIRMED"),
                "TRANSP:" + ("TRANSPARENT" if cancelled else "OPAQUE"),
                "CLASS:PRIVATE",
            ]
            if booking.start_date:
                properties += [
                    "DTSTART;VALUE=DATE:" + booking.start_date.strftime("%Y%m%d"),
                    "DTEND;VALUE=DATE:" + booking.end_date_exclusive.strftime("%Y%m%d"),
                ]
            else:
                properties += ["DTSTART:" + stamp(booking.start), "DTEND:" + stamp(booking.end)]
            digest = hashlib.sha256(json.dumps(properties, ensure_ascii=False).encode()).hexdigest()
            revision, created = CalendarRevision.objects.select_for_update().get_or_create(
                source=source, defaults={"fingerprint": digest, "modified_at": booking.updated_at}
            )
            if not created and revision.fingerprint != digest:
                revision.fingerprint = digest
                revision.sequence += 1
                revision.modified_at = timezone.now()
                revision.save()
            lines += [
                "BEGIN:VEVENT",
                *properties,
                "SEQUENCE:" + str(revision.sequence),
                "DTSTAMP:" + stamp(revision.modified_at),
                "LAST-MODIFIED:" + stamp(revision.modified_at),
                "END:VEVENT",
            ]
        lines += ["END:VCALENDAR"]
        return b"\r\n".join(fold(line) for line in lines) + b"\r\n"


def fetch(raw):
    if not isinstance(raw, str) or not 40 <= len(raw) <= 64:
        raise PermissionDenied
    with authorization_write():
        feed = CalendarFeed.objects.select_related("owner").get(
            digest=hashlib.sha256(raw.encode()).hexdigest(),
            revoked_at=None,
            expires_at__gt=timezone.now(),
        )
        return serialize(feed.owner, feed.scope, feed.scope_id)
