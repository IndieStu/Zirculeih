import re
import secrets
from dataclasses import dataclass
from uuid import UUID

from accounts.authorization import Scope, allowed_many, authorization_write, bump, require
from accounts.services import audit
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    Asset,
    AssetMovement,
    Category,
    Identifier,
    IdentifierNamespace,
    Location,
    Tag,
)


def tree_scope(node):
    kind = "location" if isinstance(node, Location) else "category"
    return Scope(kind, node.pk, tuple(n.pk for n in node.lineage[:-1]))


def asset_scope(asset):
    loc, cat = tree_scope(asset.location), tree_scope(asset.category)
    return Scope("asset", asset.pk, related=(loc, cat))


def asset_snapshot(asset):
    return {
        "name": asset.name,
        "inventory_number": asset.inventory_number,
        "category_id": str(asset.category_id),
        "location_id": str(asset.location_id),
        "location_path": asset.location.breadcrumb,
        "category_path": asset.category.breadcrumb,
        "condition": asset.condition,
        "lifecycle": asset.lifecycle,
        "archived": asset.archived_at is not None,
        "revision": asset.revision,
    }


def visible_assets(actor, action="asset.read"):
    """Central batch resolver: scope-filter before pagination, without per-asset auth queries."""
    locations = dict(Location.objects.values_list("id", "parent_id"))
    categories = dict(Category.objects.values_list("id", "parent_id"))

    def context(kind, pk, tree):
        ancestors, seen, current = [], {pk}, tree[pk]
        while current is not None:
            if current in seen:
                raise ValidationError("Zyklische Hierarchie.")
            seen.add(current)
            ancestors.append(current)
            current = tree[current]
        return Scope(kind, pk, tuple(ancestors))

    assets = list(Asset.objects.only("id", "location_id", "category_id"))
    scopes = [
        Scope(
            "asset",
            a.pk,
            related=(
                context("location", a.location_id, locations),
                context("category", a.category_id, categories),
            ),
        )
        for a in assets
    ]
    decisions = allowed_many(actor, action, scopes)
    ids = [asset.pk for asset, permitted in zip(assets, decisions, strict=True) if permitted]
    return Asset.objects.filter(pk__in=ids).select_related("location", "category")


def read_asset(actor, asset_id, action="asset.read"):
    asset = Asset.objects.select_related("location", "category").get(pk=asset_id)
    require(actor, action, asset_scope(asset))
    return asset


def descendants(model, node_id):
    result, todo = [], [node_id]
    while todo:
        pk = todo.pop()
        if pk in result:
            raise ValidationError("Zyklische Hierarchie.")
        result.append(pk)
        todo.extend(model.objects.filter(parent_id=pk).values_list("pk", flat=True))
    return result


def require_active(node):
    if not all(n.is_active for n in node.lineage):
        raise ValidationError("Bitte einen aktiven Ort und eine aktive Kategorie wählen.")


