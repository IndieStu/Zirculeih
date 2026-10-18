import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class NotificationSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    pickup_hours = models.PositiveIntegerField(default=24)
    return_hours = models.PositiveIntegerField(default=24)
    overdue_repeat_hours = models.PositiveIntegerField(default=24)
    max_attempts = models.PositiveIntegerField(default=5)
    qualification_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    id=1,
                    pickup_hours__lte=8760,
                    return_hours__lte=8760,
                    overdue_repeat_hours__gte=1,
                    overdue_repeat_hours__lte=8760,
                    max_attempts__gte=1,
                    max_attempts__lte=10,
                ),
                name="notification_config_bounds",
            )
        ]


class NotificationTemplate(models.Model):
    kind = models.CharField(max_length=40)
    locale = models.CharField(max_length=10, default="de")
    subject = models.CharField(max_length=200)
    body = models.TextField(max_length=10000)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "locale"], name="notification_template_kind_locale"
            )
        ]


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.PROTECT
    )
    qualification_email = models.BooleanField(default=True)
    locale = models.CharField(
        max_length=2, choices=[("de", "Deutsch"), ("en", "English")], default="de"
    )


class Delivery(models.Model):
    """Encrypted immutable message envelope; SMTP status is separate from domain state."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    key = models.CharField(max_length=240, unique=True)
    kind = models.CharField(max_length=40)
    payload = models.BinaryField()
    booking = models.ForeignKey("bookings.Booking", null=True, on_delete=models.PROTECT)
    request = models.ForeignKey("bookings.ReservationRequest", null=True, on_delete=models.PROTECT)
    action_token_digest = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=10,
        default="pending",
        choices=[
            ("pending", "Ausstehend"),
            ("sending", "In Zustellung"),
            ("sent", "Übergeben"),
            ("failed", "Fehlgeschlagen"),
            ("skipped", "Nicht mehr relevant"),
        ],
    )
    attempts = models.PositiveIntegerField(default=0)
    next_attempt = models.DateTimeField(default=timezone.now)
    lease_until = models.DateTimeField(null=True)
    lease_id = models.UUIDField(null=True)
    error_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["status", "next_attempt"], name="delivery_due")]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["pending", "sending", "sent", "failed", "skipped"]),
                name="delivery_state_valid",
            )
        ]


class CalendarFeed(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    label = models.CharField(max_length=100)
    scope = models.CharField(
        max_length=20,
        choices=[
            ("personal", "Meine Vorgänge"),
            ("resource", "Artikel / Raum"),
            ("category", "Kategorie"),
            ("location", "Standort"),
            ("organization", "Berechtigte Organisationsübersicht"),
        ],
    )
    scope_id = models.UUIDField(null=True)
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(scope__in=["personal", "organization"], scope_id__isnull=True)
                | Q(scope__in=["resource", "category", "location"], scope_id__isnull=False),
                name="calendar_feed_scope_shape",
            )
        ]


class CalendarRevision(models.Model):
    """Stable logical occurrence identity and monotonic publication revision."""

    source = models.UUIDField(primary_key=True)
    fingerprint = models.CharField(max_length=64)
    sequence = models.PositiveIntegerField(default=0)
    modified_at = models.DateTimeField(default=timezone.now)
