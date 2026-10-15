import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TreeNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=2000)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

    @property
    def lineage(self):
        nodes, seen, node = [], set(), self
        while node is not None:
            if node.pk in seen:
                raise ValueError("Cyclic inventory tree")
            seen.add(node.pk)
            nodes.append(node)
            node = node.parent
        return tuple(reversed(nodes))

    @property
    def breadcrumb(self):
        return " / ".join(n.name for n in self.lineage)


class Location(TreeNode):
    class Meta(TreeNode.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=~Q(id=models.F("parent_id")), name="location_not_own_parent"
            )
        ]


class Category(TreeNode):
    class Meta(TreeNode.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=~Q(id=models.F("parent_id")), name="category_not_own_parent"
            )
        ]


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Asset(models.Model):
    class Condition(models.TextChoices):
        GOOD = "good", "Gut"
        WORN = "worn", "Gebrauchsspuren"
        DAMAGED = "damaged", "Beschädigt"
        INSPECTION = "inspection", "Prüfung erforderlich"

    class Lifecycle(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        UNAVAILABLE = "unavailable", "Vorübergehend nicht verfügbar"
        MAINTENANCE = "maintenance", "In Wartung"
        RETIRED = "retired", "Ausgemustert"
        LOST = "lost", "Verloren"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_number = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=10000)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    tags = models.ManyToManyField(Tag, blank=True)
    manufacturer = models.CharField(max_length=150, blank=True)
    model = models.CharField(max_length=150, blank=True)
    serial_number = models.CharField(max_length=200, blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    lifecycle = models.CharField(max_length=20, choices=Lifecycle.choices, default=Lifecycle.ACTIVE)
    internal_notes = models.TextField(blank=True, max_length=10000)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(inventory_number=""), name="asset_inventory_nonempty"
            ),
            models.CheckConstraint(
                condition=Q(acquisition_value__gte=0) | Q(acquisition_value__isnull=True),
                name="asset_nonnegative_value",
            ),
            models.CheckConstraint(
                condition=Q(condition__in=["good", "worn", "damaged", "inspection"]),
                name="asset_condition_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    lifecycle__in=["active", "unavailable", "maintenance", "retired", "lost"]
                ),
                name="asset_lifecycle_valid",
            ),
        ]

    def __str__(self):
        return f"{self.inventory_number} · {self.name}"


class IdentifierNamespace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    normalization = models.CharField(
        max_length=20,
        choices=[("exact-v1", "Exakt (v1)"), ("upper-ascii-v1", "ASCII Großbuchstaben (v1)")],
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Identifier(models.Model):
    class Kind(models.TextChoices):
        OWNED = "owned", "Deelvo-Code"
        INVENTORY = "inventory", "Inventarnummer"
        QR = "qr", "QR-Code"
        BARCODE = "barcode", "Barcode"
        EXTERNAL = "external", "Externer Code"
        MANUFACTURER = "manufacturer", "Eindeutiger Hersteller-Code"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    namespace = models.ForeignKey(IdentifierNamespace, on_delete=models.PROTECT)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="identifiers")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    raw_value = models.CharField(max_length=128)
    canonical_value = models.CharField(max_length=128)
    source = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    retired_at = models.DateTimeField(null=True, blank=True)
    retirement_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "canonical_value"], name="identifier_namespace_unique"
            ),
            models.CheckConstraint(
                condition=~Q(canonical_value=""), name="identifier_value_nonempty"
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, retired_at__isnull=True)
                    | Q(is_active=False, retired_at__isnull=False)
                ),
                name="identifier_retirement_state",
            ),
        ]


class AssetMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="movements")
    from_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="moves_out")
    to_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="moves_in")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.CharField(max_length=500)
    from_path = models.TextField()
    to_path = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)


class CustomFieldDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=60, unique=True)
    label = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=10,
        choices=[
            (k, label)
            for k, label in (
                ("text", "Text"),
                ("number", "Zahl"),
                ("date", "Datum"),
                ("boolean", "Ja/Nein"),
                ("enum", "Auswahl"),
                ("url", "Webadresse"),
            )
        ],
    )
    options = models.JSONField(default=list, blank=True)
    is_sensitive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class CustomFieldValue(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="custom_values")
    definition = models.ForeignKey(CustomFieldDefinition, on_delete=models.PROTECT)
    value_text = models.CharField(max_length=2000, null=True, blank=True)
    value_number = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_boolean = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset", "definition"], name="one_asset_custom_field"),
            models.CheckConstraint(
                condition=(
                    Q(
                        value_text__isnull=False,
                        value_number__isnull=True,
                        value_date__isnull=True,
                        value_boolean__isnull=True,
                    )
                    | Q(
                        value_text__isnull=True,
                        value_number__isnull=False,
                        value_date__isnull=True,
                        value_boolean__isnull=True,
                    )
                    | Q(
                        value_text__isnull=True,
                        value_number__isnull=True,
                        value_date__isnull=False,
                        value_boolean__isnull=True,
                    )
                    | Q(
                        value_text__isnull=True,
                        value_number__isnull=True,
                        value_date__isnull=True,
                        value_boolean__isnull=False,
                    )
                ),
                name="custom_value_exactly_one_type",
            ),
        ]

    @property
    def value(self):
        for field in ("value_text", "value_number", "value_date", "value_boolean"):
            value = getattr(self, field)
            if value is not None:
                return value


class AssetMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="media")
    storage_name = models.CharField(max_length=200, unique=True)
    display_name = models.CharField(max_length=150)
    content_type = models.CharField(max_length=50)
    size = models.PositiveIntegerField()
    is_image = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)


class ImportPreview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    rows = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    committed_at = models.DateTimeField(null=True, blank=True)
    created_asset_ids = models.JSONField(default=list)
