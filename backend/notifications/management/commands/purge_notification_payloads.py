from django.core.management.base import BaseCommand

from notifications.services import purge_payloads


class Command(BaseCommand):
    help = "Entfernt alte terminale Nachrichteninhalte; Idempotenz-/Statushistorie bleibt erhalten."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        self.stdout.write(str(purge_payloads(options["days"])))
