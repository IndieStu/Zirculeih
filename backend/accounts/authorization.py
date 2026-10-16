from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import AuthorizationRevision, Grant, User

SYSTEM_ACTIONS = frozenset({"permissions.manage", "system.configure", "admin.manage"})
BASELINE_ACTIONS = frozenset(
    {
        "catalog.view_public",
        "booking.create_own",
        "booking.request_recurrence",
        "booking.cancel_own",
    }
)
ACTIONS = (
    BASELINE_ACTIONS
    | SYSTEM_ACTIONS
    | frozenset(
        {
            "catalog.view_private",
            "booking.create_for_others",
            "booking.override_policy",
            "booking.approve",
            "booking.manage_all",
            "resource.use_unstaffed",
            "loan.checkout",
            "loan.return",
            "loan.inspect_identity",
            "loan.read",
            "borrower.read_contact",
            "asset.read",
            "asset.manage",
            "asset.read_financial",
            "asset.export",
            "asset.move",
            "resource.manage",
            "maintenance.manage",
            "qualification.issue",
            "agreement.edit",
            "agreement.publish",
            "agreement.assign",
            "user.manage_groups",
            "account.suspend",
            "identifier.resolve",
            "identifier.assign",
            "identifier.retire",
            "inventory_run.create",
            "inventory_run.start",
            "inventory_run.observe",
            "inventory_run.read",
            "inventory_run.export",
            "inventory_run.complete",
            "inventory_discrepancy.resolve",
        }
    )
)
INVENTORY_ACTIONS = {
    "booking.configure": "Buchungsregeln und Zeitpläne konfigurieren",
    "booking.block": "Harte Ressourcensperren verwalten",
    "booking.read_all": "Buchungen im Betriebsbereich ansehen",
    "resource.publish": "Angebote veröffentlichen oder zurückziehen",
    "resource.type_manage": "Angebotstypen konfigurieren",
    "asset.archive": "Inventar archivieren oder ausmustern",
    "asset.read_sensitive": "Seriennummern und interne Inventarnotizen ansehen/bearbeiten",
    "asset.import": "Inventar per CSV importieren",
    "asset.attach": "Inventarbilder und Textdokumente hochladen",
    "location.read": "Standorte ansehen",
    "location.manage": "Standorte verwalten",
    "category.read": "Inventarkategorien ansehen",
    "category.manage": "Inventarkategorien verwalten",
    "identifier.namespace_manage": "Inventar-Code-Namensräume verwalten",
    "custom_field.manage": "Zusatzfelder konfigurieren",
}
ACTIONS = ACTIONS | frozenset(INVENTORY_ACTIONS)
SCOPE_KINDS = frozenset(
    {"organization", "group", "user", "asset", "resource", "category", "location"}
)


@dataclass(frozen=True)
class Scope:
    kind: str = "organization"
    id: UUID | None = None
    # Only domain services may construct ancestors from validated category/location trees.
    ancestors: tuple[UUID, ...] = ()
    related: tuple["Scope", ...] = ()


@contextmanager
def authorization_write():
    """Hold through the complete protected write; never cache an authorization result."""
    with transaction.atomic():
        revision = AuthorizationRevision.objects.select_for_update().get(pk=1)
        yield revision


def bump(revision):
    revision.revision += 1
    revision.save(update_fields=["revision"])


ORGANIZATION = Scope()


def _grants_allow(grants, scope, horizon_days, duration_minutes):
    contexts = (scope, *scope.related)
    if any(
        s.kind not in SCOPE_KINDS or (s.kind == "organization") != (s.id is None) for s in contexts
    ):
        return False
    applicable = [
        g
        for g in grants
        if g.scope_kind == "organization"
        or any(
            g.scope_kind == s.kind
            and (
                g.scope_id == s.id
                or (g.inherit and s.kind in {"location", "category"} and g.scope_id in s.ancestors)
            )
            for s in contexts
        )
    ]
    if any(g.effect == "deny" for g in applicable):
        return False
    return any(
        g.effect == "allow"
        and (
            g.max_horizon_days is None
            or (horizon_days is not None and horizon_days <= g.max_horizon_days)
        )
        and (
            g.max_duration_minutes is None
            or (duration_minutes is not None and duration_minutes <= g.max_duration_minutes)
        )
        for g in applicable
    )


