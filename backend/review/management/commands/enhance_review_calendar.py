"""Add meaningful calendar scenarios without replacing team bookings or schedules."""

from datetime import datetime, time, timedelta
from uuid import uuid4

from accounts.authorization import authorization_write
from accounts.models import User
from accounts.services import audit
from bookings import services as booking
from bookings.time_rules import local_instant
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from inventory import services as inventory
from inventory.models import Category
from resources import services as resources
from resources.models import Resource

from review.models import ReviewDataset


class Command(BaseCommand):
    help = "Add month/day calendar examples once; preserve existing review data and passwords."

    def handle(self, *args, **options):
        if not settings.REVIEW_MODE:
            raise CommandError("REVIEW_MODE required")
        with authorization_write():
            marker = ReviewDataset.objects.select_for_update().get(pk=1)
            if marker.calendar_revision:
                self.stdout.write("Calendar scenarios already applied; review data preserved")
                return
            if "ux_ready" not in marker.accounts:
                raise CommandError("Run the additive UX enhancement first")
            actor = User.objects.get(pk=marker.accounts["system"])
            user = User.objects.get(pk=marker.accounts["ux_ready"])
            scope = inventory.save_tree(
                actor, Category, {"name": "Kalenderreview · Vor-Ort-Nutzung", "is_active": True}
            )
            targets = list(
                Resource.objects.filter(
                    slug__in=[
                        "review-raum",
                        "review-drucker",
                        "review-cnc",
                        "review-mini",
                        "review-mk3s",
                        "review-mk4",
                    ]
                )
            )
            for resource in targets:
                updates: dict[str, object] = {"categories": [*resource.categories.all(), scope]}
                if resource.pickup_notes == (
                    "Review-Zeitfenster 00:00–24:00, damit das Team alle Abläufe "
                    "unabhängig von Uhrzeit testen kann."
                ):
                    updates["pickup_notes"] = ""
                resources.save_resource(
                    actor,
                    updates,
                    resource_id=resource.pk,
                    expected_revision=resource.revision,
                )
                policy = resource.bookingpolicy
                maximum = (
                    240
                    if resource.slug == "review-raum"
                    else 180
                    if resource.slug == "review-cnc"
                    else 480
                )
                booking.save_policy(
                    actor,
                    resource.pk,
                    {
                        "max_duration_minutes": maximum,
                        "buffer_after_minutes": max(30, policy.buffer_after_minutes),
                    },
                    policy.revision,
                )
            for day in (2, 3, 4):
                booking.save_schedule(
                    actor,
                    {
                        "category": scope,
                        "purpose": "usage",
                        "weekday": day,
                        "start_time": time(11),
                        "end_time": time(20),
                    },
                )
            room = Resource.objects.get(slug="review-raum")
            printer = Resource.objects.get(slug="review-mk4")
            cnc = Resource.objects.get(slug="review-cnc")
            plan = [(room, 11, 12), (room, 14, 15), (printer, 12, 13), (cnc, 15, 16)]
            anchor = timezone.localdate() + timedelta(days=1)
            for _ in range(30):
                if anchor.weekday() == 2 and all(
                    booking.availability(
                        actor,
                        r.pk,
                        datetime.combine(anchor, time(s)),
                        datetime.combine(anchor, time(e)),
                        beneficiary=user,
                    ).code
                    == "available"
                    for r, s, e in plan
                ):
                    break
                anchor += timedelta(days=1)
            else:
                raise CommandError(
                    "No safe synthetic calendar day found; existing rules/data were not bypassed"
                )
            for resource, start, end in plan:
                booking.confirm(
                    actor,
                    resource.pk,
                    datetime.combine(anchor, time(start)),
                    datetime.combine(anchor, time(end)),
                    uuid4(),
                    beneficiary=user,
                )
            booking.save_schedule(
                actor,
                {
                    "category": scope,
                    "purpose": "usage",
                    "date": anchor + timedelta(days=1),
                    "is_closed": True,
                },
                exception=True,
            )
            booking.set_block(
                actor,
                {
                    "resource": cnc,
                    "start": local_instant(datetime.combine(anchor, time(17)), "Europe/Berlin"),
                    "end": local_instant(datetime.combine(anchor, time(18)), "Europe/Berlin"),
                    "reason": "Fiktive Wartung für Kalenderreview",
                },
            )
            cargo = Resource.objects.get(slug="review-lastenrad")
            cargo_category = (
                cargo.categories.first()
                or cargo.units.select_related("asset__category")
                .get(asset__inventory_number="UXR-CARGO")
                .asset.category
            )
            asset = inventory.save_asset(
                actor,
                {
                    "inventory_number": "UXR-CALENDAR-CARGO",
                    "name": "Lastenrad Tagesausleihe",
                    "location": cargo.location,
                    "category": cargo_category,
                },
            )
            days = resources.save_resource(
                actor,
                {
                    "title": "Lastenrad Tagesausleihe",
                    "slug": "review-kalender-lastenrad",
                    "type": cargo.type,
                    "location": cargo.location,
                    "location_label": cargo.location_label,
                    "visibility": "public",
                    "booking_enabled": True,
                    "categories": list(cargo.categories.all()) or [cargo_category],
                    "description": "Fiktives zusätzliches Lastenrad für den Kalenderreview.",
                },
            )
            resources.save_unit(actor, days.pk, {"name": "Lastenrad Tagesausleihe", "asset": asset})
            booking.save_policy(
                actor,
                days.pk,
                {
                    "use_mode": "physical_loan",
                    "time_mode": "days",
                    "max_days": 7,
                    "max_horizon_days": 90,
                },
            )
            for weekday in (2, 3, 4):
                for purpose in ("pickup", "return", "access"):
                    booking.save_schedule(
                        actor,
                        {
                            "resource": days,
                            "purpose": purpose,
                            "weekday": weekday,
                            "start_time": time(11),
                            "end_time": time(20),
                        },
                    )
            resources.publication(
                actor, days.pk, days.revision, "publish", "Fiktiver Tageskalenderreview"
            )
            from lending.models import AgreementAssignment
            from resources.requirements import configure

            configure(
                actor,
                days.pk,
                list(
                    AgreementAssignment.objects.filter(resource=cargo).values_list(
                        "agreement_id", flat=True
                    )
                ),
                [],
            )
            marker.calendar_revision = 1
            marker.calendar_anchor = anchor
            marker.save(update_fields=["calendar_revision", "calendar_anchor"])
            audit(None, "review.calendar_enhanced", reason="Owner month/day calendar correction")
        self.stdout.write(
            f"Calendar scenarios added for {anchor}. Existing records/passwords preserved."
        )
