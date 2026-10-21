"""Explicit correction of untouched legacy fictional lending policies, no reseed."""

from accounts.authorization import authorization_write
from accounts.models import User
from bookings.models import BookingPolicy
from bookings.services import save_policy
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from review.models import ReviewDataset


class Command(BaseCommand):
    help = "Correct legacy fictional take-home offers to inclusive calendar-day lending."

    def handle(self, *args, **options):
        if not settings.REVIEW_MODE:
            raise CommandError("Review mode required")
        with authorization_write():
            dataset = ReviewDataset.objects.get(pk=1)
            actor = User.objects.get(pk=dataset.accounts["admin"])
            changed = 0
            for slug in (
                "review-bohrer",
                "review-lastenrad",
                "review-powerstation",
                "review-kabel",
            ):
                policy = BookingPolicy.objects.select_related("resource").get(resource__slug=slug)
                if policy.time_mode == "days":
                    continue
                # The UX enhancement only enabled the cargo agreement (revision 2).
                legacy_revision = policy.revision == 1 or (
                    slug == "review-lastenrad"
                    and policy.revision == 2
                    and policy.requires_agreement
                )
                if (
                    policy.use_mode != "physical_loan"
                    or policy.time_mode != "slots"
                    or not legacy_revision
                    or policy.max_duration_minutes != 14 * 1440
                    or policy.max_days != 14
                ):
                    raise CommandError(
                        "Changed review policy requires explicit operator review: " + slug
                    )
                save_policy(actor, policy.resource_id, {"time_mode": "days"}, policy.revision)
                changed += 1
        self.stdout.write(
            f"Corrected {changed} legacy review policies; existing bookings unchanged."
        )
