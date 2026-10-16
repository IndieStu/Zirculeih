from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from review.models import ReviewDataset
from review.seed import seed


class Command(BaseCommand):
    help = "Explicit fictional UX dataset; empty review database only, no implicit reset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date", type=date.fromisoformat, help="Anchor date; first run defaults to local today"
        )

    def handle(self, *args, **options):
        prior = ReviewDataset.objects.first()
        anchor = options["date"] or (prior.anchor_date if prior else timezone.localdate())
        try:
            row, created = seed(anchor)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"{('Created') if created else ('Preserved')} fictional review dataset v{
                row.version
            }, anchor {row.anchor_date}. Set passwords explicitly with set_review_password."
        )
