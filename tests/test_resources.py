from uuid import uuid4

import pytest
from accounts.models import Grant, Group, Membership, User
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from inventory import services as inventory
from inventory.models import Identifier, IdentifierNamespace, Location
from resources import services
from resources.models import PoolMembership, Resource, ResourcePool, ResourceUnit
from test_inventory_extensions import image_upload

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture
def editor(staff):
    group = staff.membership_set.get(removed_at=None).group
    for action in (
        "resource.manage",
        "resource.publish",
        "resource.type_manage",
        "catalog.view_private",
    ):
        Grant.objects.create(group=group, action=action, effect="allow")
    return staff


@pytest.fixture
def offer(editor, registry):
    kind = services.save_type(editor, {"key": "shared", "name": "Frei benannter Typ"})
    return services.save_resource(
        editor,
        {
            "title": "Gemeinsames Mischpult",
            "slug": "mischpult",
            "type": kind,
            "location": registry[1],
            "location_label": "Öffentliche Werkstatt",
            "categories": [registry[2]],
            "visibility": "public",
            "is_featured": True,
            "description": "Gemeinsam kreativ werden",
            "summary": "Für Veranstaltungen",
        },
    )


def publish(editor, offer):
    services.save_unit(editor, offer.pk, {"name": "Logische Kapazität"})
    return services.publication(editor, offer.pk, offer.revision, "publish", "Redaktionell geprüft")


def reader(action, scope_kind="organization", scope_id=None):
    user = User.objects.create_user(
        str(uuid4()) + "@example.test",
        "Review-safe-2026!Test",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name=str(uuid4()))
    Membership.objects.create(group=group, user=user)
    Grant.objects.create(
        group=group, action=action, effect="allow", scope_kind=scope_kind, scope_id=scope_id
    )
    return user, group


def test_draft_publication_and_withdrawal(editor, offer, client):
    assert not services.visible_resources(AnonymousUser()).exists()
    assert client.get(reverse("resource_detail", args=[offer.slug])).status_code == 404
    with pytest.raises(ValidationError):
        services.publication(editor, offer.pk, offer.revision, "publish", "No unit")
    offer = publish(editor, offer)
    assert services.visible_resources(AnonymousUser()).get().pk == offer.pk
    assert client.get(reverse("resource_detail", args=[offer.slug])).status_code == 200
    offer = services.publication(editor, offer.pk, offer.revision, "withdraw", "Pause")
    assert client.get(reverse("resource_detail", args=[offer.slug])).status_code == 404
    assert not services.visible_resources(AnonymousUser()).exists()


def test_private_scope_deny_and_admin_no_bypass(editor, offer, registry, client):
    offer.visibility = "private"
    offer.save()
    publish(editor, offer)
    user, group = reader("catalog.view_private", "resource", offer.pk)
    assert services.visible_resources(user).count() == 1
    assert not services.visible_resources(AnonymousUser()).exists()
    Grant.objects.create(
        group=group,
        action="catalog.view_private",
        effect="deny",
        scope_kind="category",
        scope_id=registry[2].pk,
    )
    assert not services.visible_resources(user).exists()
    user.is_system_admin = True
    user.save()
    assert not services.visible_resources(user).exists()
    client.force_login(user)
    assert client.get(reverse("resource_detail", args=[offer.slug])).status_code == 404
    assert client.get(reverse("resource_manage", args=[offer.pk])).status_code == 404


def test_public_pages_never_expose_private_inventory(editor, offer, registry, client):
    services.save_unit(editor, offer.pk, {"name": "PRIVATE-UNIT", "asset": registry[3]})
    offer = services.publication(editor, offer.pk, offer.revision, "publish", "Reviewed")
    for url in (reverse("home"), reverse("catalog"), reverse("resource_detail", args=[offer.slug])):
        response = client.get(url)
        assert response.status_code == 200
        for secret in ("PRIVATE-SERIAL", "PRIVATE-NOTE", "PRIVATE-UNIT", "0001-a", "Regal A"):
            assert secret.encode() not in response.content
        assert b"Online-Reservierungen" in response.content or url == reverse("catalog")
        assert response["Cache-Control"] == "no-store, private"
    assert b"Gemeinsames Mischpult" in client.get(reverse("home")).content


