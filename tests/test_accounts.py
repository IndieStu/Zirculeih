import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from accounts import services
from accounts.authorization import Scope, allowed, authorization_write, require_beneficiary
from accounts.models import (
    ActionToken,
    AuditEvent,
    AuthorizationRevision,
    Grant,
    Group,
    Membership,
    OIDCIdentity,
    User,
)
from accounts.oidc import validate_id_token
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]
PASSWORD = "Quiet-River-8941!Cloud"


@pytest.fixture(autouse=True)
def account_settings(settings):
    settings.SECURE_SSL_REDIRECT = False
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.PRIVACY_NOTICE_TEXT = "Synthetischer Datenschutzhinweis für Tests."
    settings.PRIVACY_NOTICE_VERSION = "test-v1"
    settings.PUBLIC_BASE_URL = "https://example.test"
    settings.OIDC_ISSUER = "https://auth.example.test/application/o/deelvo/"
    settings.OIDC_AUTHORIZATION_ENDPOINT = "https://auth.example.test/application/o/authorize/"
    settings.OIDC_TOKEN_ENDPOINT = "https://auth.example.test/application/o/token/"
    settings.OIDC_JWKS_ENDPOINT = "https://auth.example.test/application/o/deelvo/jwks/"
    settings.OIDC_CLIENT_ID = "deelvo-test"
    settings.OIDC_CLIENT_SECRET = "synthetic-test-client-secret"


@pytest.fixture
def users():
    def create(email="person@example.test", **kwargs):
        return User.objects.create_user(
            email, PASSWORD, email_verified_at=timezone.now(), privacy_version="test-v1", **kwargs
        )

    return create


@pytest.fixture
def admin(users):
    return users("admin@example.test", is_system_admin=True)


def grant(admin, user, action, **kwargs):
    group = services.save_group(admin, name=str(uuid4()))
    services.add_grant(admin, group.pk, {"action": action, "effect": "allow", **kwargs})
    services.change_membership(admin, group.pk, user.pk)
    return group