def save_tree(actor, model, data, *, node_id=None, expected_revision=None):
    if model not in (Location, Category):
        raise ValueError("Unsupported tree")
    action = "location.manage" if model is Location else "category.manage"
    with authorization_write() as revision:
        node = model.objects.get(pk=node_id) if node_id else model()
        if node_id:
            require(actor, action, tree_scope(node))
            if expected_revision != node.revision:
                raise ValidationError("Der Eintrag wurde inzwischen geändert. Bitte neu laden.")
        parent = model.objects.get(pk=data["parent"].pk) if data.get("parent") else None
        if parent and (
            parent.pk == node.pk or (node_id and parent.pk in descendants(model, node.pk))
        ):
            raise ValidationError("Eine Hierarchie darf keinen Kreis bilden.")
        if parent:
            require_active(parent)
            require(actor, action, tree_scope(parent))
        else:
            require(actor, action)
        old_path = node.breadcrumb if node_id else None
        branch = descendants(model, node.pk) if node_id else []
        affected = list(
            Asset.objects.filter(
                **{"location_id__in" if model is Location else "category_id__in": branch}
            )
        )
        before = {str(a.pk): asset_snapshot(a) for a in affected}
        # Reparent/deactivation changes inherited scope; check the whole affected subtree.
        structural = node_id and (
            node.parent_id != (parent.pk if parent else None) or node.is_active != data["is_active"]
        )
        from resources.integrity import affected_resources, check_tree_change

        resource_ids = [r.pk for r in affected_resources(model, branch)] if structural else []
        if structural:
            check_tree_change(actor, resource_ids)
            for child in model.objects.filter(pk__in=branch):
                require(actor, action, tree_scope(child))
            for asset in affected:
                require(
                    actor, "asset.move" if model is Location else "asset.manage", asset_scope(asset)
                )
        node.name, node.description = data["name"], data.get("description", "")
        node.parent, node.is_active = parent, data["is_active"]
        node.revision += 1
        node.full_clean()
        node.save()
        if structural:
            check_tree_change(actor, resource_ids)
            for child in model.objects.filter(pk__in=branch):
                require(actor, action, tree_scope(child))
            for previous in affected:
                asset = Asset.objects.get(pk=previous.pk)
                require(
                    actor, "asset.move" if model is Location else "asset.manage", asset_scope(asset)
                )
        audit(
            actor,
            "location.saved" if model is Location else "category.saved",
            object_id=node.pk,
            details={
                "before_path": old_path,
                "after_path": node.breadcrumb,
                "active": node.is_active,
                "parent_id": str(node.parent_id) if node.parent_id else None,
                "affected_assets": before if structural else {},
                "affected_resources": [str(pk) for pk in resource_ids],
            },
        )
        bump(revision)
        return node


def normalize(namespace, raw):
    if not isinstance(raw, str) or len(raw) > 256:
        raise ValidationError("Der Code ist zu lang oder ungültig.")
    value = raw.strip(" \t\r\n")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/ -]{0,127}", value):
        raise ValidationError("Code: 1–128 druckbare ASCII-Zeichen, keine Steuerzeichen.")
    if namespace.normalization == "upper-ascii-v1":
        return value.upper()
    if namespace.normalization != "exact-v1":
        raise ValidationError("Unbekannte Normalisierungsversion.")
    return value


def insert_identifier(actor, asset, namespace, raw, kind, source=""):
    canonical = normalize(namespace, raw)
    row = Identifier(
        asset=asset,
        namespace=namespace,
        raw_value=raw.strip(" \t\r\n"),
        canonical_value=canonical,
        kind=kind,
        source=source,
        created_by=actor,
    )
    try:
        with transaction.atomic():
            row.full_clean(validate_unique=False, validate_constraints=False)
            row.save()
    except IntegrityError as exc:
        raise ValidationError(
            "Dieser Code ist bereits vergeben oder dauerhaft stillgelegt."
        ) from exc
    audit(
        actor,
        "identifier.assigned",
        object_id=row.pk,
        details={
            "asset_id": str(asset.pk),
            "namespace": namespace.key,
            "value": canonical,
            "kind": kind,
        },
    )
    return row


def owned_identifier(actor, asset):
    namespace = IdentifierNamespace.objects.get(key="deelvo", is_active=True)
    for _ in range(5):
        try:
            return insert_identifier(
                actor,
                asset,
                namespace,
                "DLV-" + secrets.token_hex(12).upper(),
                Identifier.Kind.OWNED,
                "Deelvo",
            )
        except ValidationError:
            continue
    raise ValidationError("Code konnte nicht erzeugt werden. Bitte erneut versuchen.")


