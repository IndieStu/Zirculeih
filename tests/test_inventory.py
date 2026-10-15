from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from accounts.models import AuditEvent, Grant, Group, Membership, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from inventory import services
from inventory.models import (
    Asset,
    AssetMovement,
    Identifier,
    IdentifierNamespace,
    Location,
)

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


def test_inventory_only_and_multiple_identifiers(staff, registry):
    root, shelf, category, asset = registry
    assert shelf.breadcrumb == "Werkstatt / Regal A"
    assert asset.inventory_number == "0001-a"
    assert asset.identifiers.count() == 2
    assert not hasattr(asset, "resource") and not hasattr(asset, "resourceunit")
    own = asset.identifiers.get(kind="owned")
    assert own.canonical_value.startswith("DLV-") and len(own.canonical_value) == 28
    assert (
        str(asset.pk) not in own.canonical_value
        and asset.inventory_number not in own.canonical_value
    )
    ns = services.save_namespace(staff, "legacy", "Alte Nummern", "upper-ascii-v1")
    alias = services.assign_identifier(staff, asset.pk, ns.pk, "  00ab-12\r\n", "external")
    assert alias.canonical_value == "00AB-12"
    count = AuditEvent.objects.count()
    for _ in range(5):
        result = services.resolve_identifier(staff, ns.pk, "00ab-12\r\n")
        assert result.status == "found" and result.asset_id == asset.pk
    assert AuditEvent.objects.count() == count
    asset.refresh_from_db()
    assert asset.location_id == shelf.pk
    assert not AssetMovement.objects.exists()