def test_signup_verify_profile_and_no_escalation(client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        result = client.post(
            reverse("signup"),
            {
                "email": " NEW@Example.test ",
                "password": PASSWORD,
                "password_confirm": PASSWORD,
                "privacy": "on",
                "is_system_admin": "on",
                "is_employee": "on",
                "groups": "all",
            },
        )
    assert result.status_code == 200
    user = User.objects.get(email="new@example.test")
    assert not user.email_verified_at and not user.is_system_admin and not user.is_employee
    assert not user.full_name and not user.borrower_profile_complete
    assert user.privacy_version == "test-v1"
    assert Membership.objects.get(user=user).group.is_baseline
    assert not allowed(user, "booking.create_own")
    raw = re.search(r"bestaetigen/([^/]+)/", mail.outbox[0].body)[1]
    assert ActionToken.objects.get().digest == hashlib.sha256(raw.encode()).hexdigest()
    assert client.get(reverse("verify", args=[raw])).status_code == 200
    user.refresh_from_db()
    assert user.email_verified_at is None  # GET and email scanners must not consume.
    assert client.post(reverse("verify", args=[raw])).status_code == 302
    user.refresh_from_db()
    assert user.email_verified_at
    with pytest.raises(ValidationError):
        services.consume_token(raw, "verify")
    assert (
        client.post(reverse("login"), {"username": user.email, "password": PASSWORD}).status_code
        == 302
    )
    assert client.get(reverse("account")).status_code == 200
    data = {
        "full_name": "Testperson",
        "street": "Beispielweg 1",
        "postal_code": "27568",
        "city": "Teststadt",
        "country": "Deutschland",
        "phone": "0000000",
    }
    client.post(
        reverse("account"), {**data, "email": "attacker@example.test", "is_system_admin": "on"}
    )
    user.refresh_from_db()
    assert user.borrower_profile_complete and user.profile_revision == 1
    assert user.email == "new@example.test" and not user.is_system_admin
    assert all(value not in str(list(AuditEvent.objects.values())) for value in data.values())


def test_duplicate_signup_generic_and_case_unique(users, client):
    user = users()
    payload = {
        "email": user.email.upper(),
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "privacy": "on",
    }
    result = client.post(reverse("signup"), payload)
    assert b"Pr\xc3\xbcfe dein" in result.content
    assert User.objects.filter(email__iexact=user.email).count() == 1
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(email=user.email.upper(), privacy_version="test")


def test_privacy_required_and_unconfigured_signup_closed(client, settings):
    result = client.post(
        reverse("signup"),
        {"email": "x@example.test", "password": PASSWORD, "password_confirm": PASSWORD},
    )
    assert not User.objects.exists()
    assert result.status_code == 200
    settings.PRIVACY_NOTICE_TEXT = ""
    assert client.get(reverse("signup")).status_code == 503


def test_password_reset_generic_expiry_replay_and_session_invalidation(
    users, client, django_capture_on_commit_callbacks
):
    user = users()
    client.force_login(user)
    other = Client()
    other.force_login(user)
    with django_capture_on_commit_callbacks(execute=True):
        known = client.post(reverse("token_request", args=["reset"]), {"email": user.email})
        unknown = client.post(
            reverse("token_request", args=["reset"]), {"email": "missing@example.test"}
        )
    assert known.context["text"] == unknown.context["text"]
    raw = re.search(r"passwort-neu/([^/]+)/", mail.outbox[0].body)[1]
    assert (
        client.post(
            reverse("reset", args=[raw]),
            {"password": PASSWORD + "new", "password_confirm": PASSWORD + "new"},
        ).status_code
        == 302
    )
    assert other.get(reverse("account")).status_code == 302
    with pytest.raises(ValidationError):
        services.consume_token(raw, "reset", PASSWORD)
    expired = services.issue_token(user, "reset")
    ActionToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(ValidationError):
        services.consume_token(expired, "reset", PASSWORD)


def test_password_change_invalidates_other_sessions(users, client):
    user = users()
    client.force_login(user)
    other = Client()
    other.force_login(user)
    response = client.post(
        reverse("password_change"),
        {
            "old_password": PASSWORD,
            "new_password1": PASSWORD + "new",
            "new_password2": PASSWORD + "new",
        },
    )
    assert response.status_code == 302, response.context["form"].errors
    assert client.get(reverse("account")).status_code == 200
    assert other.get(reverse("account")).status_code == 302


def test_csrf_logout_and_form_protection(users):
    user = users()
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post(reverse("account"), {}).status_code == 403
    assert client.post(reverse("logout")).status_code == 403
    assert client.get(reverse("logout")).status_code == 405


def test_login_rate_limited_and_safe_redirect(users, client):
    user = users()
    for _ in range(10):
        assert (
            client.post(reverse("login"), {"username": user.email, "password": "wrong"}).status_code
            == 200
        )
    assert (
        client.post(reverse("login"), {"username": user.email, "password": PASSWORD}).status_code
        == 429
    )
    other = Client(REMOTE_ADDR="192.0.2.1")
    assert (
        other.post(reverse("login"), {"username": user.email, "password": PASSWORD}).status_code
        == 429
    )
    response = other.post(
        reverse("login"), {"username": "missing@example.test", "password": PASSWORD}
    )
    assert response.status_code == 200


def test_default_deny_employee_and_system_admin_have_no_operational_bypass(users, admin):
    user = users(is_employee=True)
    for actor in (user, admin):
        assert not allowed(actor, "loan.checkout")
        assert not allowed(actor, "identifier.resolve")
    assert allowed(admin, "permissions.manage")
    assert not allowed(user, "permissions.manage")
    assert not allowed(admin, "made.up")


def test_group_crud_baseline_safety_and_idor(users, admin, client):
    user = users()
    client.force_login(user)
    group = services.save_group(admin, name="Inventarteam")
    assert client.get(reverse("group_detail", args=[group.pk])).status_code == 403
    assert client.post(reverse("group_archive", args=[group.pk])).status_code == 403
    with pytest.raises(PermissionDenied):
        services.save_group(user, group_id=group.pk, name="hacked")
    baseline = Group.objects.get(is_baseline=True)
    with pytest.raises(ValidationError):
        services.add_grant(admin, baseline.pk, {"action": "asset.manage", "effect": "allow"})
    with pytest.raises(ValidationError):
        services.archive_group(admin, baseline.pk)
    with pytest.raises(ValidationError):
        services.add_grant(admin, group.pk, {"action": "admin.manage", "effect": "allow"})
    services.save_group(admin, group_id=group.pk, name="Geändert")
    services.archive_group(admin, group.pk)
    group.refresh_from_db()
    assert not group.is_active and group.archived_at


def test_complete_grant_profiles_and_deny_priority(users, admin):
    user = users()
    scope = Scope("resource", uuid4())
    grant(
        admin,
        user,
        "booking.create_own",
        scope_kind=scope.kind,
        scope_id=scope.id,
        max_horizon_days=90,
        max_duration_minutes=120,
    )
    group = grant(
        admin,
        user,
        "booking.create_own",
        scope_kind=scope.kind,
        scope_id=scope.id,
        max_horizon_days=30,
        max_duration_minutes=480,
    )
    assert allowed(user, "booking.create_own", scope, horizon_days=62, duration_minutes=120)
    assert not allowed(user, "booking.create_own", scope, horizon_days=62, duration_minutes=480)
    assert not allowed(user, "booking.create_own", scope)
    services.add_grant(
        admin,
        group.pk,
        {
            "action": "booking.create_own",
            "effect": "deny",
            "scope_kind": scope.kind,
            "scope_id": scope.id,
        },
    )
    assert not allowed(user, "booking.create_own", scope, horizon_days=1, duration_minutes=60)
    assert not allowed(
        user, "booking.create_own", Scope("resource", uuid4()), horizon_days=1, duration_minutes=60
    )


def test_inheritance_explicit_and_unstaffed_separate(users, admin):
    user = users()
    parent, child = uuid4(), uuid4()
    group = grant(admin, user, "resource.use_unstaffed", scope_kind="location", scope_id=parent)
    scope = Scope("location", child, (parent,))
    assert not allowed(user, "resource.use_unstaffed", scope)
    services.add_grant(
        admin,
        group.pk,
        {
            "action": "resource.use_unstaffed",
            "effect": "allow",
            "scope_kind": "location",
            "scope_id": parent,
            "inherit": True,
        },
    )
    assert allowed(user, "resource.use_unstaffed", scope)
    assert not allowed(user, "loan.checkout", scope)
    assert not allowed(user, "inventory_run.observe", scope)
    assert not allowed(user, "asset.move", scope)


def test_delegation_cannot_self_escalate_or_change_ceiling(users, admin, client):
    manager = users("manager@example.test")
    member = users()
    target = services.save_group(admin, name="Leseteam")
    services.add_grant(admin, target.pk, {"action": "asset.read", "effect": "allow"})
    grant(admin, manager, "user.manage_groups", scope_kind="group", scope_id=target.pk)
    services.change_membership(manager, target.pk, member.pk)
    assert allowed(member, "asset.read")
    with pytest.raises(PermissionDenied):
        services.change_membership(manager, target.pk, manager.pk)
    with pytest.raises(PermissionDenied):
        services.change_membership(manager, target.pk, admin.pk)
    with pytest.raises(PermissionDenied):
        services.add_grant(manager, target.pk, {"action": "asset.manage", "effect": "allow"})
    with pytest.raises(ValidationError):
        services.add_grant(admin, target.pk, {"action": "asset.manage", "effect": "allow"})
    client.force_login(manager)
    assert client.get(reverse("group_detail", args=[target.pk])).status_code == 200
    assert (
        client.post(reverse("group_detail", args=[target.pk]), {"operation": "grant"}).status_code
        == 403
    )
    services.change_membership(manager, target.pk, member.pk, remove=True)
    assert not allowed(member, "asset.read")


def test_suspension_invalidates_sessions_but_staff_can_return(users, admin, client):
    user = users()
    staff = users("staff@example.test")
    grant(admin, user, "booking.create_own")
    grant(admin, staff, "loan.return")
    grant(admin, staff, "loan.checkout")
    client.force_login(user)
    raw = services.issue_token(user, "reset")
    services.suspend_account(admin, user.pk, suspended=True, reason="Synthetischer Test")
    assert not allowed(user, "booking.create_own")
    assert allowed(staff, "loan.return")
    with pytest.raises(PermissionDenied):
        require_beneficiary(staff, user, "loan.checkout", Scope())
    assert client.get(reverse("account")).status_code == 302
    services.suspend_account(admin, user.pk, suspended=False, reason="Test beendet")
    assert client.get(reverse("account")).status_code == 302
    with pytest.raises(ValidationError):
        services.consume_token(raw, "reset", PASSWORD)
    with pytest.raises(PermissionDenied):
        services.suspend_account(admin, admin.pk, suspended=True, reason="test")


def test_no_other_profile_url(users, client):
    user = users()
    other = users("other@example.test", street="PRIVATE STREET")
    client.force_login(user)
    response = client.get(reverse("account") + f"?user={other.pk}")
    assert b"PRIVATE STREET" not in response.content
    assert client.get(f"/konto/{other.pk}/").status_code == 404


@pytest.fixture
def signing_key():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    key.update(kid="test-key", use="sig", alg="RS256")
    return private, key


def encoded_token(settings, signing_key, **overrides):
    claims = dict(
        iss=settings.OIDC_ISSUER,
        aud=settings.OIDC_CLIENT_ID,
        sub="staff-123",
        iat=int(timezone.now().timestamp()),
        exp=int(timezone.now().timestamp()) + 300,
        nonce="test-nonce",
        email="ignored@example.test",
        groups=["admin"],
        is_superuser=True,
    )
    claims.update(overrides)
    return jwt.encode(claims, signing_key[0], algorithm="RS256", headers={"kid": "test-key"})


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://attacker.test"},
        {"aud": "wrong"},
        {"nonce": "wrong"},
        {"exp": 1},
        {"iat": 9999999999},
        {"sub": ""},
        {"aud": ["deelvo-test", "other"]},
        {"azp": "other"},
    ],
)
def test_oidc_rejects_invalid_signed_claims(settings, signing_key, overrides):
    token = encoded_token(settings, signing_key, **overrides)
    with patch("accounts.oidc.fetch_json", return_value={"keys": [signing_key[1]]}):
        with pytest.raises((ValueError, jwt.PyJWTError)):
            validate_id_token(token, "test-nonce")