def test_inactive_ancestor_removes_publication_from_catalog(editor, offer, registry, client):
    publish(editor, offer)
    Location.objects.filter(pk=registry[0].pk).update(is_active=False)
    assert not services.visible_resources(AnonymousUser()).exists()
    assert client.get(reverse("resource_detail", args=[offer.slug])).status_code == 404


def test_asset_optional_and_permanently_unique(editor, offer, registry):
    logical = services.save_unit(editor, offer.pk, {"name": "Raum ohne Asset"})
    physical = services.save_unit(editor, offer.pk, {"name": "Physisch", "asset": registry[3]})
    assert logical.asset_id is None and physical.asset_id == registry[3].pk
    with pytest.raises(ValidationError):
        services.save_unit(editor, offer.pk, {"name": "Doppelt", "asset": registry[3]})
    services.save_unit(
        editor,
        offer.pk,
        {"is_active": False},
        unit_id=physical.pk,
        expected_revision=physical.revision,
    )
    with pytest.raises(ValidationError):
        services.save_unit(editor, offer.pk, {"name": "Wiederverwendung", "asset": registry[3]})
    with pytest.raises(IntegrityError), transaction.atomic():
        ResourceUnit.objects.filter(pk=physical.pk).update(asset=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        physical.delete()


def test_unit_requires_asset_permissions(editor, offer, registry):
    actor, _ = reader("resource.manage")
    with pytest.raises(PermissionDenied):
        services.save_unit(actor, offer.pk, {"name": "Forbidden", "asset": registry[3]})
    assert not offer.units.exists()


def test_publish_and_published_edits_require_separate_right(editor, offer):
    actor, _ = reader("resource.manage")
    services.save_unit(actor, offer.pk, {"name": "Logical"})
    with pytest.raises(PermissionDenied):
        services.publication(actor, offer.pk, offer.revision, "publish", "Not permitted")
    offer = services.publication(editor, offer.pk, offer.revision, "publish", "Reviewed")
    with pytest.raises(PermissionDenied):
        services.save_resource(
            actor, {"title": "Unreviewed"}, resource_id=offer.pk, expected_revision=offer.revision
        )


def test_stale_revision_and_archive(editor, offer):
    with pytest.raises(ValidationError):
        services.save_resource(
            editor, {"title": "Stale"}, resource_id=offer.pk, expected_revision=0
        )
    offer = publish(editor, offer)
    archived = services.publication(editor, offer.pk, offer.revision, "archive", "Retired")
    assert archived.archived_at and not archived.published_at
    assert not services.visible_resources(AnonymousUser()).exists()
    with pytest.raises(ValidationError):
        services.save_unit(editor, offer.pk, {"name": "No more"})
    with pytest.raises(IntegrityError), transaction.atomic():
        Resource.objects.filter(pk=offer.pk).update(archived_at=None)


def test_pool_same_resource_unique_membership_and_database_guard(editor, offer):
    a = services.save_unit(editor, offer.pk, {"name": "A"})
    b = services.save_unit(editor, offer.pk, {"name": "B"})
    pool = services.save_pool(editor, offer.pk, "Equivalent", [a, b])
    assert pool.memberships.count() == 2
    other = services.save_resource(
        editor, {"title": "Other", "slug": "other", "type": offer.type, "location": offer.location}
    )
    foreign = services.save_unit(editor, other.pk, {"name": "Foreign"})
    with pytest.raises(ValidationError):
        services.save_pool(editor, offer.pk, "Wrong", [foreign])
    with pytest.raises(ValidationError):
        services.save_pool(editor, offer.pk, "Duplicate", [a])
    with pytest.raises(IntegrityError), transaction.atomic():
        PoolMembership.objects.create(pool=pool, unit=foreign)
    with pytest.raises(IntegrityError), transaction.atomic():
        ResourcePool.objects.filter(pk=pool.pk).update(resource=other)


def test_unit_identifiers_xor_canonical_asset_and_immutable(editor, offer, registry):
    unit = services.save_unit(editor, offer.pk, {"name": "Physical", "asset": registry[3]})
    ns = inventory.save_namespace(editor, "unit-codes", "Unit Codes", "exact-v1")
    code = services.assign_unit_identifier(editor, unit.pk, ns.pk, "UNIT-001", "barcode")
    assert code.asset_id is None and code.unit_id == unit.pk
    found = inventory.resolve_identifier(editor, ns.pk, "UNIT-001")
    assert (
        found.asset_id == registry[3].pk
        and found.unit_id == unit.pk
        and found.resource_id == offer.pk
    )
    asset_code = inventory.resolve_identifier(
        editor, IdentifierNamespace.objects.get(key="inventory").pk, registry[3].inventory_number
    )
    assert asset_code.asset_id == found.asset_id and asset_code.unit_id == unit.pk
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.filter(pk=code.pk).update(asset=registry[3])
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.filter(pk=code.pk).update(unit=None, asset=registry[3])
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.create(
            namespace=ns,
            canonical_value="EMPTY",
            raw_value="EMPTY",
            kind="external",
            created_by=editor,
        )
    services.retire_unit_identifier(editor, unit.pk, code.pk, "Damaged label")
    assert inventory.resolve_identifier(editor, ns.pk, "UNIT-001").status == "unknown"
    with pytest.raises(ValidationError):
        services.assign_unit_identifier(editor, unit.pk, ns.pk, "UNIT-001", "qr")


def test_logical_resolution_and_no_resource_or_asset_scope_leak(editor, offer, registry, client):
    logical = services.save_unit(editor, offer.pk, {"name": "Logische Einheit"})
    physical = services.save_unit(editor, offer.pk, {"name": "Physisch", "asset": registry[3]})
    ns = inventory.save_namespace(editor, "logical", "Logical", "exact-v1")
    services.assign_unit_identifier(editor, logical.pk, ns.pk, "LOGICAL", "qr")
    services.assign_unit_identifier(editor, physical.pk, ns.pk, "PHYSICAL", "qr")
    actor, _ = reader("identifier.resolve", "resource", offer.pk)
    assert inventory.resolve_identifier(actor, ns.pk, "LOGICAL").unit_id == logical.pk
    assert inventory.resolve_identifier(actor, ns.pk, "PHYSICAL").status == "unknown"
    client.force_login(actor)
    response = client.post(reverse("identifier_lookup"), {"namespace": ns.pk, "code": "LOGICAL"})
    assert response.status_code == 200 and b"Einheit erkannt" in response.content
    assert b"Assetdetails" not in response.content


def test_catalog_search_filters_escape_and_does_not_search_inventory(
    editor, offer, registry, client
):
    publish(editor, offer)
    assert (
        client.get(reverse("catalog"), {"q": "PRIVATE-SERIAL"}).context["page_obj"].paginator.count
        == 0
    )
    assert (
        client.get(reverse("catalog"), {"q": "Mischpult", "category": registry[2].pk})
        .context["page_obj"]
        .paginator.count
        == 1
    )
    assert (
        client.get(reverse("catalog"), {"location": "invalid"}).context["page_obj"].paginator.count
        == 0
    )
    Resource.objects.filter(pk=offer.pk).update(description="<script>alert(1)</script>")
    response = client.get(reverse("resource_detail", args=[offer.slug]))
    assert b"<script>" not in response.content and b"&lt;script&gt;" in response.content


def test_gallery_is_separate_private_until_publication_and_revoked(
    editor, offer, registry, client, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    row = services.upload_image(editor, offer.pk, image_upload(), "Synthetisches Bild")
    assert client.get(reverse("resource_image", args=[row.pk])).status_code == 404
    offer = publish(editor, offer)
    response = client.get(reverse("resource_image", args=[row.pk]))
    assert response.status_code == 200 and response["Content-Type"] == "image/jpeg"
    assert b"".join(response.streaming_content).startswith(b"\xff\xd8")
    assert response["Cache-Control"] == "no-store, private"
    services.publication(editor, offer.pk, offer.revision, "withdraw", "Privacy review")
    assert client.get(reverse("resource_image", args=[row.pk])).status_code == 404
    assert registry[3].media.count() == 0


def test_resource_csrf_idor_forms_and_mass_assignment(editor, offer, registry, client):
    secured = Client(enforce_csrf_checks=True)
    secured.force_login(editor)
    assert secured.post(reverse("resource_publish", args=[offer.pk]), {}).status_code == 403
    client.force_login(editor)
    for name in ("resources_manage", "resource_create", "resource_types"):
        assert client.get(reverse(name)).status_code == 200
    assert client.get(reverse("resource_manage", args=[offer.pk])).status_code == 200
    for name in (
        "unit_create",
        "pool_create",
        "resource_image_upload",
        "resource_edit",
        "resource_publish",
    ):
        assert client.get(reverse(name, args=[offer.pk])).status_code == 200
    with pytest.raises(ValidationError):
        services.save_resource(
            editor,
            {"published_at": timezone.now()},
            resource_id=offer.pk,
            expected_revision=offer.revision,
        )
    outsider, _ = reader("catalog.view_public")
    client.force_login(outsider)
    assert client.get(reverse("resource_manage", args=[offer.pk])).status_code == 404


@pytest.mark.django_db(transaction=True)
def test_concurrent_physical_unit_claim_has_one_winner(editor, offer, registry):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    barrier = Barrier(2)

    def claim(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                services.save_unit(editor, offer.pk, {"name": str(index), "asset": registry[3]})
                return "created"
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(claim, range(2)))
    assert sorted(results) == ["conflict", "created"]
    assert ResourceUnit.objects.filter(asset=registry[3]).count() == 1


def test_hierarchy_change_cannot_shift_resource_scope_without_rights(editor, offer, registry):
    actor, group = reader("location.manage")
    for action in ("asset.move",):
        Grant.objects.create(group=group, action=action, effect="allow")
    target = inventory.save_tree(editor, Location, {"name": "Other branch", "is_active": True})
    with pytest.raises(PermissionDenied):
        inventory.save_tree(
            actor,
            Location,
            {"name": registry[0].name, "parent": target, "is_active": True},
            node_id=registry[0].pk,
            expected_revision=registry[0].revision,
        )
    registry[0].refresh_from_db()
    assert registry[0].parent_id is None


def test_published_hierarchy_change_needs_publish_right(editor, offer, registry):
    publish(editor, offer)
    actor, group = reader("location.manage")
    for action in ("asset.move", "resource.manage"):
        Grant.objects.create(group=group, action=action, effect="allow")
    with pytest.raises(PermissionDenied):
        inventory.save_tree(
            actor,
            Location,
            {"name": registry[0].name, "is_active": False},
            node_id=registry[0].pk,
            expected_revision=registry[0].revision,
        )
    registry[0].refresh_from_db()
    assert registry[0].is_active


def test_pool_eligible_count_derived_from_real_units_and_asset_state(editor, offer, registry):
    a = services.save_unit(editor, offer.pk, {"name": "Physical", "asset": registry[3]})
    b = services.save_unit(editor, offer.pk, {"name": "Logical"})
    pool = services.save_pool(editor, offer.pk, "Pool", [a, b])
    assert services.eligible_pool_units(editor, pool).count() == 2
    inventory.save_asset(
        editor,
        {"condition": "damaged"},
        asset_id=registry[3].pk,
        expected_revision=registry[3].revision,
    )
    assert list(services.eligible_pool_units(editor, pool)) == [b]
    services.save_unit(
        editor, offer.pk, {"is_active": False}, unit_id=b.pk, expected_revision=b.revision
    )
    assert not services.eligible_pool_units(editor, pool).exists()


def test_permanent_slug_and_reserved_routes(editor, offer):
    with pytest.raises(ValidationError):
        services.save_resource(
            editor, {"slug": "changed"}, resource_id=offer.pk, expected_revision=offer.revision
        )
    with pytest.raises(ValidationError):
        services.save_resource(
            editor,
            {
                "title": "Reserved",
                "slug": "verwaltung",
                "location": offer.location,
                "type": offer.type,
            },
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Resource.objects.filter(pk=offer.pk).update(slug="raw-change")


def test_unit_physical_target_move_and_xor_do_not_reinterpret_labels(editor, offer, registry):
    unit = services.save_unit(editor, offer.pk, {"name": "Logical"})
    physical = services.save_unit(editor, offer.pk, {"name": "Physical", "asset": registry[3]})
    ns = inventory.save_namespace(editor, "xor", "XOR", "exact-v1")
    code = services.assign_unit_identifier(editor, unit.pk, ns.pk, "UNIT", "qr")
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.filter(pk=code.pk).update(unit=physical)
    with pytest.raises(ValidationError):
        services.save_unit(
            editor,
            offer.pk,
            {"asset": registry[3]},
            unit_id=unit.pk,
            expected_revision=unit.revision,
        )


def test_catalog_image_does_not_accept_document_or_missing_alt(editor, offer, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    with pytest.raises(ValidationError):
        services.upload_image(editor, offer.pk, SimpleUploadedFile("manual.txt", b"Text"), "Text")
    with pytest.raises(ValidationError):
        services.upload_image(editor, offer.pk, image_upload(), "  ")
    assert not offer.images.exists() and not list(tmp_path.iterdir())


def test_operational_post_flow_create_unit_publish_and_filtered_catalog(editor, registry, client):
    kind = services.save_type(editor, {"key": "room", "name": "Raum"})
    client.force_login(editor)
    response = client.post(
        reverse("resource_create"),
        {
            "title": "Seminarraum",
            "slug": "seminarraum",
            "type": kind.pk,
            "location": registry[1].pk,
            "location_label": "Haupteingang",
            "categories": [registry[2].pk],
            "visibility": "public",
            "revision": 0,
        },
    )
    assert response.status_code == 302, (
        response.context["form"].errors if response.status_code == 200 else response.content
    )
    row = Resource.objects.get(slug="seminarraum")
    assert not row.published_at and not row.units.exists()
    assert (
        client.post(
            reverse("unit_create", args=[row.pk]),
            {"name": "Raum", "is_active": "on", "revision": 0},
        ).status_code
        == 302
    )
    assert (
        client.post(
            reverse("resource_publish", args=[row.pk]),
            {"operation": "publish", "reason": "Reviewed", "revision": row.revision},
        ).status_code
        == 302
    )
    client.logout()
    assert client.get(reverse("resource_detail", args=[row.slug])).status_code == 200
    assert (
        client.get(reverse("catalog"), {"type": kind.pk}).context["page_obj"].paginator.count == 1
    )


def test_scoped_resource_grant_selector_and_unauthorized_target(editor, offer):
    from accounts.forms import GrantForm

    actor, _ = reader("resource.manage", "resource", offer.pk)
    data = {
        "action": "catalog.view_private",
        "effect": "allow",
        "scope_kind": "resource",
        "scope_resource": offer.pk,
    }
    form = GrantForm(data, actor=actor)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["scope_id"] == offer.pk
    stranger, _ = reader("catalog.view_public")
    assert not GrantForm(data, actor=stranger).is_valid()


def test_unauthorized_pool_projection_requires_current_actor(editor, offer):
    unit = services.save_unit(editor, offer.pk, {"name": "Unit"})
    pool = services.save_pool(editor, offer.pk, "Pool", [unit])
    actor, _ = reader("catalog.view_public")
    with pytest.raises(PermissionDenied):
        services.eligible_pool_units(actor, pool)


def test_reparent_rechecks_resource_deny_in_new_ancestor(editor, offer, registry):
    target = inventory.save_tree(editor, Location, {"name": "Restricted", "is_active": True})
    group = editor.membership_set.get(removed_at=None).group
    Grant.objects.create(
        group=group,
        action="resource.manage",
        effect="deny",
        scope_kind="location",
        scope_id=target.pk,
        inherit=True,
    )
    with pytest.raises(PermissionDenied):
        inventory.save_tree(
            editor,
            Location,
            {"name": registry[0].name, "parent": target, "is_active": True},
            node_id=registry[0].pk,
            expected_revision=registry[0].revision,
        )
    registry[0].refresh_from_db()
    assert registry[0].parent_id is None


def test_public_gallery_does_not_publish_existing_inventory_media(
    editor, offer, registry, settings, tmp_path, client
):
    from inventory import extensions

    settings.MEDIA_ROOT = tmp_path
    private = extensions.upload_media(editor, registry[3].pk, image_upload(), is_sensitive=True)
    public = services.upload_image(
        editor, offer.pk, image_upload(), "Öffentlich geprüftes Testbild"
    )
    publish(editor, offer)
    assert client.get(reverse("media_download", args=[private.pk])).status_code == 302
    assert client.get(reverse("resource_image", args=[private.pk])).status_code == 404
    response = client.get(reverse("resource_image", args=[public.pk]))
    assert response.status_code == 200
    response.close()
    assert private.storage_name != public.storage_name
