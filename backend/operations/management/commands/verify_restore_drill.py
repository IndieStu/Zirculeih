import json

from django.core.management.base import BaseCommand

from operations.recovery import verify_drill


class Command(BaseCommand):
    help = "Verify isolated fictional recovery; never permits production database names."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(verify_drill(), sort_keys=True))
