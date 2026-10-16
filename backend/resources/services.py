from dataclasses import dataclass
from uuid import UUID, uuid4

from accounts.authorization import Scope, allowed_many, authorization_write, require
from accounts.services import audit
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from inventory import extensions
from inventory.models import Asset, Category, Identifier, IdentifierNamespace, Location, Tag
from inventory.services import asset_scope, normalize, require_active, tree_scope

from .models import (
    PoolMembership,
    Resource,
    ResourceImage,
    ResourcePool,
    ResourceType,
    ResourceUnit,
)


def resource_scope(resource, categories=None):
    categories = list(resource.categories.all()) if categories is None else list(categories)
    return Scope(
        "resource",
        resource.pk,
        related=(tree_scope(resource.location), *(tree_scope(c) for c in categories)),
    )


def active_context(resource):
    try:
        require_active(resource.location)
        for category in resource.categories.all():
            require_active(category)
        return resource.type.is_active
    except ValidationError:
        return False


def visible_resources(actor, *, management=False):
    rows = list(Resource.objects.select_related("location", "type").prefetch_related("categories"))
    scopes = [resource_scope(r) for r in rows]
    private = allowed_many(
        actor, "resource.manage" if management else "catalog.view_private", scopes
    )
    ids = [
        r.pk
        for r, permitted in zip(rows, private, strict=True)
        if (
            permitted
            if management
            else (
                r.archived_at is None
                and r.published_at is not None
                and (permitted or (r.visibility == "public" and active_context(r)))
            )
        )
    ]
    return (
        Resource.objects.filter(pk__in=ids)
        .select_related("type", "location")
        .prefetch_related("categories", "tags", "images")
    )


def read_resource(actor, resource_id, action="resource.manage"):
    resource = Resource.objects.select_related("location", "type").get(pk=resource_id)
    require(actor, action, resource_scope(resource))
    return resource


def check_revision(row, expected):
    if row.revision != expected:
        raise ValidationError("Der Eintrag wurde inzwischen geändert. Bitte neu laden.")


def editable(resource):
    if resource.archived_at:
        raise ValidationError("Archivierte Angebote sind unveränderlich.")


def save_type(actor, data):
    with authorization_write():
        require(actor, "resource.type_manage")
        row = ResourceType(**data)
        row.full_clean()
        row.save()
        audit(actor, "resource.type_created", object_id=row.pk)
        return row


def save_resource(actor, data, *, resource_id=None, expected_revision=None):
    data = dict(data)
    allowed_fields = {
        "title",
        "slug",
        "summary",
        "description",
        "safety_notes",
        "pickup_notes",
        "specifications",
        "location_label",
        "location",
        "type",
        "visibility",
        "booking_enabled",
        "is_featured",
        "categories",
        "tags",
    }
    if set(data) - allowed_fields:
        raise ValidationError("Unbekannte Angebotsfelder.")
    with authorization_write():
        row = read_resource(actor, resource_id) if resource_id else Resource()
        before = {"title": row.title, "revision": row.revision} if resource_id else None
        if resource_id:
            editable(row)
            check_revision(row, expected_revision)
            if "slug" in data and data["slug"] != row.slug:
                raise ValidationError("Der URL-Name bleibt dauerhaft stabil.")
            if row.published_at:
                require(actor, "resource.publish", resource_scope(row))
        categories = list(data.pop("categories", row.categories.all() if resource_id else []))
        tags = list(data.pop("tags", row.tags.all() if resource_id else []))
        categories = list(Category.objects.filter(pk__in=[c.pk for c in categories]))
        for field, value in data.items():
            setattr(row, field, value)
        if row.slug in {"verwaltung", "bilder"}:
            raise ValidationError("Dieser URL-Name ist für die Navigation reserviert.")
        row.location = Location.objects.get(pk=row.location_id)
        row.type = ResourceType.objects.get(pk=row.type_id)
        require_active(row.location)
        if not row.type.is_active:
            raise ValidationError("Angebotstyp ist inaktiv.")
        require(actor, "location.read", tree_scope(row.location))
        for category in categories:
            require_active(category)
            require(actor, "category.read", tree_scope(category))
        scope = resource_scope(row, categories)
        require(actor, "resource.manage", scope)
        if row.published_at:
            require(actor, "resource.publish", scope)
        row.revision += 1
        row.updated_at = timezone.now()
        row.full_clean()
        row.save()
        row.categories.set(categories)
        row.tags.set(Tag.objects.filter(pk__in=[t.pk for t in tags]))
        if resource_id and set(data) & {"location", "type", "booking_enabled"}:
            from bookings.integrity import resource_changed

            resource_changed(row.pk)
        audit(
            actor,
            "resource.saved",
            object_id=row.pk,
            details={"before": before, "title": row.title, "revision": row.revision},
        )
        return row