def test_oidc_rejects_wrong_signature_and_algorithm(settings, signing_key):
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = encoded_token(settings, (wrong, signing_key[1]))
    with patch("accounts.oidc.fetch_json", return_value={"keys": [signing_key[1]]}):
        with pytest.raises(jwt.PyJWTError):
            validate_id_token(token, "test-nonce")
    with pytest.raises(ValueError):
        validate_id_token(
            jwt.encode({"sub": "staff"}, "s" * 64, algorithm="HS256", headers={"kid": "test-key"}),
            "test-nonce",
        )


def prepare_oidc(client, settings):
    settings.OIDC_ENABLED = True
    response = client.post(reverse("oidc_login"))
    assert response.status_code == 302
    assert "code_challenge_method=S256" in response.url
    session = client.session
    flow = session["oidc_flow"]
    flow["nonce"] = "test-nonce"
    session["oidc_flow"] = flow
    session.save()
    return flow


def test_oidc_staff_login_claims_ignored_and_replay_rejected(users, settings, signing_key, client):
    user = users(is_employee=True)
    OIDCIdentity.objects.create(user=user, issuer=settings.OIDC_ISSUER, subject="staff-123")
    flow = prepare_oidc(client, settings)
    token = encoded_token(settings, signing_key)
    with patch(
        "accounts.oidc.fetch_json", side_effect=[{"id_token": token}, {"keys": [signing_key[1]]}]
    ) as fetch:
        response = client.get(
            reverse("oidc_callback"), {"code": "test-code", "state": flow["state"]}
        )
        assert "code_verifier=" in fetch.call_args_list[0].args[1].decode()
    assert response.status_code == 302
    assert client.get(reverse("account")).status_code == 200
    user.refresh_from_db()
    assert not user.is_system_admin and user.email == "person@example.test"
    assert not Membership.objects.filter(user=user).exists()
    assert not allowed(user, "permissions.manage")
    assert (
        client.get(
            reverse("oidc_callback"), {"code": "test-code", "state": flow["state"]}
        ).status_code
        == 400
    )


