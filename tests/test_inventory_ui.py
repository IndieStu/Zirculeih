from uuid import uuid4

import pytest
from accounts.models import Grant, Group, Membership, User
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from inventory import extensions, services
from inventory.models import Asset, IdentifierNamespace, Location
from test_inventory import limited_user
from test_inventory_extensions import csv_upload, image_upload

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture(autouse=True)
def inventory_ui_settings(settings):
    settings.SECURE_SSL_REDIRECT = False


def test_dashboard_scopes_actions_attention_and_personal_area(staff, registry, client):
    root, shelf, category, asset = registry
    asset = services.save_asset(
        staff, {"condition": "damaged"}, asset_id=asset.pk, expected_revision=asset.revision
    )
    elsewhere = services.save_tree(staff, Location, {"name": "Secret Place", "is_active": True})
    services.save_asset(
        staff,
        {
            "inventory_number": "SECRET",
            "name": "SECRET-ASSET",
            "location": elsewhere,
            "category": category,
            "condition": "inspection",
        },
    )
    user, _ = limited_user(root)
    client.force_login(user)
    response = client.get(reverse("inventory_dashboard"))
    assert response.status_code == 200
    assert response.context["attention_count"] == 1 and response.context["asset_count"] == 1
    assert asset.name.encode() in response.content and b"SECRET-ASSET" not in response.content
    assert b"Asset anlegen" not in response.content and b"Code scannen" in response.content
    assert b"Checkout" not in response.content and b"Buchung anlegen" not in response.content
    assert response.content.index(b"Inventar pr") < response.content.index(b"Inventarbestand")
    ordinary = User.objects.create_user(
        "ordinary@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    client.force_login(ordinary)
    assert client.get(reverse("inventory_dashboard")).url == reverse("account")
    assert client.get(reverse("asset_list")).status_code == 404
    assert b"Betriebs\xc3\xbcbersicht" not in client.get(reverse("account")).content


def test_asset_list_detail_search_filters_and_protected_fields(staff, registry, client):
    user, group = limited_user(registry[0])
    Grant.objects.create(group=group, action="category.read", effect="allow")
    Grant.objects.create(group=group, action="location.read", effect="allow")
    client.force_login(user)
    response = client.get(reverse("asset_list"), {"q": "Mischpult", "location": registry[0].pk})
    assert response.status_code == 200 and response.context["page_obj"].paginator.count == 1
    assert (
        client.get(reverse("asset_list"), {"q": "not there"}).context["page_obj"].paginator.count
        == 0
    )
    assert (
        client.get(reverse("asset_list"), {"location": "invalid"})
        .context["page_obj"]
        .paginator.count
        == 0
    )
    detail = client.get(reverse("asset_detail", args=[registry[3].pk]))
    assert detail.status_code == 200
    assert (
        b"PRIVATE-SERIAL" not in detail.content
        and b"PRIVATE-NOTE" not in detail.content
        and b"100,00" not in detail.content
    )
    assert client.get(reverse("asset_edit", args=[registry[3].pk])).status_code == 404
    assert client.get(reverse("asset_detail", args=[uuid4()])).status_code == 404


def test_ui_create_edit_and_location_change(staff, registry, client):
    client.force_login(staff)
    response = client.post(
        reverse("asset_create"),
        {
            "inventory_number": "UI-1",
            "name": "Neues Asset",
            "category": registry[2].pk,
            "location": registry[1].pk,
            "condition": "good",
            "lifecycle": "active",
            "revision": 0,
        },
    )
    assert response.status_code == 302, (
        response.context["form"].errors if response.status_code == 200 else response.content
    )
    asset = Asset.objects.get(inventory_number="UI-1")
    assert asset.identifiers.count() == 2
    assert client.get(response.url).status_code == 200
    response = client.post(
        reverse("asset_edit", args=[asset.pk]),
        {
            "name": "Umbenannt",
            "category": registry[2].pk,
            "condition": "worn",
            "lifecycle": "active",
            "revision": asset.revision,
        },
    )
    assert response.status_code == 302
    asset.refresh_from_db()
    assert asset.name == "Umbenannt" and asset.condition == "worn"
    response = client.post(
        reverse("asset_move", args=[asset.pk]),
        {"location": registry[0].pk, "reason": "UI-Umzug", "revision": asset.revision},
    )
    assert response.status_code == 302
    asset.refresh_from_db()
    assert asset.location_id == registry[0].pk
    assert (
        client.post(
            reverse("asset_archive", args=[asset.pk]),
            {"reason": "UI-Archiv", "revision": asset.revision},
        ).status_code
        == 302
    )
    assert client.get(reverse("asset_detail", args=[asset.pk])).status_code == 200


def test_lookup_manual_hid_enter_reset_and_scope(staff, registry, client):
    ns = IdentifierNamespace.objects.get(key="inventory")
    client.force_login(staff)
    assert b"autofocus" in client.get(reverse("identifier_lookup")).content
    for _ in range(3):
        response = client.post(
            reverse("identifier_lookup"),
            {"namespace": ns.pk, "code": registry[3].inventory_number + "\r\n"},
        )
        assert response.context["result"].status == "found"
        assert b"Gegenstand erkannt" in response.content
        assert response.context["form"].initial["namespace"] == str(ns.pk)
        assert not response.context[
            "form"
        ].is_bound  # next scanner input starts in an empty focused field.
        assert b"Details" in response.content
    assert (
        client.post(reverse("identifier_lookup"), {"namespace": ns.pk, "code": "unknown"})
        .context["result"]
        .status
        == "unknown"
    )
    assert (
        client.post(reverse("identifier_lookup"), {"namespace": ns.pk, "code": "<script>"})
        .context["result"]
        .status
        == "invalid"
    )
    assert (
        client.post(reverse("identifier_lookup"), {"namespace": ns.pk, "code": "x" * 1000})
        .context["form"]
        .errors
    )
    user = User.objects.create_user(
        "scanner@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name="Scanner")
    Membership.objects.create(user=user, group=group)
    Grant.objects.create(group=group, action="identifier.resolve", effect="allow")
    client.force_login(user)
    response = client.post(
        reverse("identifier_lookup"), {"namespace": ns.pk, "code": registry[3].inventory_number}
    )
    assert response.context["result"].status == "found" and b"Details" not in response.content
    assert client.get(reverse("asset_detail", args=[registry[3].pk])).status_code == 404


def test_inventory_csrf_and_unsafe_origin(staff, registry):
    client = Client(enforce_csrf_checks=True)
    client.force_login(staff)
    assert client.post(reverse("identifier_lookup"), {}).status_code == 403
    response = client.get(reverse("identifier_lookup"))
    assert response["Cache-Control"] == "no-store, private"
    csrf = client.cookies["csrftoken"].value
    ns = IdentifierNamespace.objects.get(key="inventory")
    data = {"namespace": ns.pk, "code": registry[3].inventory_number, "csrfmiddlewaretoken": csrf}
    assert (
        client.post(reverse("identifier_lookup"), data, HTTP_ORIGIN="http://testserver").status_code
        == 200
    )
    assert (
        client.post(
            reverse("identifier_lookup"), data, HTTP_ORIGIN="https://attacker.test"
        ).status_code
        == 403
    )
    assert client.get(reverse("media_archive", args=[uuid4()])).status_code == 405


def test_media_download_no_public_url_and_scope(staff, registry, client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    row = extensions.upload_media(staff, registry[3].pk, image_upload(), is_sensitive=False)
    client.force_login(staff)
    response = client.get(reverse("media_download", args=[row.pk]))
    assert response.status_code == 200 and response["Content-Type"] == "image/jpeg"
    assert response["Cache-Control"] == "no-store, private"
    assert b"".join(response.streaming_content).startswith(b"\xff\xd8")
    assert client.get("/media/" + row.storage_name).status_code == 404
    user = User.objects.create_user(
        "private-media@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    client.force_login(user)
    assert client.get(reverse("media_download", args=[row.pk])).status_code == 404


def test_tree_namespace_field_and_import_interfaces(staff, registry, client):
    client.force_login(staff)
    for name in (
        "locations",
        "categories",
        "inventory_namespaces",
        "inventory_fields",
        "inventory_tags",
        "csv_import",
    ):
        assert client.get(reverse(name)).status_code == 200
    assert (
        client.post(
            reverse("locations"), {"name": "UI-Ort", "is_active": "on", "revision": 0}
        ).status_code
        == 302
    )
    assert (
        client.post(
            reverse("inventory_namespaces"),
            {"key": "ui", "name": "UI-Codes", "normalization": "exact-v1"},
        ).status_code
        == 302
    )
    assert (
        client.post(
            reverse("inventory_fields"), {"key": "ui-field", "label": "UI-Feld", "kind": "text"}
        ).status_code
        == 302
    )
    response = client.post(reverse("csv_import"), {"file": csv_upload(registry)})
    assert response.status_code == 302
    assert client.get(response.url).status_code == 200
    assert client.post(response.url).status_code == 302
    assert Asset.objects.filter(inventory_number__in=["CSV-1", "CSV-2"]).count() == 2
    assert client.get(reverse("csv_export")).status_code == 200


def test_privilege_field_injection_does_not_overwrite_hidden_values(staff, registry, client):
    user, group = limited_user(registry[0], manage=True)
    Grant.objects.create(group=group, action="category.read", effect="allow")
    client.force_login(user)
    response = client.post(
        reverse("asset_edit", args=[registry[3].pk]),
        {
            "name": "Safe edit",
            "category": registry[2].pk,
            "condition": "good",
            "lifecycle": "active",
            "revision": registry[3].revision,
            "serial_number": "attacker",
            "acquisition_value": "1",
            "internal_notes": "attacker",
            "location": registry[0].pk,
        },
    )
    assert response.status_code == 302
    registry[3].refresh_from_db()
    assert (
        registry[3].serial_number == "PRIVATE-SERIAL"
        and registry[3].internal_notes == "PRIVATE-NOTE"
    )
    assert (
        str(registry[3].acquisition_value) == "100.00" and registry[3].location_id == registry[1].pk
    )


def test_preview_expires_without_exposing_rows_or_allowing_commit(staff, registry, client):
    from datetime import timedelta

    from inventory import csvio
    from inventory.models import ImportPreview

    preview = csvio.preview_import(staff, csv_upload(registry))
    ImportPreview.objects.filter(pk=preview.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    client.force_login(staff)
    for method in (client.get, client.post):
        response = method(reverse("csv_preview", args=[preview.pk]))
        assert response.status_code == 200 and b"abgelaufen" in response.content
        assert b"CSV-1" not in response.content and b"verbindlich" not in response.content
    assert not Asset.objects.filter(inventory_number="CSV-1").exists()


def test_preview_rechecks_current_rights_on_read(staff, registry, client):
    from inventory import csvio

    preview = csvio.preview_import(staff, csv_upload(registry))
    Grant.objects.filter(group__membership__user=staff, action="asset.manage").delete()
    client.force_login(staff)
    response = client.get(reverse("csv_preview", args=[preview.pk]))
    assert response.status_code == 404 and b"CSV-1" not in response.content


def test_grant_form_inventory_targets_are_read_scoped(staff, registry):
    from accounts.forms import GrantForm

    user, group = limited_user(registry[0])
    Grant.objects.create(
        group=group,
        action="location.read",
        effect="allow",
        scope_kind="location",
        scope_id=registry[0].pk,
        inherit=True,
    )
    hidden = services.save_tree(staff, Location, {"name": "Hidden", "is_active": True})
    data = {
        "action": "asset.read",
        "effect": "allow",
        "scope_kind": "location",
        "scope_location": registry[1].pk,
        "inherit": True,
    }
    form = GrantForm(data, actor=user)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["scope_id"] == registry[1].pk
    assert form.cleaned_data["inherit"] is True
    assert not GrantForm({**data, "scope_location": hidden.pk}, actor=user).is_valid()
    assert not GrantForm({**data, "scope_asset": registry[3].pk}, actor=user).is_valid()
    assert not GrantForm(data).is_valid()


def test_lookup_rate_limit_blocks_before_resolution(staff, registry, client):
    from accounts.models import RateBucket

    client.force_login(staff)
    ns = IdentifierNamespace.objects.get(key="inventory")
    url = reverse("identifier_lookup")
    data = {"namespace": ns.pk, "code": registry[3].inventory_number}
    assert client.post(url, data).status_code == 200
    RateBucket.objects.update(count=600)
    response = client.post(url, data)
    assert response.status_code == 429 and registry[3].name.encode() not in response.content
