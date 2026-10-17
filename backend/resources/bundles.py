"""Bounded component graph; configuration is separate from immutable reservations."""

from accounts.authorization import authorization_write, require
from accounts.services import audit
from django.core.exceptions import ValidationError

from .models import BundleComponent, Resource
from .services import editable, resource_scope

MAX_MEMBERS = 20


def expansion(resource, optional_ids=()):
    optional = {str(pk) for pk in optional_ids}
    from uuid import UUID

    seen: set[UUID] = set()
    visiting: set[UUID] = set()
    result, recognized = [], set()

    def visit(node, required=True):
        if node.pk in visiting:
            raise ValidationError("Bundles dürfen keinen Kreis enthalten.")
        if node.pk in seen:
            raise ValidationError("Eine Komponente darf im Bundle nur einmal vorkommen.")
        if len(seen) >= MAX_MEMBERS:
            raise ValidationError("Ein Bundle darf höchstens 20 Angebote enthalten.")
        seen.add(node.pk)
        visiting.add(node.pk)
        result.append((node, required))
        for link in node.bundle_components.select_related("component__location", "component__type"):
            recognized.add(str(link.component_id))
            if link.required or str(link.component_id) in optional:
                visit(link.component, required and link.required)
        visiting.remove(node.pk)

    visit(resource)
    if optional - recognized:
        raise ValidationError("Unbekannte optionale Komponente.")
    return result


def _configure(actor, resource_id, components, expected_revision):
    """components contains (Resource, required) pairs; never alter past member sets."""
    from .services import check_revision

    with authorization_write():
        resource = Resource.objects.select_for_update().get(pk=resource_id)
        editable(resource)
        require(actor, "resource.manage", resource_scope(resource))
        require(actor, "booking.configure", resource_scope(resource))
        check_revision(resource, expected_revision)
        ids = [r.pk for r, required in components]
        if len(set(ids)) != len(ids) or len(ids) >= MAX_MEMBERS:
            raise ValidationError("Eindeutige Komponenten wählen (höchstens 19).")
        for row, _required in components:
            require(actor, "booking.configure", resource_scope(row))
            if row.pk == resource.pk or row.archived_at:
                raise ValidationError("Eine aktive andere Komponente wählen.")
            # Common calendar unit and timezone; each component retains its own use mode.
            if not hasattr(row, "bookingpolicy") or not hasattr(resource, "bookingpolicy"):
                raise ValidationError("Buchungsregeln zuerst für alle Angebote einrichten.")
            if (row.bookingpolicy.time_mode, row.bookingpolicy.timezone) != (
                resource.bookingpolicy.time_mode,
                resource.bookingpolicy.timezone,
            ):
                raise ValidationError(
                    "Bundle-Komponenten benötigen denselben Zeitmodus und dieselbe Zeitzone."
                )
        BundleComponent.objects.filter(resource=resource).delete()
        for component, required in components:
            BundleComponent.objects.create(
                resource=resource, component=component, required=required
            )
        # Validate even optional branches and every affected ancestor before commit.
        roots = [resource]
        frontier = [resource.pk]
        while frontier:
            parents = list(
                Resource.objects.filter(bundle_components__component_id__in=frontier).distinct()
            )
            frontier = [r.pk for r in parents if r.pk not in {x.pk for x in roots}]
            roots.extend(r for r in parents if r.pk in frontier)
        for root in roots:
            # expansion requires only supplied IDs recognized by this particular tree.
            def validate(node, path, count):
                if node.pk in path:
                    raise ValidationError("Bundles dürfen keinen Kreis enthalten.")
                if node.pk in count or len(count) >= MAX_MEMBERS:
                    raise ValidationError(
                        "Komponenten müssen eindeutig und auf 20 Angebote begrenzt sein."
                    )
                count.add(node.pk)
                for link in node.bundle_components.select_related("component"):
                    validate(link.component, path | {node.pk}, count)

            validate(root, set(), set())
        resource.revision += 1
        resource.save(update_fields=["revision"])
        audit(
            actor,
            "resource.bundle_configured",
            object_id=resource.pk,
            details={
                "components": [
                    {"id": str(r.pk), "required": required} for r, required in components
                ]
            },
        )
        return resource


def configure(actor, resource_id, components, expected_revision):
    from django.db import IntegrityError

    try:
        return _configure(actor, resource_id, components, expected_revision)
    except IntegrityError as exc:
        raise ValidationError(
            "Ungültige Bundle-Struktur: kein Kreis und keine doppelten Komponenten."
        ) from exc