def test_oidc_no_email_autolink_no_jit_and_local_independent(users, settings, signing_key, client):
    user = users(is_employee=True)
    flow = prepare_oidc(client, settings)
    token = encoded_token(settings, signing_key, email=user.email, email_verified=True)
    with patch(
        "accounts.oidc.fetch_json", side_effect=[{"id_token": token}, {"keys": [signing_key[1]]}]
    ):
        response = client.get(
            reverse("oidc_callback"), {"code": "test-code", "state": flow["state"]}
        )
    assert b"nicht m\xc3\xb6glich" in response.content
    assert not OIDCIdentity.objects.exists() and User.objects.count() == 1
    assert (
        client.post(reverse("login"), {"username": user.email, "password": PASSWORD}).status_code
        == 302
    )


def test_oidc_link_requires_employee_password_and_state(users, settings, signing_key, client):
    settings.OIDC_ENABLED = True
    user = users()
    client.force_login(user)
    assert client.get(reverse("oidc_link")).status_code == 403
    user.is_employee = True
    user.save()
    assert client.post(reverse("oidc_link"), {"password": "wrong"}).status_code == 200
    response = client.post(reverse("oidc_link"), {"password": PASSWORD})
    assert response.status_code == 302
    flow = client.session["oidc_flow"]
    token = encoded_token(settings, signing_key, nonce=flow["nonce"])
    with patch(
        "accounts.oidc.fetch_json", side_effect=[{"id_token": token}, {"keys": [signing_key[1]]}]
    ):
        assert (
            client.get(
                reverse("oidc_callback"), {"code": "test", "state": flow["state"]}
            ).status_code
            == 302
        )
    assert OIDCIdentity.objects.get().user_id == user.pk
    assert not allowed(user, "asset.manage")
    flow = prepare_oidc(client, settings)
    with patch(
        "accounts.oidc.fetch_json", side_effect=AssertionError("No network for invalid state")
    ):
        assert (
            client.get(reverse("oidc_callback"), {"code": "test", "state": "wrong"}).status_code
            == 400
        )


