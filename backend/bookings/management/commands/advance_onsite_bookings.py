from django.core.management.base import BaseCommand

from bookings.services import advance_onsite_bookings


class Command(BaseCommand):
    help = "Advance onsite bookings only; never records a physical return."

    def handle(self, *args, **options):
        self.stdout.write(f"{advance_onsite_bookings()} Vor-Ort-Buchungen aktualisiert.")