def allowed_many(actor, action, scopes, *, horizon_days=None, duration_minutes=None):
    """One fresh actor/grant read for an authorized list; never cache between requests/writes."""
    scopes = list(scopes)
    if not getattr(actor, "is_authenticated", False) or action not in ACTIONS:
        return [False] * len(scopes)
    user = User.objects.filter(pk=actor.pk, is_active=True, email_verified_at__isnull=False).first()
    if user is None:
        return [False] * len(scopes)
    if action in SYSTEM_ACTIONS:
        return [
            user.is_system_admin
            and all(
                c.kind in SCOPE_KINDS and ((c.kind == "organization") == (c.id is None))
                for c in (s, *s.related)
            )
            for s in scopes
        ]
    grants = list(
        Grant.objects.filter(
            group__is_active=True,
            group__archived_at__isnull=True,
            group__membership__user=user,
            group__membership__removed_at__isnull=True,
            action=action,
        )
    )
    return [_grants_allow(grants, scope, horizon_days, duration_minutes) for scope in scopes]


def allowed(actor, action, scope=ORGANIZATION, *, horizon_days=None, duration_minutes=None):
    return allowed_many(
        actor, action, [scope], horizon_days=horizon_days, duration_minutes=duration_minutes
    )[0]


def require(actor, action, scope=ORGANIZATION, **restrictions):
    if not allowed(actor, action, scope, **restrictions):
        raise PermissionDenied("Für diese Aktion fehlt die Berechtigung.")


def require_beneficiary(actor, beneficiary, action, scope, **restrictions):
    """loan.return callers check only actor; a suspended borrower can always return via staff."""
    require(actor, action, scope, **restrictions)
    if not User.objects.filter(
        pk=beneficiary.pk, is_active=True, email_verified_at__isnull=False
    ).exists():
        raise PermissionDenied("Das Empfängerkonto ist nicht freigegeben.")
    require(beneficiary, "booking.create_own", scope, **restrictions)


ACTION_LABELS = {
    "catalog.view_public": "Öffentlichen Katalog ansehen",
    "catalog.view_private": "Internen Katalog ansehen",
    "booking.create_own": "Eigene Reservierungen erstellen",
    "booking.request_recurrence": "Reservierungsserien beantragen",
    "booking.cancel_own": "Eigene Reservierungen stornieren",
    "booking.create_for_others": "Für andere reservieren",
    "booking.override_policy": "Freigegebene Buchungsregeln begründet übersteuern",
    "booking.approve": "Reservierungen genehmigen",
    "booking.manage_all": "Reservierungen verwalten",
    "resource.use_unstaffed": "Außerhalb betreuter Öffnungszeiten nutzen",
    "loan.checkout": "Gegenstände ausgeben",
    "loan.return": "Rückgaben annehmen",
    "loan.inspect_identity": "Identität bei erster Ausgabe prüfen",
    "loan.read": "Ausleihen ansehen",
    "borrower.read_contact": "Ausleihkontaktdaten ansehen",
    "asset.read": "Inventar ansehen",
    "asset.manage": "Inventar bearbeiten",
    "asset.read_financial": "Anschaffungsdaten ansehen",
    "asset.export": "Inventar exportieren",
    "asset.move": "Standort ausdrücklich ändern",
    "resource.manage": "Angebote verwalten",
    "maintenance.manage": "Wartung verwalten",
    "qualification.issue": "Einweisungen erteilen",
    "agreement.edit": "Vereinbarungen entwerfen",
    "agreement.publish": "Vereinbarungen veröffentlichen",
    "agreement.assign": "Vereinbarungen zuordnen",
    "user.manage_groups": "Mitgliedschaften einer Gruppe verwalten",
    "account.suspend": "Ein Konto sperren oder freigeben",
    "identifier.resolve": "Inventarcodes nachschlagen",
    "identifier.assign": "Inventarcodes zuordnen",
    "identifier.retire": "Inventarcodes stilllegen",
    "inventory_run.create": "Inventur anlegen",
    "inventory_run.start": "Inventur starten",
    "inventory_run.observe": "Inventurbeobachtungen erfassen",
    "inventory_run.read": "Inventuren ansehen",
    "inventory_run.export": "Inventuren exportieren",
    "inventory_run.complete": "Inventur abschließen",
    "inventory_discrepancy.resolve": "Inventurabweichungen entscheiden",
}

ACTION_LABELS.update(INVENTORY_ACTIONS)