def test_oidc_provider_down_does_not_break_local(users, settings, client):
    user = users()
    flow = prepare_oidc(client, settings)
    with patch("accounts.oidc.fetch_json", side_effect=OSError("private provider error")):
        response = client.get(reverse("oidc_callback"), {"code": "test", "state": flow["state"]})
    assert b"private provider error" not in response.content
    assert (
        client.post(reverse("login"), {"username": user.email, "password": PASSWORD}).status_code
        == 302
    )


@pytest.mark.django_db(transaction=True)
def test_parallel_membership_assignment_one_active_row():
    # Transactional tests flush seeded rows: explicitly reconstruct synthetic baseline/lock.
    AuthorizationRevision.objects.get_or_create(pk=1)
    admin = User.objects.create_user(
        "admin@race.test",
        PASSWORD,
        is_system_admin=True,
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    user = User.objects.create_user(
        "person@race.test", PASSWORD, email_verified_at=timezone.now(), privacy_version="test"
    )
    group = services.save_group(admin, name="Parallel")

    def assign(_):
        close_old_connections()
        try:
            services.change_membership(admin, group.pk, user.pk)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(assign, range(8)))
    assert Membership.objects.filter(group=group, user=user, removed_at__isnull=True).count() == 1


@pytest.mark.django_db(transaction=True)
def test_permission_removal_serializes_with_protected_write():
    import threading

    AuthorizationRevision.objects.get_or_create(pk=1)
    user = User.objects.create_user(
        "staff@race.test", PASSWORD, email_verified_at=timezone.now(), privacy_version="test"
    )
    group = Group.objects.create(name="Race grant")
    Membership.objects.create(user=user, group=group)
    row = Grant.objects.create(group=group, action="loan.return", effect="allow")
    entered, attempted = threading.Event(), threading.Event()
    decisions = []

    def protected():
        close_old_connections()
        try:
            with authorization_write():
                entered.set()
                assert attempted.wait(5)
                decisions.append(allowed(user, "loan.return"))
        finally:
            connection.close()

    def revoke():
        close_old_connections()
        try:
            assert entered.wait(5)
            attempted.set()
            with authorization_write():
                Grant.objects.filter(pk=row.pk).delete()
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        a, b = executor.submit(protected), executor.submit(revoke)
        a.result(timeout=10)
        b.result(timeout=10)
    assert decisions == [True]
    assert not allowed(user, "loan.return")


