from django.core.management.base import BaseCommand

from notifications.services import deliver_due


class Command(BaseCommand):
    help = "Sendet fällige Benachrichtigungen mit begrenzten Wiederholungen."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        self.stdout.write(str(deliver_due(options["limit"])))
