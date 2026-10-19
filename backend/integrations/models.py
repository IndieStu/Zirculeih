import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class IntegrationClient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    capabilities = models.JSONField()
    scope_kind = models.CharField(max_length=20)
    scope_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    retired_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def scope_label(self):
        return {
            "organization": "Aktuell erlaubter Bereich",
            "location": "Standort mit Unterorten",
            "category": "Kategorie mit Unterkategorien",
            "resource": "Artikel / Raum",
            "asset": "Inventargegenstand",
        }[self.scope_kind]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(scope_kind="organization", scope_id__isnull=True)
                | Q(
                    scope_kind__in=["resource", "category", "location", "asset"],
                    scope_id__isnull=False,
                ),
                name="api_client_scope_valid",
            )
        ]


class IntegrationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(IntegrationClient, on_delete=models.PROTECT, related_name="tokens")
    digest = models.CharField(max_length=64, unique=True)
    capabilities = models.JSONField()
    read_only = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("created_at")),
                name="api_token_positive_lifetime",
            )
        ]


class APIImport(models.Model):
    client = models.ForeignKey(IntegrationClient, on_delete=models.PROTECT)
    preview = models.OneToOneField(
        "inventory.ImportPreview", on_delete=models.PROTECT, primary_key=True
    )
