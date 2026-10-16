import getpass
from pathlib import Path

from accounts.authorization import authorization_write
from accounts.models import User
from accounts.services import audit
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError

from review.models import ReviewDataset
from review.seed import ROLES


class Command(BaseCommand):
    help = "Set fictional review account passwords locally; no password argument or logging."

    def add_arguments(self, parser):
        parser.add_argument("--role", choices=[*ROLES, "all"], required=True)
        parser.add_argument(
            "--password-file", help="Optional private mode-0600 file for automation"
        )

    def handle(self, *args, **options):
        if not settings.REVIEW_MODE or not ReviewDataset.objects.exists():
            raise CommandError("Seeded review instance required")
        if options["password_file"]:
            path = Path(options["password_file"])
            if path.stat().st_mode & 0o077:
                raise CommandError("Password file must be private (0600)")
            password = path.read_text().rstrip("\n")
        else:
            password = getpass.getpass("Neues Reviewpasswort: ")
            if password != getpass.getpass("Wiederholen: "):
                raise CommandError("Passwords differ")
        with authorization_write():
            row = ReviewDataset.objects.get(pk=1)
            roles = list(ROLES) if options["role"] == "all" else [options["role"]]
            users = [User.objects.get(pk=row.accounts[key]) for key in roles]
            for user in users:
                validate_password(password, user)
            for user in users:
                user.set_password(password)
                user.session_revision += 1
                user.save(update_fields=["password", "session_revision"])
                audit(None, "review.password_set", subject=user, reason="Explicit operator command")
        self.stdout.write("Review passwords updated; no password printed")
