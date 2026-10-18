import hashlib
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from accounts.limits import limited
from accounts.models import Grant, Membership, OIDCStateUse
from bookings import services as bookings
from bookings.models import Booking
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone
from integrations import services
from integrations.api import ROUTES
from integrations.models import IntegrationClient, IntegrationToken
from integrations.schema import contract
from inventory.models import AssetMovement, Location
from inventory.services import move_asset, save_asset, save_tree
from lending import services as lending
from lending.models import Loan
from test_bookings import configured as configured_fixture
from test_lending import lending_setup as lending_fixture
from test_lending import reserve

configured = configured_fixture
lending_setup = lending_fixture
pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


def manager(user):
    group = Membership.objects.get(user=user).group
    Grant.objects.get_or_create(group=group, action="integration.manage", effect="allow")
    return user


def access(user, caps, *, readonly=True, kind="organization", pk=None):
    manager(user)
    integration = services.create_client(user, "Synthetic adapter", caps, kind, pk)
    token, raw = services.issue(user, integration.pk, read_only=readonly)
    return integration, token, raw


def http(raw):
    return Client(HTTP_AUTHORIZATION="Bearer " + raw)


def post(client, path, data, **headers):
    return client.post(
        "/api/v1/" + path, json.dumps(data), content_type="application/json", **headers
    )


def period(c):
    return dict(
        resource_id=str(c[1].pk), start=c[5].isoformat() + "+02:00", end=c[6].isoformat() + "+02:00"
    )


def test_token_hash_rotation_and_irreversible_sql(staff):
    integration, token, raw = access(staff, ["inventory.read"])
    assert len(raw) == 47 and token.digest == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in str(token.__dict__)
    newer, replacement = services.rotate(staff, token.pk)
    assert newer.expires_at == token.expires_at and replacement != raw
    assert http(raw).get("/api/v1/assets/").status_code == 401
    assert http(replacement).get("/api/v1/assets/").status_code == 200
    for fn in [
        lambda: IntegrationToken.objects.filter(pk=newer.pk).update(read_only=False),
        lambda: IntegrationToken.objects.filter(pk=token.pk).update(revoked_at=None),
        lambda: IntegrationClient.objects.filter(pk=integration.pk).update(scope_id=uuid4()),
        lambda: IntegrationToken.objects.filter(pk=newer.pk).delete(),
    ]:
        with pytest.raises(IntegrityError), transaction.atomic():
            fn()


def test_no_session_fallback_and_private_machine_error(staff):
    client = Client()
    client.force_login(staff)
    response = client.get("/api/v1/assets/")
    assert response.status_code == 401
    assert response.json()["error"]["request_id"] == response["X-Request-ID"]
    assert response["Cache-Control"] == "no-store, private"
    assert response["Referrer-Policy"] == "no-referrer"
    assert "Bearer" in response["WWW-Authenticate"]


def test_readonly_and_retirement(staff, registry):
    integration, _, raw = access(staff, ["inventory.read", "inventory.move"])
    client = http(raw)
    assert client.get("/api/v1/assets/").json()["count"] == 1
    assert post(client, f"assets/{registry[3].pk}/move/", {}).status_code == 403
    services.retire(staff, integration.pk)
    assert client.get("/api/v1/assets/").status_code == 401
    with pytest.raises(IntegrityError), transaction.atomic():
        IntegrationClient.objects.filter(pk=integration.pk).update(retired_at=None)


def test_live_owner_revocation_and_suspension(staff, registry):
    _, _, raw = access(staff, ["inventory.read"])
    client = http(raw)
    group = Membership.objects.get(user=staff).group
    deny = Grant.objects.create(group=group, action="asset.read", effect="deny")
    assert client.get("/api/v1/assets/").json()["count"] == 0
    assert client.get(f"/api/v1/assets/{registry[3].pk}/").status_code == 404
    deny.delete()
    Grant.objects.filter(group=group, action="integration.manage").delete()
    assert client.get("/api/v1/assets/").status_code == 401
    manager(staff)
    staff.is_active = False
    staff.save()
    assert client.get("/api/v1/assets/").status_code == 401


def test_scope_before_count_and_private_projection(staff, registry):
    other = save_asset(
        staff,
        dict(inventory_number="out", name="Outside", location=registry[0], category=registry[2]),
    )
    _, _, raw = access(staff, ["inventory.read"], kind="asset", pk=registry[3].pk)
    client = http(raw)
    response = client.get("/api/v1/assets/?page_size=1")
    assert response.status_code == 200 and response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(registry[3].pk)
    assert client.get(f"/api/v1/assets/{other.pk}/").status_code == 404
    assert b"PRIVATE-" not in response.content and b"acquisition_value" not in response.content