def publication(actor, resource_id, expected_revision, operation, reason):
    if operation not in {"publish", "withdraw", "archive"} or not reason.strip():
        raise ValidationError("Bitte Aktion und Grund angeben.")
    with authorization_write():
        row = read_resource(actor, resource_id)
        require(actor, "resource.publish", resource_scope(row))
        check_revision(row, expected_revision)
        editable(row)
        if operation == "publish":
            if not active_context(row) or not row.units.filter(is_active=True).exists():
                raise ValidationError(
                    "Aktiver Typ, Ort/Kategorien und mindestens eine Einheit nötig."
                )
            row.published_at = timezone.now()
        else:
            row.published_at = None
            if operation == "archive":
                row.archived_at = timezone.now()
        row.revision += 1
        row.updated_at = timezone.now()
        row.save()
        if operation != "publish":
            from bookings.integrity import resource_changed

            resource_changed(row.pk)
        audit(
            actor,
            "resource." + operation,
            object_id=row.pk,
            reason=reason,
            details={"visibility": row.visibility, "revision": row.revision},
        )
        return row


def save_unit(actor, resource_id, data, *, unit_id=None, expected_revision=None):
    if set(data) - {"name", "asset", "is_active"}:
        raise ValidationError("Unbekannte Einheitsfelder.")
    with authorization_write():
        resource = read_resource(actor, resource_id)
        editable(resource)
        unit = (
            ResourceUnit.objects.get(pk=unit_id, resource=resource)
            if unit_id
            else ResourceUnit(resource=resource)
        )
        if unit_id:
            check_revision(unit, expected_revision)
            if "asset" in data and getattr(data["asset"], "pk", None) != unit.asset_id:
                raise ValidationError("Assetzuordnung einer Einheit bleibt dauerhaft stabil.")
        for key, value in data.items():
            setattr(unit, key, value)
        if unit.asset_id:
            asset = Asset.objects.get(pk=unit.asset_id)
            require(actor, "asset.read", asset_scope(asset))
            require(actor, "asset.manage", asset_scope(asset))
            if asset.archived_at:
                raise ValidationError("Archivierte Assets können nicht zugeordnet werden.")
        unit.revision += 1
        unit.full_clean()
        try:
            with transaction.atomic():
                unit.save()
        except IntegrityError as exc:
            raise ValidationError("Dieses Asset ist bereits einer Einheit zugeordnet.") from exc
        if unit_id:
            from bookings.integrity import resource_changed

            resource_changed(resource.pk)
        audit(
            actor,
            "resource.unit_saved",
            object_id=resource.pk,
            details={"unit_id": str(unit.pk), "active": unit.is_active},
        )
        return unit


def save_pool(
    actor, resource_id, name, units, *, pool_id=None, expected_revision=None, is_active=True
):
    with authorization_write():
        resource = read_resource(actor, resource_id)
        editable(resource)
        pool = (
            ResourcePool.objects.get(pk=pool_id, resource=resource)
            if pool_id
            else ResourcePool(resource=resource)
        )
        if pool_id:
            check_revision(pool, expected_revision)
        ids = [u.pk for u in units]
        selected = list(ResourceUnit.objects.filter(pk__in=ids, resource=resource, is_active=True))
        if len(selected) != len(set(ids)):
            raise ValidationError("Nur aktive Einheiten dieses Angebots wählen.")
        if PoolMembership.objects.filter(unit_id__in=ids).exclude(pool=pool).exists():
            raise ValidationError("Eine Einheit ist bereits einem anderen Pool zugeordnet.")
        pool.name, pool.is_active = name, is_active
        pool.revision += 1
        pool.full_clean()
        pool.save()
        pool.memberships.exclude(unit_id__in=ids).delete()
        for unit in selected:
            PoolMembership.objects.get_or_create(pool=pool, unit=unit)
        audit(
            actor,
            "resource.pool_saved",
            object_id=resource.pk,
            details={"pool_id": str(pool.pk), "unit_ids": [str(u.pk) for u in selected]},
        )
        return pool


