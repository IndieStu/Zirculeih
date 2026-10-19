import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_system_admin = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=False)
    session_revision = models.PositiveIntegerField(default=0)
    full_name = models.CharField(max_length=200, blank=True)
    street = models.CharField(max_length=200, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    profile_revision = models.PositiveIntegerField(default=0)
    privacy_version = models.CharField(max_length=100)
    privacy_acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="account_email_ci_unique")]

    def get_session_auth_hash(self):
        return self._get_session_auth_hash(secret=None) + str(self.session_revision)

    def get_session_auth_fallback_hash(self):
        # A rotated signing secret deliberately requires a new login.
        return iter(())

    @property
    def borrower_profile_complete(self):
        return bool(
            self.email_verified_at
            and all(
                getattr(self, field).strip()
                for field in ("full_name", "street", "postal_code", "city", "country", "phone")
            )
        )


class AuthorizationRevision(models.Model):
    """Singleton lock shared by authz changes and future privileged domain writes."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="one_authz_lock")]


class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, max_length=2000)
    is_active = models.BooleanField(default=True)
    is_baseline = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_baseline"],
                condition=models.Q(is_baseline=True),
                name="one_baseline_group",
            )
        ]


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    assigned_by = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="assigned"
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "group"],
                condition=models.Q(removed_at__isnull=True),
                name="one_active_membership",
            )
        ]


class Grant(models.Model):
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    effect = models.CharField(max_length=5, choices=[("allow", "Erlauben"), ("deny", "Verweigern")])
    scope_kind = models.CharField(max_length=20, default="organization")
    scope_id = models.UUIDField(null=True, blank=True)
    inherit = models.BooleanField(default=False)
    max_horizon_days = models.PositiveIntegerField(null=True, blank=True)
    max_duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    @property
    def label(self):
        from .authorization import ACTION_LABELS

        return ACTION_LABELS.get(self.action, self.action)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(scope_kind="organization", scope_id__isnull=True, inherit=False)
                    | (~models.Q(scope_kind="organization") & models.Q(scope_id__isnull=False))
                ),
                name="grant_scope_shape",
            ),
            models.CheckConstraint(
                condition=models.Q(effect__in=["allow", "deny"]), name="grant_effect_valid"
            ),
        ]


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="audit_actions"
    )
    subject = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="audit_subject"
    )
    action = models.CharField(max_length=80)
    object_id = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)


class ActionToken(models.Model):
    digest = models.CharField(primary_key=True, max_length=64)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=10)
    password_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()


class RateBucket(models.Model):
    key = models.CharField(primary_key=True, max_length=64)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()


class OIDCIdentity(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    issuer = models.URLField(max_length=500)
    subject = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["issuer", "subject"], name="unique_oidc_subject")
        ]


class OIDCStateUse(models.Model):
    digest = models.CharField(primary_key=True, max_length=64)
    expires_at = models.DateTimeField()