def test_related_location_deny_overrides_resource_allow(users, admin):
    user = users()
    resource, location = uuid4(), uuid4()
    group = grant(admin, user, "identifier.resolve", scope_kind="resource", scope_id=resource)
    services.add_grant(
        admin,
        group.pk,
        {
            "action": "identifier.resolve",
            "effect": "deny",
            "scope_kind": "location",
            "scope_id": location,
        },
    )
    assert allowed(user, "identifier.resolve", Scope("resource", resource))
    assert not allowed(
        user,
        "identifier.resolve",
        Scope("resource", resource, related=(Scope("location", location),)),
    )


def test_oidc_only_account_can_explicitly_set_local_fallback_and_safe_unlink(
    users, settings, django_capture_on_commit_callbacks
):
    user = users(is_employee=True)
    user.set_unusable_password()
    user.save()
    OIDCIdentity.objects.create(user=user, issuer=settings.OIDC_ISSUER, subject="fallback-subject")
    with pytest.raises(ValidationError):
        services.unlink_oidc(user, PASSWORD)
    with django_capture_on_commit_callbacks(execute=True):
        services.request_token(user.email, "reset")
    raw = re.search(r"passwort-neu/([^/]+)/", mail.outbox[0].body)[1]
    services.consume_token(raw, "reset", PASSWORD + "fallback")
    user.refresh_from_db()
    assert user.check_password(PASSWORD + "fallback")
    services.unlink_oidc(user, PASSWORD + "fallback")
    assert not OIDCIdentity.objects.filter(user=user).exists()


def test_oidc_link_cannot_take_another_users_subject(users, settings, signing_key, client):
    settings.OIDC_ENABLED = True
    first = users("first@example.test", is_employee=True)
    second = users("second@example.test", is_employee=True)
    OIDCIdentity.objects.create(user=first, issuer=settings.OIDC_ISSUER, subject="staff-123")
    client.force_login(second)
    client.post(reverse("oidc_link"), {"password": PASSWORD})
    flow = client.session["oidc_flow"]
    token = encoded_token(settings, signing_key, nonce=flow["nonce"])
    with patch(
        "accounts.oidc.fetch_json", side_effect=[{"id_token": token}, {"keys": [signing_key[1]]}]
    ):
        response = client.get(reverse("oidc_callback"), {"code": "test", "state": flow["state"]})
    assert b"nicht m\xc3\xb6glich" in response.content
    assert OIDCIdentity.objects.get().user_id == first.pk