def save_asset(actor, data, *, asset_id=None, expected_revision=None):
    data = dict(data)
    with authorization_write():
        asset = Asset.objects.get(pk=asset_id) if asset_id else Asset()
        before = asset_snapshot(asset) if asset_id else None
        if asset_id:
            require(actor, "asset.manage", asset_scope(asset))
            if asset.archived_at:
                raise ValidationError("Archivierte Assets sind unveränderlich.")
            if expected_revision != asset.revision:
                raise ValidationError("Das Asset wurde inzwischen geändert. Bitte neu laden.")
            if "inventory_number" in data and data["inventory_number"] != asset.inventory_number:
                raise ValidationError(
                    "Inventarnummer bleibt stabil; zusätzliche Codes bitte als Alias zuordnen."
                )
            if "location" in data and data["location"].pk != asset.location_id:
                raise ValidationError(
                    "Für Standortänderungen bitte den ausdrücklichen Umzugsdialog verwenden."
                )
        location = Location.objects.get(
            pk=(data["location"] if "location" in data else asset.location).pk
        )
        category = Category.objects.get(
            pk=(data["category"] if "category" in data else asset.category).pk
        )
        require_active(location)
        require_active(category)
        asset.location, asset.category = location, category
        target_scope = asset_scope(asset)
        require(actor, "asset.manage", target_scope)
        if "serial_number" in data or "internal_notes" in data:
            require(actor, "asset.read_sensitive", target_scope)
        if "acquisition_value" in data:
            require(actor, "asset.read_financial", target_scope)
        fields = {
            "inventory_number",
            "name",
            "description",
            "manufacturer",
            "model",
            "serial_number",
            "acquisition_date",
            "acquisition_value",
            "condition",
            "lifecycle",
            "internal_notes",
        }
        for field in fields & data.keys():
            setattr(asset, field, data[field])
        if "inventory_number" in data:
            namespace = IdentifierNamespace.objects.get(key="inventory")
            asset.inventory_number = normalize(namespace, data["inventory_number"])
            if len(asset.inventory_number) > 80:
                raise ValidationError("Inventarnummer: maximal 80 Zeichen.")
        if (
            before is not None and asset.lifecycle != before["lifecycle"]
        ) or asset.lifecycle == "retired":
            require(
                actor,
                "asset.archive" if asset.lifecycle == "retired" else "asset.manage",
                target_scope,
            )
        asset.revision += 1
        asset.updated_at = timezone.now()
        asset.full_clean()
        asset.save()
        if "tags" in data:
            asset.tags.set(data["tags"])
        if not asset_id:
            insert_identifier(
                actor,
                asset,
                IdentifierNamespace.objects.get(key="inventory", is_active=True),
                asset.inventory_number,
                Identifier.Kind.INVENTORY,
                "Inventarnummer",
            )
            owned_identifier(actor, asset)
        elif set(data) & {"condition", "lifecycle", "category"}:
            from bookings.integrity import asset_changed

            asset_changed(asset.pk)
        audit(
            actor,
            "asset.updated" if asset_id else "asset.created",
            object_id=asset.pk,
            details={
                "before": before,
                "after": asset_snapshot(asset),
                "fields": sorted(data.keys()),
            },
        )
        return asset


def move_asset(actor, asset_id, location_id, reason, expected_revision):
    with authorization_write():
        asset = read_asset(actor, asset_id, "asset.move")
        if asset.archived_at or asset.revision != expected_revision:
            raise ValidationError("Asset archiviert oder inzwischen geändert. Bitte neu laden.")
        if not reason.strip():
            raise ValidationError("Bitte einen Grund angeben.")
        destination = Location.objects.get(pk=location_id)
        require_active(destination)
        source = asset.location
        from_path = source.breadcrumb
        asset.location = destination
        require(actor, "asset.move", asset_scope(asset))
        if source.pk == destination.pk:
            return asset
        AssetMovement.objects.create(
            asset=asset,
            from_location=source,
            to_location=destination,
            from_path=from_path,
            to_path=destination.breadcrumb,
            actor=actor,
            reason=reason,
        )
        asset.revision += 1
        asset.updated_at = timezone.now()
        asset.save(update_fields=["location", "revision", "updated_at"])
        from bookings.integrity import asset_changed

        asset_changed(asset.pk)
        audit(
            actor,
            "asset.moved",
            object_id=asset.pk,
            reason=reason,
            details={
                "from": str(source.pk),
                "to": str(destination.pk),
                "from_path": from_path,
                "to_path": destination.breadcrumb,
            },
        )
        return asset


