"""Explicit fictional Phase-7 bundle examples; no credential or existing record edits."""

from datetime import time

from accounts.authorization import authorization_write
from accounts.models import User
from bookings import services as bookings
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from inventory import services as inventory
from inventory.models import Category
from resources import bundles, requirements
from resources import services as resources
from resources.models import Resource

from review.models import ReviewDataset


class Command(BaseCommand):
    help = "Add an independent fictional cargo-bike bundle once, without changing existing data."

    def handle(self, *args, **options):
        if not settings.REVIEW_MODE:
            raise CommandError("REVIEW_MODE required")
        with authorization_write():
            marker = ReviewDataset.objects.select_for_update().get(pk=1)
            slugs = ["review-p7-bike", "review-p7-battery", "review-p7-charger", "review-p7-lock"]
            count = Resource.objects.filter(slug__in=slugs).count()
            if count == 4:
                self.stdout.write("Phase-7 examples already present; existing data preserved")
                return
            if count:
                raise CommandError("Partial/colliding fixture detected; no records overwritten")
            if "ux_ready" not in marker.accounts:
                raise CommandError("Apply enhance_review_ux first")
            actor = User.objects.get(pk=marker.accounts["system"])
            cargo = Resource.objects.get(slug="review-lastenrad")
            equipment = Resource.objects.get(slug="review-kabel")
            category = inventory.save_tree(
                actor, Category, {"name": "Phase-7-Bundlereview", "is_active": True}
            )
            rows = []
            for i, (slug, title) in enumerate(
                zip(
                    slugs,
                    [
                        "Lastenrad mit Zubehör",
                        "Akku · Bundlereview",
                        "Ladegerät · Bundlereview",
                        "Schloss · Bundlereview",
                    ],
                    strict=True,
                )
            ):
                asset = inventory.save_asset(
                    actor,
                    {
                        "inventory_number": f"UXR-P7-{i}",
                        "name": title,
                        "category": category,
                        "location": cargo.location,
                    },
                )
                row = resources.save_resource(
                    actor,
                    {
                        "title": title,
                        "slug": slug,
                        "type": cargo.type if i == 0 else equipment.type,
                        "location": cargo.location,
                        "location_label": cargo.location_label,
                        "visibility": "public",
                        "booking_enabled": True,
                        "categories": [category],
                        "description": (
                            "Eigenständiges fiktives Exemplar für Phase-7-Bundletests; "
                            "keine echte Ausleihe."
                        ),
                    },
                )
                resources.save_unit(
                    actor, row.pk, {"name": title, "public_name": title, "asset": asset}
                )
                bookings.save_policy(
                    actor,
                    row.pk,
                    {
                        "use_mode": "physical_loan",
                        "time_mode": "days",
                        "max_days": 7,
                        "max_horizon_days": 90,
                    },
                )
                for weekday in (2, 3, 4):
                    for purpose in ("access", "pickup", "return"):
                        bookings.save_schedule(
                            actor,
                            {
                                "resource": row,
                                "purpose": purpose,
                                "weekday": weekday,
                                "start_time": time(11),
                                "end_time": time(20),
                            },
                        )
                rows.append(
                    resources.publication(
                        actor, row.pk, row.revision, "publish", "Fiktiver Phase-7-Review"
                    )
                )
            root = rows[0]
            bundles.configure(actor, root.pk, [(r, True) for r in rows[1:]], root.revision)
            q = requirements.create_type(actor, "Review · Akkusystem", resource=rows[1])
            requirements.configure(actor, rows[1].pk, [], [q.pk])
            requirements.issue(
                actor, marker.accounts["ux_ready"], q.pk, "Fiktiver Phase-7-Nachweis"
            )
        self.stdout.write(
            "Phase-7 cargo bike, battery, charger and lock added; passwords unchanged"
        )
