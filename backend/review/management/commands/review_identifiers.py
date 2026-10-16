import csv

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from inventory.models import Identifier

from review.models import ReviewDataset


class Command(BaseCommand):
    help = "List fictional review identifiers as CSV for manual/HID input. Operator-only command."

    def handle(self, *args, **options):
        if not settings.REVIEW_MODE or not ReviewDataset.objects.exists():
            raise CommandError("Seeded review instance required")
        writer = csv.writer(self.stdout)
        writer.writerow(["Inventory", "Item", "Namespace", "Identifier"])
        for row in (
            Identifier.objects.filter(asset__inventory_number__startswith="UXR-")
            .select_related("asset", "namespace")
            .order_by("asset__inventory_number", "namespace__key")
        ):
            writer.writerow(
                [row.asset.inventory_number, row.asset.name, row.namespace.key, row.raw_value]
            )
