from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from django.db import connection
from psycopg import sql


@pytest.fixture
def pg_factory(transactional_db):
    """One real, independently committed connection per participant."""
    assert connection.vendor == "postgresql", "PostgreSQL required; no SQLite substitute"
    db = connection.settings_dict
    params = dict(
        dbname=db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        host=db["HOST"],
        port=db["PORT"],
        connect_timeout=5,
    )
    schema = "prototype_" + uuid4().hex
    with psycopg.connect(**params, autocommit=True) as admin:
        admin.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        admin.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
        admin.execute(Path("prototypes/allocation/schema.sql").read_text())
    opened = []

    def factory():
        conn = psycopg.connect(
            **params,
            autocommit=True,
            options=f"-c search_path={schema},public -c statement_timeout=15000",
        )
        opened.append(conn)
        return conn

    yield factory
    for conn in opened:
        conn.close()
    with psycopg.connect(**params, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def staff():
    from accounts.models import AuthorizationRevision, Grant, Group, Membership, User
    from django.utils import timezone
    from inventory.models import IdentifierNamespace

    AuthorizationRevision.objects.get_or_create(pk=1)
    for key in ("deelvo", "inventory"):
        IdentifierNamespace.objects.get_or_create(
            key=key, defaults={"name": key, "normalization": "exact-v1"}
        )
    user = User.objects.create_user(
        "inventory@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name="Inventory test")
    Membership.objects.create(user=user, group=group)
    for action in (
        "asset.read",
        "asset.manage",
        "asset.move",
        "asset.archive",
        "asset.read_sensitive",
        "asset.read_financial",
        "identifier.resolve",
        "identifier.assign",
        "identifier.retire",
        "location.read",
        "location.manage",
        "category.read",
        "category.manage",
        "identifier.namespace_manage",
        "custom_field.manage",
        "asset.import",
        "asset.export",
        "asset.attach",
    ):
        Grant.objects.create(group=group, action=action, effect="allow")
    return user


@pytest.fixture
def registry(staff):
    from inventory import services
    from inventory.models import Category, Location

    root = services.save_tree(staff, Location, {"name": "Werkstatt", "is_active": True})
    shelf = services.save_tree(
        staff, Location, {"name": "Regal A", "parent": root, "is_active": True}
    )
    category = services.save_tree(staff, Category, {"name": "Freie Kategorie", "is_active": True})
    asset = services.save_asset(
        staff,
        {
            "inventory_number": "0001-a",
            "name": "Inventar-Mischpult",
            "location": shelf,
            "category": category,
            "serial_number": "PRIVATE-SERIAL",
            "internal_notes": "PRIVATE-NOTE",
            "acquisition_value": "100.00",
        },
    )
    return root, shelf, category, asset
