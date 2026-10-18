import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class InventoryRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=150)
    scope = models.CharField(
        max_length=20,
        choices=[
            ("organization", "Organisation"),
            ("location", "Standort mit Unterorten"),
            ("category", "Kategorie mit Unterkategorien"),
        ],
    )
    scope_id = models.UUIDField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=15,
        default="draft",
        choices=[
            ("draft", "Entwurf"),
            ("active", "Läuft"),
            ("completed", "Abgeschlossen"),
            ("cancelled", "Abgebrochen"),
        ],
    )
    started_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    report = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(scope="organization", scope_id__isnull=True)
                | Q(scope__in=["location", "category"], scope_id__isnull=False),
                name="inventory_run_valid_scope",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["draft", "active", "completed", "cancelled"]),
                name="inventory_run_valid_status",
            ),
        ]


class ExpectedAsset(models.Model):
    run = models.ForeignKey(InventoryRun, on_delete=models.PROTECT, related_name="expected")
    asset = models.ForeignKey("inventory.Asset", on_delete=models.PROTECT)
    snapshot = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "asset"], name="inventory_expected_unique")
        ]


class Observation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(InventoryRun, on_delete=models.PROTECT, related_name="observations")
    asset = models.ForeignKey("inventory.Asset", on_delete=models.PROTECT)
    location = models.ForeignKey("inventory.Location", on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request_key = models.UUIDField()
    created_at = models.DateTimeField(default=timezone.now)
    custody = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "request_key"], name="inventory_observation_idempotent"
            )
        ]


class Discrepancy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(InventoryRun, on_delete=models.PROTECT, related_name="discrepancies")
    asset = models.ForeignKey("inventory.Asset", on_delete=models.PROTECT)
    kind = models.CharField(
        max_length=20,
        choices=[("wrong_location", "Abweichender Fundort"), ("unexpected", "Unerwarteter Fund")],
    )
    decision = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("move", "Standort berichtigt"),
            ("temporary", "Temporärer Fund"),
            ("defer", "Später klären"),
        ],
    )
    reason = models.CharField(max_length=500, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    resolved_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "asset", "kind"], name="inventory_discrepancy_unique"
            )
        ]


class MaintenanceTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        "inventory.Asset", on_delete=models.PROTECT, related_name="maintenance_tasks"
    )
    title = models.CharField(max_length=150)
    kind = models.CharField(
        max_length=20,
        choices=[("repair", "Reparatur"), ("inspection", "Prüfung"), ("service", "Wartung")],
    )
    description = models.TextField(max_length=5000, blank=True)
    due_date = models.DateField()
    interval_days = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        default="planned",
        choices=[
            ("planned", "Geplant"),
            ("in_progress", "In Arbeit"),
            ("completed", "Erledigt"),
            ("cancelled", "Abgebrochen"),
        ],
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="maintenance_reported"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="maintenance_assigned",
    )
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(max_length=5000, blank=True)
    revision = models.PositiveIntegerField(default=1)
    previous = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="follow_up"
    )
    attachments = models.ManyToManyField("inventory.AssetMedia", blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(interval_days__isnull=True)
                | Q(interval_days__gte=1, interval_days__lte=3660),
                name="maintenance_interval_bounded",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["planned", "in_progress", "completed", "cancelled"]),
                name="maintenance_status_valid",
            ),
        ]


class StaffedContext(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    generation = models.CharField(max_length=32)
    touched_at = models.DateTimeField(default=timezone.now)
    revoked = models.BooleanField(default=False)
