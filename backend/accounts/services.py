import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .authorization import (
    ACTIONS,
    BASELINE_ACTIONS,
    SCOPE_KINDS,
    SYSTEM_ACTIONS,
    Scope,
    authorization_write,
    bump,
    require,
)
from .models import ActionToken, AuditEvent, Grant, Group, Membership, User


def audit(actor, action, *, subject=None, object_id="", reason="", details=None):
    AuditEvent.objects.create(
        actor=actor,
        subject=subject,
        action=action,
        object_id=str(object_id),
        reason=reason,
        details=details or {},
    )


def issue_token(user, purpose):
    raw = secrets.token_urlsafe(32)
    ActionToken.objects.filter(user=user, purpose=purpose).delete()
    ActionToken.objects.create(
        digest=hashlib.sha256(raw.encode()).hexdigest(),
        user=user,
        purpose=purpose,
        password_hash=user.password,
        expires_at=timezone.now() + timedelta(hours=24 if purpose == "verify" else 1),
    )
    return raw


def email_token(user, purpose, raw):
    path = "bestaetigen" if purpose == "verify" else "passwort-neu"
    url = f"{settings.PUBLIC_BASE_URL}/konto/{path}/{raw}/"
    subject = "E-Mail bestätigen" if purpose == "verify" else "Passwort zurücksetzen"
    # Tokens are never logged; SMTP errors leave the generic response unchanged.
    try:
        send_mail(
            subject,
            f"{subject}:\n{url}\n\nFalls du dies nicht angefordert hast, ignoriere diese E-Mail.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
    except Exception:
        # No exception text: SMTP responses can contain addresses or credentials.
        import logging

        logging.getLogger("deelvo.mail").warning(
            "mail_delivery_failed", extra={"event": "mail_delivery_failed"}
        )


def signup(email, password, privacy_acknowledged):
    if not settings.PRIVACY_NOTICE_TEXT or not privacy_acknowledged:
        raise ValidationError("Bitte lies und bestätige die Datenschutzhinweise.")
    email = email.strip().lower()
    validate_email(email)
    candidate = User(
        email=email,
        privacy_version=settings.PRIVACY_NOTICE_VERSION,
        privacy_acknowledged_at=timezone.now(),
    )
    validate_password(password, candidate)
    candidate.set_password(password)  # Also hash for existing email: generic response.
    candidate.full_clean(exclude=["email"], validate_unique=False, validate_constraints=False)
    with authorization_write():
        if User.objects.filter(email__iexact=email).exists():
            return
        candidate.save()
        baseline = Group.objects.get(is_baseline=True)
        Membership.objects.create(user=candidate, group=baseline)
        raw = issue_token(candidate, "verify")
        audit(None, "account.signup", subject=candidate)
        transaction.on_commit(lambda: email_token(candidate, "verify", raw))


def request_token(email, purpose):
    with authorization_write():
        user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
        if user is None or (purpose == "verify" and user.email_verified_at):
            return
        raw = issue_token(user, purpose)
        transaction.on_commit(lambda: email_token(user, purpose, raw))


def consume_token(raw, purpose, password=None):
    with authorization_write() as revision:
        token = (
            ActionToken.objects.filter(
                digest=hashlib.sha256(raw.encode()).hexdigest(),
                purpose=purpose,
                expires_at__gt=timezone.now(),
                user__is_active=True,
            )
            .select_related("user")
            .first()
        )
        if token is None or token.password_hash != token.user.password:
            raise ValidationError(
                "Der Link ist ungültig oder abgelaufen. Bitte fordere einen neuen an."
            )
        user = token.user
        if purpose == "verify":
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
            ActionToken.objects.filter(user=user, purpose=purpose).delete()
        else:
            validate_password(password, user)
            user.set_password(password)
            user.session_revision += 1
            user.save(update_fields=["password", "session_revision"])
            ActionToken.objects.filter(user=user).delete()
        audit(user, f"account.{purpose}", subject=user)
        bump(revision)


def save_profile(actor, data):
    with authorization_write():
        user = User.objects.get(pk=actor.pk, is_active=True)
        for field in ("full_name", "street", "postal_code", "city", "country", "phone"):
            setattr(user, field, data[field].strip())
        user.profile_revision += 1
        user.full_clean()
        user.save()
        audit(user, "account.profile_updated", subject=user)
        return user


def save_group(actor, *, group_id=None, name, description="", is_active=True):
    with authorization_write() as revision:
        require(actor, "permissions.manage")
        group = Group.objects.get(pk=group_id) if group_id else Group()
        if group.archived_at or (group.is_baseline and not is_active):
            raise ValidationError(
                "Die Basisgruppe muss aktiv bleiben; archivierte Gruppen sind unveränderlich."
            )
        group.name, group.description, group.is_active = name, description, is_active
        group.full_clean()
        group.save()
        audit(actor, "group.saved", object_id=group.pk)
        bump(revision)
        return group


def archive_group(actor, group_id):
    with authorization_write() as revision:
        require(actor, "permissions.manage")
        group = Group.objects.get(pk=group_id)
        if group.is_baseline:
            raise ValidationError("Die Basisgruppe kann nicht archiviert werden.")
        group.archived_at, group.is_active = timezone.now(), False
        group.save()
        Membership.objects.filter(group=group, removed_at__isnull=True).update(
            removed_at=timezone.now()
        )
        audit(actor, "group.archived", object_id=group.pk)
        bump(revision)


def validate_grant(group, data):
    action = data["action"]
    kind, scope_id = data.get("scope_kind", "organization"), data.get("scope_id")
    if action not in ACTIONS or action in SYSTEM_ACTIONS or kind not in SCOPE_KINDS:
        raise ValidationError("Unzulässige Aktion oder Geltungsbereich.")
    if (kind == "organization") != (scope_id is None):
        raise ValidationError("Dieser Geltungsbereich benötigt genau eine Objekt-ID.")
    if action != "user.manage_groups" and kind == "group":
        raise ValidationError("Gruppenscope gilt nur für die Mitgliedschaftsverwaltung.")
    if action != "account.suspend" and kind == "user":
        raise ValidationError("Kontoscope gilt nur für die Kontosperre.")
    if action == "account.suspend" and kind not in {"organization", "user"}:
        raise ValidationError("Kontosperren benötigen Organisations- oder Kontoscope.")
    if action in {"identifier.namespace_manage", "custom_field.manage"} and kind != "organization":
        raise ValidationError("Diese Konfiguration benötigt Organisationsscope.")
    if data.get("inherit") and kind not in {"location", "category"}:
        raise ValidationError("Vererbung ist nur für Orte und Kategorien vorgesehen.")
    if group.is_baseline and (
        action not in BASELINE_ACTIONS or kind != "organization" or data["effect"] != "allow"
    ):
        raise ValidationError("Die Basisgruppe darf nur sichere eigene Aktionen erlauben.")
    if action == "user.manage_groups":
        if (
            kind != "group"
            or not Group.objects.filter(
                pk=scope_id, is_baseline=False, archived_at__isnull=True
            ).exists()
        ):
            raise ValidationError(
                "Delegation benötigt eine konkrete, nicht privilegierte Zielgruppe."
            )
        # Membership managers may not confer management, suspension or system authority.
        if (
            Grant.objects.filter(group_id=scope_id)
            .exclude(
                action__in=BASELINE_ACTIONS
                | {"asset.read", "identifier.resolve", "resource.use_unstaffed"}
            )
            .exists()
        ):
            raise ValidationError("Diese Zielgruppe überschreitet die Delegationsobergrenze.")
    # Do not later escalate an already delegated target group.
    if Grant.objects.filter(
        action="user.manage_groups", scope_kind="group", scope_id=group.pk
    ).exists():
        if action not in BASELINE_ACTIONS | {
            "asset.read",
            "identifier.resolve",
            "resource.use_unstaffed",
        }:
            raise ValidationError("Delegierte Gruppen dürfen keine Verwaltungsrechte erhalten.")


def add_grant(actor, group_id, data):
    with authorization_write() as revision:
        require(actor, "permissions.manage")
        group = Group.objects.get(pk=group_id, archived_at__isnull=True)
        validate_grant(group, data)
        grant = Grant(group=group, **data)
        grant.full_clean()
        grant.save()
        audit(actor, "grant.created", object_id=grant.pk, details=grant_details(grant))
        bump(revision)
        return grant


def remove_grant(actor, group_id, grant_id):
    with authorization_write() as revision:
        require(actor, "permissions.manage")
        grant = Grant.objects.get(pk=grant_id, group_id=group_id)
        audit(actor, "grant.removed", object_id=grant.pk, details=grant_details(grant))
        grant.delete()
        bump(revision)


def change_membership(actor, group_id, user_id, *, remove=False):
    with authorization_write() as revision:
        group = Group.objects.get(pk=group_id, is_active=True, archived_at__isnull=True)
        user = User.objects.get(pk=user_id)
        admin = User.objects.get(pk=actor.pk).is_system_admin
        if admin:
            require(actor, "permissions.manage")
        else:
            require(actor, "user.manage_groups", Scope("group", group.pk))
            if user.pk == actor.pk or user.is_system_admin or group.is_baseline:
                raise PermissionDenied(
                    "Eigene oder geschützte Mitgliedschaften sind nicht delegierbar."
                )
            # Revalidate the target group's ceiling at write time as defense in depth.
            validate_grant(
                Group(is_baseline=False),
                {
                    "action": "user.manage_groups",
                    "scope_kind": "group",
                    "scope_id": group.pk,
                    "effect": "allow",
                },
            )
        membership = Membership.objects.filter(
            user=user, group=group, removed_at__isnull=True
        ).first()
        if remove and membership:
            membership.removed_at = timezone.now()
            membership.save(update_fields=["removed_at"])
        elif not remove and not membership:
            Membership.objects.create(user=user, group=group, assigned_by=actor)
        audit(
            actor,
            "membership.removed" if remove else "membership.assigned",
            subject=user,
            object_id=group.pk,
        )
        bump(revision)


def suspend_account(actor, user_id, *, suspended, reason):
    with authorization_write() as revision:
        user = User.objects.get(pk=user_id)
        if not reason.strip():
            raise ValidationError("Bitte gib einen Grund an.")
        if user.pk == actor.pk or user.is_system_admin:
            raise PermissionDenied(
                "Geschützte Administratorkonten werden nur über den Recovery-Befehl verwaltet."
            )
        if User.objects.get(pk=actor.pk).is_system_admin:
            require(actor, "admin.manage")
        else:
            require(actor, "account.suspend", Scope("user", user.pk))
        user.is_active = not suspended
        user.session_revision += 1
        user.save(update_fields=["is_active", "session_revision"])
        ActionToken.objects.filter(user=user).delete()
        audit(
            actor,
            "account.suspended" if suspended else "account.reactivated",
            subject=user,
            reason=reason.strip(),
        )
        bump(revision)


def change_password(actor, old_password, new_password):
    with authorization_write() as revision:
        user = User.objects.get(pk=actor.pk, is_active=True)
        if not user.check_password(old_password):
            raise ValidationError("Das bisherige Passwort ist nicht korrekt.")
        validate_password(new_password, user)
        user.set_password(new_password)
        user.session_revision += 1
        user.save(update_fields=["password", "session_revision"])
        ActionToken.objects.filter(user=user).delete()
        audit(user, "account.password_changed", subject=user)
        bump(revision)
        return user


def unlink_oidc(actor, password):
    from .models import OIDCIdentity

    with authorization_write() as revision:
        user = User.objects.get(pk=actor.pk, is_active=True, email_verified_at__isnull=False)
        if not user.has_usable_password() or not user.check_password(password):
            raise ValidationError("Bitte bestätige zuerst ein verwendbares lokales Passwort.")
        OIDCIdentity.objects.filter(user=user).delete()
        user.session_revision += 1
        user.save(update_fields=["session_revision"])
        audit(user, "oidc.unlinked", subject=user)
        bump(revision)
        return user


def grant_details(grant):
    return {
        "group_id": str(grant.group_id),
        "action": grant.action,
        "effect": grant.effect,
        "scope_kind": grant.scope_kind,
        "scope_id": str(grant.scope_id) if grant.scope_id else None,
        "inherit": grant.inherit,
        "max_horizon_days": grant.max_horizon_days,
        "max_duration_minutes": grant.max_duration_minutes,
    }
