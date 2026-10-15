from django.core.management.base import BaseCommand

from accounts.authorization import authorization_write, bump
from accounts.models import User
from accounts.services import audit


class Command(BaseCommand):
    help = "Set/remove the informational employee marker via protected operator access."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--remove", action="store_true")
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        with authorization_write() as revision:
            user = User.objects.get(email__iexact=options["email"].strip())
            user.is_employee = not options["remove"]
            user.session_revision += 1
            user.save(update_fields=["is_employee", "session_revision"])
            audit(None, "account.employee_marker_changed", subject=user, reason=options["reason"])
            bump(revision)
        self.stdout.write("Employee marker updated; no grants assigned.")