@pytest.mark.parametrize("query", ["page_size=51", "page=0", "q=a&q=b", "private=true", "page=abc"])
def test_strict_filters(staff, query):
    _, _, raw = access(staff, ["inventory.read"])
    assert http(raw).get("/api/v1/assets/?" + query).status_code == 400


def test_move_preconditions_and_scope_rechecked_inside_service(staff, registry):
    _, _, raw = access(
        staff,
        ["inventory.read", "inventory.move"],
        readonly=False,
        kind="location",
        pk=registry[0].pk,
    )
    client = http(raw)
    path = f"assets/{registry[3].pk}/move/"
    data = dict(location_id=str(registry[0].pk), reason="Synthetic relocation")
    assert post(client, path, data).status_code == 428
    tag = client.get(f"/api/v1/assets/{registry[3].pk}/")["ETag"]
    assert post(client, path, data, HTTP_IF_MATCH=tag).status_code == 200
    assert post(client, path, data, HTTP_IF_MATCH=tag).status_code == 409
    assert AssetMovement.objects.count() == 1
    outside = save_tree(staff, Location, dict(name="Outside", is_active=True))
    _, ceiling = services.authenticate("Bearer " + raw)
    registry[3].refresh_from_db()
    with limited(ceiling), pytest.raises(PermissionDenied):
        move_asset(staff, registry[3].pk, outside.pk, "Denied", registry[3].revision)
    assert AssetMovement.objects.count() == 1


@pytest.mark.parametrize(
    "payload,status",
    [
        ("{}", 400),
        ('{"namespace_id":null,"code":NaN}', 400),
        ('{"code":"a","code":"b"}', 400),
        ("[]", 400),
        ('{"unknown":true}', 400),
        ("x" * 65537, 413),
    ],
)
def test_strict_json(staff, payload, status):
    _, _, raw = access(staff, ["identifiers.resolve"])
    assert (
        http(raw)
        .post("/api/v1/identifiers/resolve/", payload, content_type="application/json")
        .status_code
        == status
    )


def test_media_method_and_rate_limit(staff, monkeypatch):
    _, _, raw = access(staff, ["identifiers.resolve"])
    client = http(raw)
    assert client.post("/api/v1/identifiers/resolve/", {"code": "x"}).status_code == 415
    assert client.delete("/api/v1/assets/").status_code == 405
    monkeypatch.setattr("integrations.api.take", lambda *a, **k: False)
    result = post(client, "identifiers/resolve/", {})
    assert result.status_code == 429 and result["Retry-After"] == "900"


def test_csv_import_bound_to_client_and_native_retry(staff, registry):
    caps = ["inventory.read", "inventory.import", "inventory.export"]
    _, _, raw = access(staff, caps, readonly=False)
    _, _, other = access(staff, caps, readonly=False)
    client = http(raw)
    csv = (
        "inventory_number,name,location_id,category_id\n"
        f"api-new,API asset,{registry[0].pk},{registry[2].pk}\n"
    )
    created = post(client, "assets/imports/", {"csv": csv})
    assert created.status_code == 201, created.content
    pk = created.json()["id"]
    assert http(other).get(f"/api/v1/assets/imports/{pk}/").status_code == 404
    done = post(client, f"assets/imports/{pk}/commit/", {})
    assert done.status_code == 200, done.content
    assert post(client, f"assets/imports/{pk}/commit/", {}).json() == done.json()
    export = client.get("/api/v1/assets/export.csv")
    assert (
        export.status_code == 200
        and b"api-new" in export.content
        and b"PRIVATE-" not in export.content
    )
    assert post(client, "assets/imports/", {"csv": "serial_number\nprivate\n"}).status_code == 400


