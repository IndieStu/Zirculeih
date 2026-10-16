import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ResourceType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Resource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=160)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(max_length=20000, blank=True)
    safety_notes = models.TextField(max_length=10000, blank=True)
    pickup_notes = models.TextField(max_length=10000, blank=True)
    catalog_area = models.CharField(max_length=100, blank=True)
    location_label = models.CharField(max_length=160, blank=True)
    specifications = models.TextField(max_length=10000, blank=True)
    type = models.ForeignKey(ResourceType, on_delete=models.PROTECT)
    location = models.ForeignKey("inventory.Location", on_delete=models.PROTECT)
    categories = models.ManyToManyField("inventory.Category", blank=True)
    tags = models.ManyToManyField("inventory.Tag", blank=True)
    visibility = models.CharField(
        max_length=10, choices=[("private", "Intern"), ("public", "Öffentlich")], default="private"
    )
    published_at = models.DateTimeField(null=True, blank=True)
    booking_enabled = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["title", "id"]
        constraints = [
            models.CheckConstraint(condition=~Q(title=""), name="resource_title_nonempty"),
            models.CheckConstraint(
                condition=Q(visibility__in=["private", "public"]), name="resource_visibility_valid"
            ),
            models.CheckConstraint(
                condition=Q(archived_at__isnull=True) | Q(published_at__isnull=True),
                name="resource_archive_unpublished",
            ),
        ]

    def __str__(self):
        return self.title


class ResourceUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="units")
    # Permanent one-to-one inventory identity, including retired units.
    asset = models.OneToOneField(
        "inventory.Asset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="resource_unit",
    )
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name", "id"]
        constraints = [models.CheckConstraint(condition=~Q(name=""), name="unit_name_nonempty")]

    def __str__(self):
        return self.name


class ResourcePool(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="pools")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name", "id"]


class PoolMembership(models.Model):
    pool = models.ForeignKey(ResourcePool, on_delete=models.PROTECT, related_name="memberships")
    unit = models.OneToOneField(
        ResourceUnit, on_delete=models.PROTECT, related_name="pool_membership"
    )


class ResourceImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="images")
    storage_name = models.CharField(max_length=200, unique=True)
    alt_text = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField(default=0)
    size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "created_at", "id"]


class QualificationType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(max_length=2000, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ResourceQualification(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="qualifications")
    qualification = models.ForeignKey(QualificationType, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "qualification"], name="resource_qualification_unique"
            )
        ]


class UserQualification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    qualification = models.ForeignKey(QualificationType, on_delete=models.PROTECT)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_qualifications"
    )
    issued_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "qualification"], name="user_qualification_unique"
            )
        ]
