from datetime import timedelta

from accounts.models import OIDCStateUse
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Remove hashed callback states expired more than 24 hours ago; no active flow is reusable."
    )

    def handle(self, *args, **options):
        count, _ = OIDCStateUse.objects.filter(
            expires_at__lt=timezone.now() - timedelta(days=1)
        ).delete()
        self.stdout.write(str(count))