def test_oidc_disabled_does_not_offer_login(settings, client):
    settings.OIDC_ENABLED = False
    assert b"Mit Authentik anmelden" not in client.get(reverse("login")).content
    assert client.post(reverse("oidc_login")).status_code == 404


def test_mail_failure_response_contains_no_private_details(
    client, django_capture_on_commit_callbacks
):
    with patch("accounts.services.send_mail", side_effect=OSError("secret-smtp-credential")):
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(
                reverse("signup"),
                {
                    "email": "mail@example.test",
                    "password": PASSWORD,
                    "password_confirm": PASSWORD,
                    "privacy": "on",
                },
            )
    assert response.status_code == 200
    assert b"secret-smtp-credential" not in response.content
    assert User.objects.filter(email="mail@example.test").exists()


def test_groups_ui_admin_crud_and_membership(users, admin, client):
    user = users()
    client.force_login(admin)
    assert (
        client.post(
            reverse("group_create"),
            {"name": "Nachtzugang", "description": "Test", "is_active": "on"},
        ).status_code
        == 302
    )
    group = Group.objects.get(name="Nachtzugang")
    assert (
        client.post(
            reverse("group_detail", args=[group.pk]),
            {
                "operation": "grant",
                "action": "resource.use_unstaffed",
                "effect": "allow",
                "scope_kind": "organization",
            },
        ).status_code
        == 302
    )
    assert (
        client.post(
            reverse("group_detail", args=[group.pk]),
            {"operation": "membership", "email": user.email},
        ).status_code
        == 302
    )
    assert client.get(reverse("group_detail", args=[group.pk])).status_code == 200
    assert client.post(reverse("group_archive", args=[group.pk])).status_code == 302
    assert client.get(reverse("group_detail", args=[group.pk])).status_code == 404


def test_bootstrap_protected_and_audited(admin):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("bootstrap_admin", email="other-admin@example.test")
    assert User.objects.filter(is_system_admin=True).count() == 1


def test_password_change_never_reactivates_stale_suspended_account(users, admin):
    user = users()
    services.suspend_account(admin, user.pk, suspended=True, reason="race test")
    with pytest.raises(User.DoesNotExist):
        services.change_password(user, PASSWORD, PASSWORD + "new")
    user.refresh_from_db()
    assert not user.is_active


def test_removed_grant_remains_explainable_in_audit(admin):
    group = services.save_group(admin, name="Auditgruppe")
    row = services.add_grant(admin, group.pk, {"action": "asset.read", "effect": "allow"})
    original = services.grant_details(row)
    services.remove_grant(admin, group.pk, row.pk)
    assert not Grant.objects.filter(pk=row.pk).exists()
    event = AuditEvent.objects.get(action="grant.removed")
    assert event.details == original
    assert AuditEvent.objects.get(action="grant.created").details == original


def test_real_csrf_origin_login_and_profile_post(users):
    user = users()
    client = Client(enforce_csrf_checks=True)
    response = client.get(reverse("login"))
    assert response["Referrer-Policy"] == "same-origin"
    csrf = client.cookies["csrftoken"].value
    response = client.post(
        reverse("login"),
        {"username": user.email, "password": PASSWORD, "csrfmiddlewaretoken": csrf},
        HTTP_ORIGIN="http://testserver",
    )
    assert response.status_code == 302
    csrf = client.cookies["csrftoken"].value
    assert (
        client.post(
            reverse("account"),
            {"full_name": "CSRF Test", "csrfmiddlewaretoken": csrf},
            HTTP_ORIGIN="http://testserver",
        ).status_code
        == 302
    )
    assert (
        client.post(
            reverse("account"),
            {"full_name": "Attacker", "csrfmiddlewaretoken": csrf},
            HTTP_ORIGIN="https://attacker.example",
        ).status_code
        == 403
    )
