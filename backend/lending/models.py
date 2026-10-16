import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Agreement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=20,
        choices=[
            ("general", "Allgemeine Ausleihe"),
            ("insurance", "Haftpflichtbestätigung"),
            ("additional", "Zusatzvereinbarung"),
        ],
    )
    is_active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title


class AgreementVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agreement = models.ForeignKey(Agreement, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    text = models.TextField(max_length=50000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agreement", "number"], name="agreement_version_unique")
        ]


class AgreementAssignment(models.Model):
    agreement = models.ForeignKey(Agreement, on_delete=models.PROTECT)
    resource = models.ForeignKey(
        "resources.Resource", null=True, blank=True, on_delete=models.PROTECT
    )
    asset = models.ForeignKey("inventory.Asset", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(resource__isnull=False, asset__isnull=True)
                | Q(resource__isnull=True, asset__isnull=False),
                name="agreement_one_target",
            ),
            models.UniqueConstraint(
                fields=["agreement", "resource"], name="agreement_resource_unique"
            ),
            models.UniqueConstraint(fields=["agreement", "asset"], name="agreement_asset_unique"),
        ]


class Acceptance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.ForeignKey(AgreementVersion, on_delete=models.PROTECT)
    accepted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "version"], name="agreement_once_per_version")
        ]


class IdentityCheck(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="identity_checks"
    )
    checked_at = models.DateTimeField(default=timezone.now)


class Appointment(models.Model):
    booking = models.OneToOneField("bookings.Booking", primary_key=True, on_delete=models.PROTECT)
    pickup_at = models.DateTimeField()
    return_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(return_at__gt=F("pickup_at")), name="appointment_positive"
            )
        ]


class Loan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    borrower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_loans"
    )
    issued_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    evidence = models.JSONField(default=dict)


class LoanLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="lines")
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.PROTECT, related_name="loan_line"
    )
    unit = models.ForeignKey("resources.ResourceUnit", on_delete=models.PROTECT)
    asset = models.ForeignKey("inventory.Asset", on_delete=models.PROTECT)
    expected_return = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    issue_condition = models.CharField(max_length=20)
    return_condition = models.CharField(max_length=20, blank=True)
    accessories = models.TextField(blank=True, max_length=2000)
    return_note = models.TextField(blank=True, max_length=2000)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=Q(returned_at__isnull=True),
                name="one_open_custody_per_unit",
            ),
            models.UniqueConstraint(
                fields=["asset"],
                condition=Q(returned_at__isnull=True),
                name="one_open_custody_per_asset",
            ),
            models.CheckConstraint(
                condition=Q(returned_at__isnull=True, returned_by__isnull=True, return_condition="")
                | Q(returned_at__isnull=False, returned_by__isnull=False) & ~Q(return_condition=""),
                name="loan_return_shape",
            ),
        ]


class Extension(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey("bookings.Booking", on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    before_end = models.DateTimeField()
    after_end = models.DateTimeField()
    before_date = models.DateField(null=True)
    after_date = models.DateField(null=True)
    booking_revision = models.PositiveIntegerField()
    reason = models.CharField(max_length=500)
    policy_snapshot = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(after_end__gt=F("before_end")), name="extension_positive"
            ),
            models.UniqueConstraint(
                fields=["booking", "booking_revision"], name="extension_revision_unique"
            ),
        ]


class Operation(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20)
    key = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "kind", "key"], name="loan_operation_idempotency"
            )
        ]
