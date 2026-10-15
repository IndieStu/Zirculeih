from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import ImportPreview


class Command(BaseCommand):
    help = "Remove expired actor-owned CSV previews; never removes assets or media."

    def handle(self, *args, **options):
        count, _ = ImportPreview.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Expired inventory previews removed: {count}")