def test_readonly_availability_and_booking_native_idempotency(configured):
    user = configured[4]
    _, _, raw = access(
        user, ["availability.read", "bookings.create", "bookings.read"], readonly=False
    )
    client = http(raw)
    data = period(configured)
    assert post(client, "availability/", data).json()["code"] == "available"
    key = str(uuid4())
    first = post(client, "bookings/", data, HTTP_IDEMPOTENCY_KEY=key)
    assert first.status_code == 201, first.content
    assert post(client, "bookings/", data, HTTP_IDEMPOTENCY_KEY=key).json() == first.json()
    assert Booking.objects.count() == 1
    altered = data | {"end": (configured[6] + timedelta(hours=1)).isoformat() + "+02:00"}
    assert post(client, "bookings/", altered, HTTP_IDEMPOTENCY_KEY=key).status_code == 422
    _, _, readonly = access(user, ["availability.read", "bookings.create"])
    assert post(http(readonly), "availability/", data).status_code == 200
    assert (
        post(http(readonly), "bookings/", data, HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code
        == 403
    )


def test_api_cannot_read_own_booking_outside_scope(configured, registry):
    user = configured[4]
    booking = bookings.confirm(user, configured[1].pk, configured[5], configured[6], uuid4())
    # Own-object shortcuts remain subject to the integration ceiling.
    _, _, raw = access(user, ["bookings.read"], kind="organization")
    client, token, _ = access(user, ["bookings.read"])
    # A scope at an unrelated location is created by a staff owner; user cannot gain it by API.
    _, _, scoped = access(configured[0], ["bookings.read"], kind="asset", pk=registry[3].pk)
    assert http(scoped).get(f"/api/v1/bookings/{booking.pk}/").status_code == 404
    assert http(raw).get(f"/api/v1/bookings/{booking.pk}/").status_code == 200
    assert client.owner_id == user.pk and token.client_id == client.pk


def test_checkout_return_reuses_booking_and_identity_gate(lending_setup, monkeypatch):
    c = lending_setup
    actor, _, _, _, user, _, _, pickup, _, _ = c
    booking = reserve(c)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    _, _, raw = access(actor, ["loans.read", "loans.checkout", "loans.return"], readonly=False)
    client = http(raw)
    data = dict(
        borrower_id=str(user.pk),
        bookings=[dict(booking_id=str(booking.pk), condition="good", accessories_checked=True)],
    )
    key = str(uuid4())
    assert post(client, "loans/checkout/", data, HTTP_IDEMPOTENCY_KEY=key).status_code == 422
    assert not Loan.objects.exists()
    lending.identity_check(actor, user.pk)
    result = post(client, "loans/checkout/", data, HTTP_IDEMPOTENCY_KEY=key)
    assert result.status_code == 201, result.content
    assert post(client, "loans/checkout/", data, HTTP_IDEMPOTENCY_KEY=key).json() == result.json()
    assert Booking.objects.count() == 1 and Loan.objects.count() == 1
    line = result.json()["lines"][0]
    path = f"loans/{result.json()['id']}/return/"
    data = dict(
        lines=[
            dict(
                line_id=line["id"],
                revision=line["revision"] + 1,
                condition="good",
                accessories_checked=True,
            )
        ]
    )
    key = str(uuid4())
    assert post(client, path, data, HTTP_IDEMPOTENCY_KEY=key).status_code == 409
    data["lines"][0]["revision"] = line["revision"]
    returned = post(client, path, data, HTTP_IDEMPOTENCY_KEY=key)
    assert returned.status_code == 200, returned.content
    assert returned.json()["closed_at"]
    assert post(client, path, data, HTTP_IDEMPOTENCY_KEY=key).json() == returned.json()
    assert "borrower_id" not in result.json()


def test_openapi_registry_refs_and_public_contract(client):
    from pathlib import Path

    schema = contract()
    assert json.loads(Path("docs/api/deelvo-openapi-v1.json").read_text()) == schema
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200 and response.json() == schema
    assert sum(len(v) for v in schema["paths"].values()) == len(ROUTES)

    def walk(value):
        if isinstance(value, dict):
            if "$ref" in value:
                assert value["$ref"].split("/")[-1] in schema["components"]["schemas"]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
    assert all("(?P" not in path for path in schema["paths"])


def test_oidc_state_claim_is_once_only():
    from accounts.oidc import claim_flow

    flow = dict(state="synthetic-once", created=int(timezone.now().timestamp()))
    assert claim_flow(flow) and not claim_flow(flow)
    assert OIDCStateUse.objects.count() == 1


def test_nested_bundle_cannot_escape_resource_ceiling(configured):
    from resources import bundles
    from test_phase7 import component

    actor, resource, _, _, user, *_ = configured
    child = component(configured)
    bundles.configure(actor, resource.pk, [(child, True)], resource.revision)
    _, _, raw = access(user, ["bookings.create"], readonly=False, kind="resource", pk=resource.pk)
    result = post(http(raw), "bookings/", period(configured), HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert result.status_code == 422, result.content
    assert not Booking.objects.exists()


def test_own_shortcut_cannot_escape_resource_ceiling(configured):
    from test_phase7 import component

    c = configured
    child = component(c)
    booking = bookings.confirm(c[4], child.pk, c[5], c[6], uuid4())
    _, _, raw = access(c[4], ["bookings.read"], kind="resource", pk=c[1].pk)
    client = http(raw)
    assert client.get(f"/api/v1/bookings/{booking.pk}/").status_code == 404
    assert client.get("/api/v1/bookings/").json()["count"] == 0


def test_management_csrf_password_and_foreign_owner(staff, registry, client):
    _, token, _ = access(staff, ["inventory.read"])
    client.force_login(staff)
    response = client.get("/konto/integrationen/")
    assert response.status_code == 200 and b"Integrationszug" in response.content
    assert token.digest.encode() not in response.content
    assert (
        client.post(
            "/konto/integrationen/", dict(action="rotate", token_id=str(token.pk), password="wrong")
        ).status_code
        == 200
    )
    assert IntegrationToken.objects.count() == 1
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(staff)
    assert (
        strict.post(
            "/konto/integrationen/", dict(action="revoke", token_id=str(token.pk))
        ).status_code
        == 403
    )


def test_client_namespaces_idempotency_keys(configured):
    from django.test import RequestFactory
    from integrations.transport import key

    user = configured[4]
    first, _, _ = access(user, ["bookings.create"], readonly=False)
    second, _, _ = access(user, ["bookings.create"], readonly=False)
    request = RequestFactory().post("/", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert key(request, first) != key(request, second)


def test_oidc_parallel_callback_claim(transactional_db):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from accounts.oidc import claim_flow
    from django.db import close_old_connections

    barrier = Barrier(2)
    flow = dict(state="synthetic-race", created=int(timezone.now().timestamp()))

    def worker(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return claim_flow(flow)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert sorted(results) == [False, True]


def test_parallel_api_confirmation_allocates_once(configured, transactional_db):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    _, _, raw = access(configured[4], ["bookings.create"], readonly=False)
    data = period(configured)
    barrier = Barrier(2)

    def worker(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return post(http(raw), "bookings/", data, HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert sorted(results) == [201, 422]
    assert Booking.objects.count() == 1


def test_revoke_between_initial_check_and_write(configured, monkeypatch):
    user = configured[4]
    _, token, raw = access(user, ["bookings.create"], readonly=False)

    def revoke_before_lock(*args, **kwargs):
        services.revoke(user, token.pk)
        return True

    monkeypatch.setattr("integrations.api.take", revoke_before_lock)
    result = post(http(raw), "bookings/", period(configured), HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert result.status_code == 401 and not Booking.objects.exists()


def test_naive_time_rejected_and_audit_contains_only_ids(configured, caplog):
    from accounts.models import AuditEvent

    _, token, raw = access(configured[4], ["bookings.create"], readonly=False)
    client = http(raw)
    data = period(configured)
    invalid = data | {"start": configured[5].isoformat()}
    assert post(client, "bookings/", invalid, HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code == 400
    result = post(client, "bookings/", data, HTTP_IDEMPOTENCY_KEY=str(uuid4()))
    assert result.status_code == 201
    event = AuditEvent.objects.filter(action="booking.confirmed").last()
    assert event.details["api_token"] == str(token.pk)
    assert raw not in caplog.text and raw not in str(event.details)


def test_oidc_configuration_report_does_not_expose_secret(settings):
    from io import StringIO

    from django.core.management import call_command

    settings.OIDC_CLIENT_SECRET = "synthetic-never-output"
    out = StringIO()
    call_command("check_oidc_config", stdout=out)
    assert settings.OIDC_CLIENT_SECRET not in out.getvalue()
    assert json.loads(out.getvalue())["live_provider_verified"] is False


def test_oidc_nonce_type_and_critical_headers(settings):
    from unittest.mock import patch

    import jwt
    from accounts.oidc import validate_id_token
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    jwk.update(kid="test-key", use="sig", alg="RS256")
    now = int(timezone.now().timestamp())
    claims = dict(
        iss=settings.OIDC_ISSUER,
        aud=settings.OIDC_CLIENT_ID,
        sub="staff",
        exp=now + 300,
        iat=now,
        nonce=123,
    )
    for nonce, headers in [
        (123, {"kid": "test-key"}),
        ("123", {"kid": "test-key", "crit": ["unhandled"], "unhandled": True}),
    ]:
        token = jwt.encode(claims | {"nonce": nonce}, private, algorithm="RS256", headers=headers)
        with patch("accounts.oidc.fetch_json", return_value={"keys": [jwk]}):
            with pytest.raises((ValueError, jwt.PyJWTError)):
                validate_id_token(token, "123")
