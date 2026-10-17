"""Explicit additive review upgrade. No reset and no password rotation."""

from datetime import time

from accounts.admin_access import compose_admin
from accounts.authorization import authorization_write
from accounts.models import Membership, User
from accounts.services import audit
from bookings import services as booking
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from inventory import services as inventory
from lending import agreements
from resources import requirements
from resources import services as resources
from resources.models import Resource

from review.models import ReviewDataset


class Command(BaseCommand):
    help = "Add fictional UX scenarios once, preserving existing review records and passwords."

    def handle(self, *args, **options):
        if not settings.REVIEW_MODE:
            raise CommandError("REVIEW_MODE required")
        with authorization_write():
            marker = ReviewDataset.objects.select_for_update().filter(pk=1).first()
            if not marker:
                raise CommandError("Existing fictional dataset required")
            if "ux_ready" in marker.accounts:
                self.stdout.write("UX additions already applied; existing data preserved")
                return
            actor = User.objects.get(pk=marker.accounts["system"])
            compose_admin(actor.pk)
            admin = User.objects.get(pk=marker.accounts["admin"])
            admin.is_system_admin = True
            admin.save(update_fields=["is_system_admin"])
            compose_admin(admin.pk)
            audit(None, "review.admin_unified", subject=admin, reason="Owner UX correction")
            cnc = Resource.objects.get(slug="review-cnc")
            printer = Resource.objects.get(slug="review-drucker")
            cargo = Resource.objects.get(slug="review-lastenrad")
            for existing in Resource.objects.filter(slug__startswith="review-"):
                updates = {}
                if existing.title == "CNC-Fräse (Testbetrieb ohne Einweisungsgate)":
                    updates["title"] = "CNC-Fräse"
                if existing.safety_notes == (
                    "Nur Softwaretest. Einweisungen/Bundles sind noch nicht umgesetzt;"
                    " dies ist keine Freigabe realer Geräte."
                ):
                    updates["safety_notes"] = "Fiktiver Softwaretest. Keine echte Gerätenutzung."
                if updates:
                    resources.save_resource(
                        actor, updates, resource_id=existing.pk, expected_revision=existing.revision
                    )
            q = requirements.create_type(actor, "Review · 3D-Druck")
            cq = requirements.create_type(actor, "Review · CNC")
            text = agreements.create_agreement(actor, "Review · 3D-Druck Nutzung", "additional")
            v1 = agreements.save_version(
                actor, text.pk, "Fiktive Druckervereinbarung Version 1. Nur Softwaretest."
            )
            agreements.publish_version(actor, v1.pk)
            requirements.configure(actor, printer.pk, [text.pk], [q.pk])
            requirements.configure(actor, cnc.pk, [], [cq.pk])
            ct = agreements.create_agreement(actor, "Review · Lastenrad Nutzung", "additional")
            cv = agreements.save_version(
                actor, ct.pk, "Fiktive Lastenradvereinbarung. Nur Softwaretest."
            )
            agreements.publish_version(actor, cv.pk)
            requirements.configure(actor, cargo.pk, [ct.pk], [])
            baseline = Membership.objects.get(
                user_id=marker.accounts["nutzer"], removed_at=None
            ).group
            users = {}
            for key, name in [
                ("ux_ready", "Voraussetzungen erfüllt"),
                ("ux_old", "Alte Vereinbarung"),
                ("ux_noqualification", "Einweisung fehlt"),
                ("ux_neither", "Beides fehlt"),
            ]:
                user = User.objects.create_user(
                    f"{key}@deelvo.example.test",
                    None,
                    full_name="Test " + name,
                    street="Fiktive Teststraße 1",
                    postal_code="00000",
                    city="Testort",
                    country="Testland",
                    phone="000000",
                    privacy_version="review-fixture",
                    email_verified_at=timezone.now(),
                )
                Membership.objects.create(user=user, group=baseline)
                users[key] = user
                marker.accounts[key] = str(user.pk)
            for key in ("ux_ready", "ux_old"):
                requirements.issue(actor, users[key].pk, q.pk)
                requirements.issue(actor, users[key].pk, cq.pk)
                agreements.accept(users[key], [v1.pk])
            v2 = agreements.save_version(
                actor, text.pk, "Fiktive Druckervereinbarung Version 2. Nur Softwaretest."
            )
            agreements.publish_version(actor, v2.pk)
            for key in ("ux_ready", "ux_noqualification"):
                agreements.accept(users[key], [v2.pk])
            # New offers distinguish non-equivalent devices, while the old pool stays intact.
            category = (
                printer.categories.first()
                or printer.units.select_related("asset__category")
                .get(asset__inventory_number="UXR-PRUSA")
                .asset.category
            )
            for key, title in [
                ("mini", "Prusa Mini+"),
                ("mk3s", "Prusa MK3S"),
                ("mk4", "Prusa MK4"),
            ]:
                asset = inventory.save_asset(
                    actor,
                    {
                        "inventory_number": "UXR-" + key.upper(),
                        "name": title,
                        "location": printer.location,
                        "category": category,
                    },
                )
                resource = resources.save_resource(
                    actor,
                    {
                        "title": title,
                        "slug": "review-" + key,
                        "type": printer.type,
                        "location": printer.location,
                        "visibility": "public",
                        "location_label": printer.location_label,
                        "catalog_area": "Digitalwerkstatt",
                        "booking_enabled": True,
                        "categories": list(printer.categories.all()) or [category],
                        "description": "Fiktives Gerät für den UX-Test.",
                    },
                )
                resources.save_unit(actor, resource.pk, {"name": title, "asset": asset})
                booking.save_policy(actor, resource.pk, {"use_mode": "onsite", "max_parallel": 5})
                for day in range(7):
                    for purpose in ("usage", "access", "opening"):
                        booking.save_schedule(
                            actor,
                            {
                                "resource": resource,
                                "purpose": purpose,
                                "weekday": day,
                                "start_time": time(9),
                                "end_time": time(18),
                            },
                        )
                resources.publication(
                    actor, resource.pk, resource.revision, "publish", "Fictional UX fixture"
                )
                requirements.configure(actor, resource.pk, [text.pk], [q.pk])
            marker.save(update_fields=["accounts"])
            audit(None, "review.ux_enhanced", reason="Additive owner UX review scenarios")
        self.stdout.write(
            "UX scenarios added. Existing records/passwords retained. "
            "Set new test passwords explicitly."
        )