def archive_asset(actor, asset_id, expected_revision, reason):
    with authorization_write():
        asset = read_asset(actor, asset_id, "asset.archive")
        if asset.revision != expected_revision or not reason.strip():
            raise ValidationError("Bitte aktuellen Stand laden und Grund angeben.")
        if asset.archived_at:
            return asset
        before = asset_snapshot(asset)
        asset.archived_at = timezone.now()
        asset.lifecycle = Asset.Lifecycle.RETIRED
        asset.revision += 1
        asset.updated_at = timezone.now()
        asset.save(update_fields=["archived_at", "lifecycle", "revision", "updated_at"])
        from bookings.integrity import asset_changed

        asset_changed(asset.pk)
        audit(
            actor,
            "asset.archived",
            object_id=asset.pk,
            reason=reason,
            details={"before": before, "after": asset_snapshot(asset)},
        )
        return asset


def assign_identifier(actor, asset_id, namespace_id, raw, kind, source=""):
    with authorization_write():
        asset = read_asset(actor, asset_id, "identifier.assign")
        if asset.archived_at:
            raise ValidationError("Archivierten Assets keine neuen Codes zuordnen.")
        namespace = IdentifierNamespace.objects.get(pk=namespace_id, is_active=True)
        if namespace.key in {"deelvo", "inventory"}:
            raise ValidationError(
                "System-Namensräume werden ausschließlich bei Assetanlage befüllt."
            )
        return insert_identifier(actor, asset, namespace, raw, kind, source)


def retire_identifier(actor, asset_id, identifier_id, reason):
    with authorization_write():
        asset = read_asset(actor, asset_id, "identifier.retire")
        row = Identifier.objects.get(pk=identifier_id, asset=asset)
        if not reason.strip():
            raise ValidationError("Bitte einen Grund angeben.")
        if row.is_active:
            row.is_active, row.retired_at, row.retirement_reason = False, timezone.now(), reason
            row.save(update_fields=["is_active", "retired_at", "retirement_reason"])
            audit(
                actor,
                "identifier.retired",
                object_id=row.pk,
                reason=reason,
                details={
                    "asset_id": str(asset.pk),
                    "namespace": row.namespace.key,
                    "value": row.canonical_value,
                },
            )


@dataclass(frozen=True)
class Resolution:
    status: str
    asset_id: UUID | None = None
    name: str = ""
    inventory_number: str = ""
    unit_id: UUID | None = None
    resource_id: UUID | None = None
    resource_name: str = ""


def resolve_identifier(actor, namespace_id, raw):
    # Read-only; no audit noise, moves, observations, booking or loan operations.
    namespace = IdentifierNamespace.objects.filter(pk=namespace_id, is_active=True).first()
    if namespace is None:
        return Resolution("unknown")
    try:
        value = normalize(namespace, raw)
    except ValidationError:
        return Resolution("invalid")
    row = (
        Identifier.objects.filter(namespace=namespace, canonical_value=value, is_active=True)
        .select_related("asset__location", "asset__category")
        .first()
    )
    if row is None:
        return Resolution("unknown")
    # Thin projection adapter only; inventory models remain independent of resource services.
    from resources.identification import project_identifier

    return project_identifier(actor, row)


def save_namespace(actor, key, name, normalization):
    with authorization_write():
        require(actor, "identifier.namespace_manage")
        namespace = IdentifierNamespace(key=key, name=name, normalization=normalization)
        namespace.full_clean()
        namespace.save()
        audit(
            actor,
            "identifier.namespace_created",
            object_id=namespace.pk,
            details={"key": key, "normalization": normalization},
        )
        return namespace


def add_tag(actor, name):
    with authorization_write():
        require(actor, "category.manage")
        tag = Tag(name=name)
        tag.full_clean()
        tag.save()
        audit(actor, "tag.created", object_id=tag.pk)
        return tag
