from accounts.authorization import authorization_write, require
from accounts.models import User
from accounts.services import audit
from bookings.services import require_active_actor
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone
from inventory.services import asset_scope
from resources.services import resource_scope

from .models import Acceptance, Agreement, AgreementAssignment, AgreementVersion


def create_agreement(actor, title, kind):
    with authorization_write():
        require(actor, "agreement.edit")
        if kind not in {"general", "insurance", "additional"}:
            raise ValidationError("Unbekannte Vereinbarungsart.")
        row = Agreement(title=title, kind=kind)
        row.full_clean()
        row.save()
        audit(actor, "agreement.created", object_id=row.pk)
        return row


def save_version(actor, agreement_id, text):
    with authorization_write():
        require(actor, "agreement.edit")
        agreement = Agreement.objects.get(pk=agreement_id)
        if not text.strip() or len(text) > 50000:
            raise ValidationError("Bitte einen Text bis 50000 Zeichen schreiben.")
        number = (
            agreement.versions.order_by("-number").values_list("number", flat=True).first() or 0
        ) + 1
        row = AgreementVersion.objects.create(
            agreement=agreement, number=number, text=text, created_by=actor
        )
        audit(actor, "agreement.version_created", object_id=row.pk)
        return row


def publish_version(actor, version_id):
    with authorization_write():
        require(actor, "agreement.publish")
        row = AgreementVersion.objects.select_related("agreement").get(pk=version_id)
        latest = (
            row.agreement.versions.filter(published_at__isnull=False).order_by("-number").first()
        )
        if row.published_at:
            return row
        if latest and latest.number >= row.number:
            raise ValidationError(
                "Nur eine neue unveröffentlichte Version kann veröffentlicht werden."
            )
        row.published_at = timezone.now()
        row.save(update_fields=["published_at"])
        audit(actor, "agreement.published", object_id=row.pk)
        return row


def assign(actor, agreement_id, *, resource=None, asset=None):
    with authorization_write():
        if bool(resource) == bool(asset):
            raise ValidationError("Genau ein Angebot oder Asset wählen.")
        require(
            actor, "agreement.assign", resource_scope(resource) if resource else asset_scope(asset)
        )
        agreement = Agreement.objects.get(pk=agreement_id, kind="additional", is_active=True)
        row, _ = AgreementAssignment.objects.get_or_create(
            agreement=agreement, resource=resource, asset=asset
        )
        audit(actor, "agreement.assigned", object_id=row.pk)
        return row


def required_versions(resource, asset=None):
    rows = (
        Agreement.objects.filter(is_active=True)
        .filter(
            Q(kind__in=["general", "insurance"])
            | Q(agreementassignment__resource=resource)
            | (Q(agreementassignment__asset=asset) if asset else Q(pk__in=[]))
        )
        .distinct()
    )
    versions = []
    for agreement in rows:
        version = agreement.versions.filter(published_at__isnull=False).order_by("-number").first()
        if not version:
            raise ValidationError("lending_setup_required")
        versions.append(version)
    if not {"general", "insurance"}.issubset({v.agreement.kind for v in versions}):
        raise ValidationError("lending_setup_required")
    return versions


def accept(actor, version_ids):
    with authorization_write():
        require_active_actor(actor)
        ids = set(version_ids)
        rows = list(AgreementVersion.objects.filter(pk__in=ids, published_at__isnull=False))
        if len(rows) != len(ids) or not rows:
            raise ValidationError("Veröffentlichte Textversionen auswählen.")
        for row in rows:
            # Current generic texts, or currently visible Resource/Asset assignment only.
            if row.agreement.kind == "additional":
                from inventory.services import visible_assets
                from resources.services import visible_resources

                assigned = (
                    AgreementAssignment.objects.filter(agreement=row.agreement)
                    .filter(
                        Q(resource__in=visible_resources(actor))
                        | Q(asset__in=visible_assets(actor))
                        | Q(asset__resource_unit__resource__in=visible_resources(actor))
                    )
                    .exists()
                )
                if not assigned:
                    raise PermissionDenied
            Acceptance.objects.get_or_create(user=actor, version=row)
            audit(actor, "agreement.accepted", object_id=row.pk)


def gate(user, resource, unit):
    user = User.objects.get(pk=user.pk)
    if not user.is_active or not user.email_verified_at or not user.borrower_profile_complete:
        return "borrower_profile_required"
    from resources.requirements import gate as requirement_gate

    try:
        problem = requirement_gate(user, resource)
    except ValidationError:
        return "lending_setup_required"
    if problem:
        return problem
    if not unit.asset_id:
        return "physical_unit_required"
    try:
        versions = required_versions(resource, unit.asset)
    except ValidationError:
        return "lending_setup_required"
    if resource.bookingpolicy.requires_agreement and not any(
        v.agreement.kind == "additional" for v in versions
    ):
        return "agreement_required"
    if Acceptance.objects.filter(user=user, version__in=versions).count() != len(versions):
        return "agreement_required"
    return None


def unassign(actor, assignment_id):
    with authorization_write():
        row = AgreementAssignment.objects.select_related("resource", "asset").get(pk=assignment_id)
        require(
            actor,
            "agreement.assign",
            resource_scope(row.resource) if row.resource_id else asset_scope(row.asset),
        )
        audit(
            actor,
            "agreement.unassigned",
            object_id=row.pk,
            details={
                "agreement": str(row.agreement_id),
                "resource": str(row.resource_id),
                "asset": str(row.asset_id),
            },
        )
        row.delete()
