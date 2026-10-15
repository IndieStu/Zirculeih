import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.authorization import authorization_write, bump
from accounts.models import User
from accounts.services import audit


class Command(BaseCommand):
    help = "Create the initial recovery administrator; password only via hidden interactive prompt."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if User.objects.filter(is_system_admin=True, is_active=True).exists():
            raise CommandError("An active recovery administrator already exists.")
        password = getpass.getpass("Neues Administratorpasswort: ")
        if password != getpass.getpass("Passwort wiederholen: "):
            raise CommandError("Passwords differ.")
        with authorization_write() as revision:
            if User.objects.filter(is_system_admin=True, is_active=True).exists():
                raise CommandError("An active recovery administrator already exists.")
            if User.objects.filter(email__iexact=email).exists():
                raise CommandError("Existing accounts must not be silently promoted.")
            candidate = User(email=email)
            validate_password(password, candidate)
            user = User.objects.create_user(
                email,
                password,
                is_system_admin=True,
                email_verified_at=timezone.now(),
                privacy_version="operator-bootstrap",
            )
            audit(None, "admin.bootstrapped", subject=user, reason="Protected operator command")
            bump(revision)
        self.stdout.write("Recovery administrator created. No operational grants assigned.")
