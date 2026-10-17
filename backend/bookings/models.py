import uuid

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import F, Q
from django.utils import timezone as dj_timezone


class BookingPolicy(models.Model):
    resource = models.OneToOneField(
        "resources.Resource", on_delete=models.PROTECT, primary_key=True
    )
    use_mode = models.CharField(
        max_length=20,
        choices=[("onsite", "Vor Ort ohne Ausgabe"), ("physical_loan", "Physische Ausleihe")],
        default="physical_loan",
    )
    time_mode = models.CharField(
        max_length=10, choices=[("slots", "Uhrzeiten"), ("days", "Kalendertage")], default="slots"
    )
    timezone = models.CharField(max_length=64, default="Europe/Berlin")
    granularity_minutes = models.PositiveIntegerField(default=15)
    min_duration_minutes = models.PositiveIntegerField(default=15)
    max_duration_minutes = models.PositiveIntegerField(default=480)
    min_days = models.PositiveIntegerField(default=1)
    max_days = models.PositiveIntegerField(default=14)
    max_horizon_days = models.PositiveIntegerField(default=90)
    lead_minutes = models.PositiveIntegerField(default=0)
    buffer_before_minutes = models.PositiveIntegerField(default=0)
    buffer_after_minutes = models.PositiveIntegerField(default=0)
    max_parallel = models.PositiveIntegerField(default=1)
    cancellation_notice_minutes = models.PositiveIntegerField(default=0)
    requires_qualification = models.BooleanField(default=False)
    requires_agreement = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(use_mode__in=["onsite", "physical_loan"]), name="booking_use_mode_valid"
            ),
            models.CheckConstraint(
                condition=Q(time_mode__in=["slots", "days"]), name="booking_time_mode_valid"
            ),
            models.CheckConstraint(
                condition=Q(
                    granularity_minutes__gte=1,
                    min_duration_minutes__gte=1,
                    max_duration_minutes__gte=F("min_duration_minutes"),
                    min_days__gte=1,
                    max_days__gte=F("min_days"),
                    max_parallel__gte=1,
                ),
                name="booking_policy_positive_limits",
            ),
        ]


class ScheduleOwner(models.Model):
    resource = models.ForeignKey(
        "resources.Resource", null=True, blank=True, on_delete=models.PROTECT
    )
    location = models.ForeignKey(
        "inventory.Location", null=True, blank=True, on_delete=models.PROTECT
    )
    category = models.ForeignKey(
        "inventory.Category", null=True, blank=True, on_delete=models.PROTECT
    )
    organization = models.BooleanField(default=False)
    purpose = models.CharField(
        max_length=10,
        choices=[
            ("usage", "Nutzung"),
            ("access", "Gebäudezugang"),
            ("opening", "Betreute Öffnung"),
            ("pickup", "Abholung"),
            ("return", "Rückgabe"),
        ],
    )

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        resource__isnull=False,
                        location__isnull=True,
                        category__isnull=True,
                        organization=False,
                    )
                    | Q(
                        resource__isnull=True,
                        location__isnull=False,
                        category__isnull=True,
                        organization=False,
                    )
                    | Q(
                        resource__isnull=True,
                        location__isnull=True,
                        category__isnull=False,
                        organization=False,
                    )
                    | Q(
                        resource__isnull=True,
                        location__isnull=True,
                        category__isnull=True,
                        organization=True,
                    )
                ),
                name="%(class)s_one_owner",
            ),
            models.CheckConstraint(
                condition=Q(purpose__in=["usage", "access", "opening", "pickup", "return"]),
                name="%(class)s_purpose_valid",
            ),
        ]


