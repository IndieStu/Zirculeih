from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ActionToken, RateBucket


class Command(BaseCommand):
    help = "Remove expired one-time tokens and pseudonymous rate buckets (run regularly)."

    def handle(self, *args, **options):
        ActionToken.objects.filter(expires_at__lte=timezone.now()).delete()
        RateBucket.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write("Expired authentication records removed.")
