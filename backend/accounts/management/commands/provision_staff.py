from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.authorization import authorization_write, bump
from accounts.models import Membership, OIDCIdentity, User
from accounts.services import audit


class Command(BaseCommand):
    help = "Explicit operator provisioning of an Authentik staff subject; no email auto-linking."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--subject", required=True)
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        if not settings.OIDC_ENABLED:
            raise CommandError("Configure OIDC first.")
        subject, email = options["subject"], options["email"].strip().lower()
        if not subject or len(subject) > 255 or not options["reason"].strip():
            raise CommandError("Subject and reason required.")
        with authorization_write() as revision:
            if OIDCIdentity.objects.filter(issuer=settings.OIDC_ISSUER, subject=subject).exists():
                raise CommandError("Subject already linked.")
            # No takeover of an existing local email through operator convenience.
            if User.objects.filter(email__iexact=email).exists():
                raise CommandError(
                    "Existing local account: mark employee and explicitly link from its session."
                )
            user = User.objects.create_user(
                email,
                None,
                is_employee=True,
                email_verified_at=timezone.now(),
                privacy_version="operator-provisioning",
            )
            from accounts.models import Group

            Membership.objects.create(user=user, group=Group.objects.get(is_baseline=True))
            OIDCIdentity.objects.create(user=user, issuer=settings.OIDC_ISSUER, subject=subject)
            audit(None, "oidc.staff_provisioned", subject=user, reason=options["reason"])
            bump(revision)
        self.stdout.write("Staff account provisioned; no operational grants or claims imported.")