def assign_unit_identifier(actor, unit_id, namespace_id, raw, kind, source=""):
    with authorization_write():
        unit = ResourceUnit.objects.select_related("resource__location").get(pk=unit_id)
        resource = read_resource(actor, unit.resource_id)
        require(actor, "identifier.assign", resource_scope(resource))
        editable(resource)
        if not unit.is_active:
            raise ValidationError("Einheit ist inaktiv.")
        if unit.asset_id:
            require(actor, "identifier.assign", asset_scope(unit.asset))
        ns = IdentifierNamespace.objects.get(pk=namespace_id, is_active=True)
        if ns.key in {"deelvo", "inventory"}:
            raise ValidationError("Für Unit-Aliase einen eigenen Namensraum verwenden.")
        row = Identifier(
            unit=unit,
            namespace=ns,
            raw_value=raw.strip(" \t\r\n"),
            canonical_value=normalize(ns, raw),
            kind=kind,
            source=source,
            created_by=actor,
        )
        row.full_clean(validate_unique=False, validate_constraints=False)
        try:
            with transaction.atomic():
                row.save()
        except IntegrityError as exc:
            raise ValidationError("Code bereits vergeben oder dauerhaft stillgelegt.") from exc
        audit(
            actor,
            "resource.identifier_assigned",
            object_id=resource.pk,
            details={"identifier_id": str(row.pk), "unit_id": str(unit.pk)},
        )
        return row


def retire_unit_identifier(actor, unit_id, identifier_id, reason):
    with authorization_write():
        unit = ResourceUnit.objects.get(pk=unit_id)
        resource = read_resource(actor, unit.resource_id)
        require(actor, "identifier.retire", resource_scope(resource))
        if unit.asset_id:
            require(actor, "identifier.retire", asset_scope(unit.asset))
        row = Identifier.objects.get(pk=identifier_id, unit=unit)
        if not reason.strip():
            raise ValidationError("Bitte Grund angeben.")
        if row.is_active:
            row.is_active, row.retired_at, row.retirement_reason = False, timezone.now(), reason
            row.save()
            audit(
                actor,
                "resource.identifier_retired",
                object_id=resource.pk,
                details={"identifier_id": str(row.pk)},
                reason=reason,
            )


def upload_image(actor, resource_id, upload, alt_text):
    resource = read_resource(actor, resource_id)
    data, _, _, is_image = extensions.sanitize_upload(upload)
    if not is_image or not alt_text.strip() or len(alt_text) > 200:
        raise ValidationError("Bitte PNG/JPEG und einen beschreibenden Alternativtext verwenden.")
    storage, stored = extensions.media_storage(), None
    try:
        with authorization_write():
            resource = read_resource(actor, resource_id)
            editable(resource)
            if resource.published_at:
                require(actor, "resource.publish", resource_scope(resource))
            if resource.images.filter(archived_at__isnull=True).count() >= 12:
                raise ValidationError("Maximal zwölf aktive Katalogbilder je Angebot.")
            stored = storage.save("resources/" + uuid4().hex + ".jpg", ContentFile(data))
            row = ResourceImage.objects.create(
                resource=resource,
                storage_name=stored,
                size=len(data),
                alt_text=alt_text,
                uploaded_by=actor,
            )
            audit(
                actor,
                "resource.image_uploaded",
                object_id=resource.pk,
                details={"image_id": str(row.pk)},
            )
            return row
    except Exception:
        if stored:
            storage.delete(stored)
        raise


def archive_image(actor, image_id):
    with authorization_write():
        image = ResourceImage.objects.get(pk=image_id, archived_at__isnull=True)
        resource = read_resource(actor, image.resource_id)
        editable(resource)
        if resource.published_at:
            require(actor, "resource.publish", resource_scope(resource))
        image.archived_at = timezone.now()
        image.save(update_fields=["archived_at"])
        audit(
            actor,
            "resource.image_archived",
            object_id=resource.pk,
            details={"image_id": str(image.pk)},
        )


def eligible_pool_units(actor, pool):
    """Configuration readiness only; never a time-based availability promise."""
    require(actor, "resource.manage", resource_scope(pool.resource))
    if not pool.is_active or pool.resource.archived_at or not active_context(pool.resource):
        return ResourceUnit.objects.none()
    from django.db.models import Q

    return ResourceUnit.objects.filter(pool_membership__pool=pool, is_active=True).filter(
        Q(asset__isnull=True)
        | Q(
            asset__archived_at__isnull=True,
            asset__lifecycle="active",
            asset__condition__in=["good", "worn"],
        )
    )


@dataclass(frozen=True)
class CatalogCard:
    id: UUID
    slug: str
    title: str
    summary: str
    type_name: str
    location_label: str
    categories: tuple[str, ...]
    cover_id: UUID | None
    cover_alt: str


def catalog_card(resource):
    images = [i for i in resource.images.all() if not i.archived_at]
    cover = images[0] if images else None
    return CatalogCard(
        resource.pk,
        resource.slug,
        resource.title,
        resource.summary,
        resource.type.name,
        resource.location_label,
        tuple(c.name for c in resource.categories.all()),
        cover.pk if cover else None,
        cover.alt_text if cover else "",
    )