class ScheduleWindow(ScheduleOwner):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    weekday = models.PositiveSmallIntegerField(
        choices=list(
            enumerate(
                ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            )
        )
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    end_next_day = models.BooleanField(default=False)

    class Meta(ScheduleOwner.Meta):
        abstract = False
        ordering = ["weekday", "start_time", "id"]
        constraints = ScheduleOwner.Meta.constraints + [
            models.CheckConstraint(condition=Q(weekday__lte=6), name="schedule_weekday_valid"),
            models.CheckConstraint(
                condition=Q(end_next_day=True) | Q(end_time__gt=F("start_time")),
                name="schedule_nonempty_window",
            ),
        ]


class ScheduleException(ScheduleOwner):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    is_closed = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    end_next_day = models.BooleanField(default=False)

    class Meta(ScheduleOwner.Meta):
        abstract = False
        ordering = ["date", "id"]
        constraints = ScheduleOwner.Meta.constraints + [
            models.CheckConstraint(
                condition=Q(
                    is_closed=True,
                    start_time__isnull=True,
                    end_time__isnull=True,
                    end_next_day=False,
                )
                | (
                    Q(is_closed=False, start_time__isnull=False, end_time__isnull=False)
                    & (Q(end_next_day=True) | Q(end_time__gt=F("start_time")))
                ),
                name="schedule_exception_shape",
            ),
        ]


class ResourceBlock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(
        "resources.Resource", null=True, blank=True, on_delete=models.PROTECT
    )
    location = models.ForeignKey(
        "inventory.Location", null=True, blank=True, on_delete=models.PROTECT
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    reason = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(resource__isnull=False, location__isnull=True)
                | Q(resource__isnull=True, location__isnull=False),
                name="block_one_owner",
            ),
            models.CheckConstraint(condition=Q(end__gt=F("start")), name="block_positive_interval"),
        ]


class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_bookings"
    )
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    resource = models.ForeignKey("resources.Resource", on_delete=models.PROTECT)
    unit = models.ForeignKey("resources.ResourceUnit", on_delete=models.PROTECT)
    start = models.DateTimeField()
    end = models.DateTimeField()
    start_date = models.DateField(null=True, blank=True)
    end_date_exclusive = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=64)
    status = models.CharField(
        max_length=12,
        choices=[
            ("confirmed", "Bestätigt"),
            ("active", "Aktiv"),
            ("completed", "Abgeschlossen"),
            ("cancelled", "Storniert"),
            ("no_show", "Nicht abgeholt"),
        ],
        default="confirmed",
    )
    policy_snapshot = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        ordering = ["start", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end__gt=F("start")), name="booking_positive_interval"
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=["confirmed", "active", "completed", "cancelled", "no_show"]
                ),
                name="booking_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(start_date__isnull=True, end_date_exclusive__isnull=True)
                | Q(
                    start_date__isnull=False,
                    end_date_exclusive__isnull=False,
                    end_date_exclusive__gt=F("start_date"),
                ),
                name="booking_dates_shape",
            ),
        ]


class AllocationClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="claim")
    unit = models.ForeignKey("resources.ResourceUnit", on_delete=models.PROTECT)
    during = DateTimeRangeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="booking_exclusive_unit_interval",
                expressions=[("unit", RangeOperators.EQUAL), ("during", RangeOperators.OVERLAPS)],
                condition=Q(is_active=True),
            )
        ]


class BookingIncident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="incidents")
    code = models.CharField(max_length=40)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=dj_timezone.now)


class IdempotencyRecord(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operation = models.CharField(max_length=30)
    key = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "operation", "key"], name="booking_idempotency_unique"
            )
        ]


class BundleReservation(models.Model):
    expected_resources = models.JSONField(default=list)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    root = models.OneToOneField(
        Booking, on_delete=models.PROTECT, related_name="bundle_reservation"
    )
    created_at = models.DateTimeField(default=dj_timezone.now)


class BundleMember(models.Model):
    reservation = models.ForeignKey(
        BundleReservation, on_delete=models.PROTECT, related_name="members"
    )
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="bundle_member")
    required = models.BooleanField(default=True)