def test_tree_cycle_sql_and_service_protection(staff, registry):
    root, shelf, _, _ = registry
    with pytest.raises(ValidationError):
        services.save_tree(
            staff,
            Location,
            {"name": root.name, "parent": shelf, "is_active": True},
            node_id=root.pk,
            expected_revision=root.revision,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Location.objects.filter(pk=root.pk).update(parent=shelf)
    root.refresh_from_db()
    assert root.parent_id is None
    with pytest.raises(ProtectedError):
        shelf.delete()


def test_reparent_and_move_history(staff, registry):
    root, shelf, _, asset = registry
    destination = services.save_tree(staff, Location, {"name": "Außenlager", "is_active": True})
    changed = services.save_tree(
        staff,
        Location,
        {"name": shelf.name, "parent": destination, "is_active": True},
        node_id=shelf.pk,
        expected_revision=shelf.revision,
    )
    assert changed.breadcrumb == "Außenlager / Regal A"
    event = AuditEvent.objects.filter(action="location.saved", object_id=str(shelf.pk)).latest(
        "created_at"
    )
    assert event.details["before_path"] == "Werkstatt / Regal A"
    assert event.details["after_path"] == "Außenlager / Regal A"
    asset.refresh_from_db()
    services.move_asset(staff, asset.pk, root.pk, "Bewusster Umzug", asset.revision)
    move = AssetMovement.objects.get()
    assert move.from_location_id == shelf.pk and move.to_location_id == root.pk
    assert move.from_path == "Außenlager / Regal A" and move.to_path == "Werkstatt"
    assert move.actor_id == staff.pk
    with pytest.raises(ProtectedError):
        shelf.delete()


def test_condition_lifecycle_and_archive_are_independent(staff, registry):
    asset = registry[3]
    asset = services.save_asset(
        staff, {"condition": "damaged"}, asset_id=asset.pk, expected_revision=asset.revision
    )
    assert asset.condition == "damaged" and asset.lifecycle == "active"
    asset = services.save_asset(
        staff, {"lifecycle": "maintenance"}, asset_id=asset.pk, expected_revision=asset.revision
    )
    assert asset.condition == "damaged" and asset.lifecycle == "maintenance"
    services.archive_asset(staff, asset.pk, asset.revision, "Ausgemustert")
    asset.refresh_from_db()
    assert asset.archived_at and asset.lifecycle == "retired" and asset.condition == "damaged"
    assert asset.identifiers.count() == 2
    with pytest.raises(ValidationError):
        services.save_asset(
            staff, {"name": "Changed"}, asset_id=asset.pk, expected_revision=asset.revision
        )
    with pytest.raises(ValidationError):
        services.save_asset(
            staff,
            {
                "inventory_number": asset.inventory_number,
                "name": "Reuse",
                "location": registry[1],
                "category": registry[2],
            },
        )
    assert AuditEvent.objects.filter(action="asset.archived", actor=staff).exists()


def test_inventory_number_is_permanent_and_optimistic_revision(staff, registry):
    asset = registry[3]
    with pytest.raises(ValidationError):
        services.save_asset(
            staff, {"inventory_number": "new"}, asset_id=asset.pk, expected_revision=asset.revision
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Asset.objects.filter(pk=asset.pk).update(inventory_number="new")
    with pytest.raises(ValidationError):
        services.save_asset(
            staff, {"name": "stale"}, asset_id=asset.pk, expected_revision=asset.revision - 1
        )
    with pytest.raises(ValidationError):
        services.save_asset(
            staff, {"location": registry[0]}, asset_id=asset.pk, expected_revision=asset.revision
        )


def test_identifier_unique_retired_and_immutable_target(staff, registry):
    asset = registry[3]
    ns = services.save_namespace(staff, "legacy", "Altcodes", "exact-v1")
    row = services.assign_identifier(staff, asset.pk, ns.pk, "Code-01", "barcode")
    other = services.save_asset(
        staff,
        {
            "inventory_number": "0002",
            "name": "Other",
            "location": registry[1],
            "category": registry[2],
        },
    )
    with pytest.raises(ValidationError):
        services.assign_identifier(staff, other.pk, ns.pk, "Code-01", "qr")
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.filter(pk=row.pk).update(asset=other)
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.filter(pk=row.pk).delete()
    services.retire_identifier(staff, asset.pk, row.pk, "Altes Etikett")
    assert services.resolve_identifier(staff, ns.pk, "Code-01").status == "unknown"
    with pytest.raises(ValidationError):
        services.assign_identifier(staff, other.pk, ns.pk, "Code-01", "barcode")
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.filter(pk=row.pk).update(is_active=True, retired_at=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        IdentifierNamespace.objects.filter(pk=ns.pk).update(normalization="upper-ascii-v1")


@pytest.mark.parametrize(
    "raw", ["", "x" * 257, "<script>alert(1)</script>", "foo\x00bar", "foo\nbar", "☃"]
)
def test_malicious_identifier_is_clean_invalid(staff, registry, raw):
    ns = IdentifierNamespace.objects.get(key="inventory")
    assert services.resolve_identifier(staff, ns.pk, raw).status == "invalid"
    assert services.resolve_identifier(staff, ns.pk, "nonexistent").status == "unknown"


def test_exact_namespace_retains_case_and_zeroes(staff, registry):
    ns = services.save_namespace(staff, "case", "Exakt", "exact-v1")
    one = services.assign_identifier(staff, registry[3].pk, ns.pk, "000a", "barcode")
    two = services.assign_identifier(staff, registry[3].pk, ns.pk, "000A", "barcode")
    assert one.pk != two.pk and one.canonical_value == "000a"
    with pytest.raises(IntegrityError), transaction.atomic():
        Identifier.objects.create(
            namespace=ns,
            asset=registry[3],
            kind="barcode",
            raw_value="wrong",
            canonical_value="WRONG",
            created_by=staff,
        )


def limited_user(root, *, manage=False):
    user = User.objects.create_user(
        "limited@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name="Limited")
    Membership.objects.create(user=user, group=group)
    for action in (
        "asset.read",
        "identifier.resolve",
        *(["asset.manage", "asset.move"] if manage else []),
    ):
        Grant.objects.create(
            group=group,
            action=action,
            effect="allow",
            scope_kind="location",
            scope_id=root.pk,
            inherit=True,
        )
    return user, group


def test_scoped_inventory_and_no_status_bypass(staff, registry):
    root, _, category, asset = registry
    user, group = limited_user(root, manage=True)
    assert services.read_asset(user, asset.pk).pk == asset.pk
    assert services.visible_assets(user).count() == 1
    elsewhere = services.save_tree(staff, Location, {"name": "Privat", "is_active": True})
    foreign = services.save_asset(
        staff,
        {
            "inventory_number": "private",
            "name": "Hidden",
            "location": elsewhere,
            "category": category,
        },
    )
    with pytest.raises(PermissionDenied):
        services.read_asset(user, foreign.pk)
    with pytest.raises(PermissionDenied):
        services.move_asset(user, asset.pk, elsewhere.pk, "Scope escape", asset.revision)
    Grant.objects.create(
        group=group, action="asset.read", effect="deny", scope_kind="asset", scope_id=asset.pk
    )
    assert not services.visible_assets(user).exists()
    with pytest.raises(PermissionDenied):
        services.read_asset(user, asset.pk)
    admin = User.objects.create_user(
        "admin-inv@example.test",
        "Quiet-River-8941!Cloud",
        is_system_admin=True,
        is_employee=True,
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    with pytest.raises(PermissionDenied):
        services.read_asset(admin, asset.pk)


def test_unknown_and_unauthorized_lookup_identical(staff, registry):
    user = User.objects.create_user(
        "no-grant@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    ns = IdentifierNamespace.objects.get(key="inventory")
    assert services.resolve_identifier(
        user, ns.pk, registry[3].inventory_number
    ) == services.resolve_identifier(user, ns.pk, "not-known")


def test_sensitive_fields_not_implied_by_asset_manage(staff, registry):
    user, group = limited_user(registry[0], manage=True)
    asset = registry[3]
    with pytest.raises(PermissionDenied):
        services.save_asset(
            user, {"serial_number": "new"}, asset_id=asset.pk, expected_revision=asset.revision
        )
    with pytest.raises(PermissionDenied):
        services.save_asset(
            user, {"acquisition_value": "10"}, asset_id=asset.pk, expected_revision=asset.revision
        )
    asset = services.save_asset(
        user, {"name": "Allowed"}, asset_id=asset.pk, expected_revision=asset.revision
    )
    assert asset.serial_number == "PRIVATE-SERIAL"


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_identifier_one_winner(staff, registry):
    ns = services.save_namespace(staff, "race", "Race", "exact-v1")
    barrier = Barrier(4)

    def claim(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                with transaction.atomic():
                    Identifier.objects.create(
                        namespace_id=ns.pk,
                        asset_id=registry[3].pk,
                        kind="external",
                        raw_value="same",
                        canonical_value="same",
                        created_by_id=staff.pk,
                    )
                return True
            except IntegrityError:
                return False
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert sum(executor.map(claim, range(4))) == 1
    assert Identifier.objects.filter(namespace=ns, canonical_value="same").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_sql_reparent_cannot_create_cycle(staff):
    a, b = Location.objects.create(name="A"), Location.objects.create(name="B")
    barrier = Barrier(2)

    def move(pair):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                with transaction.atomic():
                    Location.objects.filter(pk=pair[0]).update(parent_id=pair[1])
                return True
            except IntegrityError:
                return False
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(move, [(a.pk, b.pk), (b.pk, a.pk)])) == 1
    for node in Location.objects.all():
        assert len(node.lineage) <= 2
