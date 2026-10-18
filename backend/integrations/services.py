import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from accounts.authorization import authorization_write, require
from accounts.services import audit
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from inventory.models import Category, Location
from inventory.services import read_asset, tree_scope
from resources.services import visible_resources

from .models import IntegrationClient, IntegrationToken

CAPABILITIES = {
    "availability.read": (
        "Verfügbarkeit prüfen",
        {"booking.create_own", "resource.use_unstaffed", "catalog.view_private"},
    ),
    "catalog.read": ("Katalog lesen", {"catalog.view_public", "catalog.view_private"}),
    "inventory.read": ("Inventar lesen", {"asset.read"}),
    "inventory.move": ("Standorte ändern", {"asset.move", "location.read"}),
    "inventory.export": ("Inventar exportieren", {"asset.export", "asset.read"}),
    "inventory.import": ("CSV-Import mit Vorschau", {"asset.import", "asset.manage", "asset.read"}),
    "identifiers.resolve": ("Inventarcodes auflösen", {"identifier.resolve"}),
    "bookings.read": ("Reservierungen lesen", {"booking.read_all"}),
    "bookings.create": (
        "Eigene Reservierungen erstellen",
        {"booking.create_own", "resource.use_unstaffed", "catalog.view_private"},
    ),
    "bookings.cancel": ("Eigene Reservierungen stornieren", {"booking.cancel_own"}),
    "loans.read": ("Ausleihen lesen", {"loan.read"}),
    "loans.checkout": (
        "Bestehende Reservierungen ausgeben",
        {
            "loan.checkout",
            "booking.create_for_others",
            "resource.use_unstaffed",
            "catalog.view_private",
        },
    ),
    "loans.return": ("Tatsächliche Rückgaben erfassen", {"loan.return"}),
}
WRITES = frozenset(
    {
        "inventory.move",
        "inventory.import",
        "bookings.create",
        "bookings.cancel",
        "loans.checkout",
        "loans.return",
    }
)


@dataclass(frozen=True)
class Ceiling:
    owner_id: object
    client_id: object
    token_id: object
    capabilities: frozenset
    scope_kind: str
    scope_id: object

    @property
    def actions(self):
        return frozenset().union(*(CAPABILITIES[c][1] for c in self.capabilities))

    def includes(self, scope):
        return self.scope_kind == "organization" or any(
            s.kind == self.scope_kind
            and (
                s.id == self.scope_id
                or (s.kind in {"category", "location"} and self.scope_id in s.ancestors)
            )
            for s in (scope, *scope.related)
        )


def validate_scope(actor, kind, pk):
    if kind == "organization" and pk is None:
        return
    if kind == "asset":
        read_asset(actor, pk)
    elif kind == "resource":
        visible_resources(actor).get(pk=pk)
    elif kind in {"category", "location"}:
        node = (Category if kind == "category" else Location).objects.get(pk=pk, is_active=True)
        require(actor, kind + ".read", tree_scope(node))
    else:
        raise ValidationError("Gültigen Integrationsbereich wählen.")


def create_client(actor, name, capabilities, scope_kind="organization", scope_id=None):
    with authorization_write():
        require(actor, "integration.manage")
        caps = set(capabilities)
        if not caps or caps - set(CAPABILITIES):
            raise ValidationError("Dokumentierte Fähigkeiten wählen.")
        if IntegrationClient.objects.filter(owner=actor, retired_at=None).count() >= 20:
            raise ValidationError("Höchstens 20 aktive Integrationen je Konto.")
        validate_scope(actor, scope_kind, scope_id)
        row = IntegrationClient(
            owner=actor,
            name=name.strip(),
            capabilities=sorted(caps),
            scope_kind=scope_kind,
            scope_id=scope_id,
        )
        row.full_clean()
        row.save()
        audit(actor, "integration.created", object_id=row.pk)
        return row


def owned(actor, client_id):
    require(actor, "integration.manage")
    return IntegrationClient.objects.get(pk=client_id, owner=actor)


def issue(actor, client_id, *, days=30, read_only=True, capabilities=None, expires_at=None):
    with authorization_write():
        client = owned(actor, client_id)
        if (
            client.retired_at
            or type(days) is not int
            or not 1 <= days <= 90
            or type(read_only) is not bool
        ):
            raise ValidationError("Aktive Integration und 1–90 Tage erforderlich.")
        caps = set(client.capabilities if capabilities is None else capabilities)
        if not caps or caps - set(client.capabilities):
            raise ValidationError("Tokenfähigkeiten müssen innerhalb der Integration liegen.")
        if read_only:
            caps -= WRITES
        if not caps:
            raise ValidationError(
                "Lesende Fähigkeit wählen oder Schreibzugang ausdrücklich aktivieren."
            )
        if client.tokens.filter(revoked_at=None, expires_at__gt=timezone.now()).count() >= 20:
            raise ValidationError("Höchstens 20 aktive Token je Integration.")
        raw = "dv1_" + secrets.token_urlsafe(32)
        now = timezone.now()
        if expires_at is not None and not now < expires_at <= now + timedelta(days=90):
            raise ValidationError("Ungültiger Tokenablauf.")
        row = IntegrationToken.objects.create(
            client=client,
            digest=hashlib.sha256(raw.encode()).hexdigest(),
            capabilities=sorted(caps),
            read_only=read_only,
            created_at=now,
            expires_at=expires_at or now + timedelta(days=days),
        )
        audit(actor, "integration.token_issued", object_id=row.pk)
        return row, raw


def revoke(actor, token_id):
    with authorization_write():
        row = IntegrationToken.objects.get(pk=token_id, client__owner=actor)
        owned(actor, row.client_id)
        if row.revoked_at is None:
            row.revoked_at = timezone.now()
            row.save(update_fields=["revoked_at"])
            audit(actor, "integration.token_revoked", object_id=row.pk)
        return row


def rotate(actor, token_id):
    with authorization_write():
        row = IntegrationToken.objects.get(pk=token_id, client__owner=actor)
        if row.revoked_at or row.expires_at <= timezone.now():
            raise ValidationError("Abgelaufenen Zugang neu anlegen.")
        revoke(actor, row.pk)
        days = max(1, min(90, (row.expires_at - timezone.now()).days + 1))
        new, raw = issue(
            actor,
            row.client_id,
            days=days,
            read_only=row.read_only,
            capabilities=row.capabilities,
            expires_at=row.expires_at,
        )
        return new, raw


def retire(actor, client_id):
    with authorization_write():
        row = owned(actor, client_id)
        if row.retired_at is None:
            row.retired_at = timezone.now()
            row.save(update_fields=["retired_at"])
            audit(actor, "integration.retired", object_id=row.pk)
        return row


def authenticate(header):
    if not isinstance(header, str) or len(header) > 256:
        raise PermissionDenied
    scheme, sep, raw = header.partition(" ")
    if scheme.lower() != "bearer" or not sep or len(raw) != 47 or not raw.startswith("dv1_"):
        raise PermissionDenied
    row = IntegrationToken.objects.select_related("client__owner").get(
        digest=hashlib.sha256(raw.encode()).hexdigest(),
        revoked_at=None,
        expires_at__gt=timezone.now(),
        client__retired_at=None,
    )
    require(row.client.owner, "integration.manage")
    caps = frozenset(row.capabilities) & frozenset(row.client.capabilities)
    if row.read_only:
        caps -= WRITES
    return row, Ceiling(
        row.client.owner_id, row.client_id, row.pk, caps, row.client.scope_kind, row.client.scope_id
    )
