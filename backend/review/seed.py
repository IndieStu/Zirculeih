"""Explicit synthetic fixture construction through productive domain services."""

import io
from contextlib import ExitStack
from datetime import datetime, time, timedelta
from unittest.mock import patch
from uuid import uuid4

from accounts.authorization import ACTIONS, SYSTEM_ACTIONS, authorization_write
from accounts.models import Grant, Group, Membership, User
from bookings import services as booking
from bookings.models import Booking
from bookings.time_rules import local_instant
from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.utils import timezone
from inventory import extensions
from inventory import services as inventory
from inventory.models import Category, Location
from lending import agreements
from lending import services as lending
from PIL import Image, ImageDraw
from resources import services as resources

from .models import ReviewDataset

ROLES = {
    "nutzer": "Test Nutzer",
    "ausleihe": "Test Ausleihe",
    "werkstatt": "Test Werkstatt",
    "inventar": "Test Inventar",
    "admin": "Test Admin",
    "system": "Test System",
}


def seed(anchor):
    if not settings.REVIEW_MODE:
        raise CommandError("Only DEELVO_REVIEW_MODE=true permits review data")
    with authorization_write():
        prior = ReviewDataset.objects.first()
        if prior:
            if prior.version != 1 or prior.anchor_date != anchor:
                raise CommandError(
                    "Existing review dataset has another date/version; preserve or "
                    "explicitly reset the isolated stack"
                )
            return prior, False
        if User.objects.exists() or Location.objects.exists() or Booking.objects.exists():
            raise CommandError("Refusing to seed a nonempty database without our review marker")
        now_fn = timezone.now
        clock = [
            local_instant(datetime.combine(anchor - timedelta(days=10), time(8)), "Europe/Berlin")
        ]
        with ExitStack() as stack:
            # Match actual model defaults to the synthetic clock, not only service calls.
            for model in apps.get_models():
                for field in model._meta.fields:
                    if field.default is now_fn:
                        stack.enter_context(patch.object(field, "default", lambda: clock[0]))
            stack.enter_context(patch("django.utils.timezone.now", lambda: clock[0]))
            actor = User.objects.create_user(
                "seed@deelvo.example.test",
                None,
                is_system_admin=True,
                email_verified_at=clock[0],
                privacy_version="review-fixture",
            )
            group = Group.objects.create(name="Review fixture bootstrap")
            Membership.objects.create(user=actor, group=group)
            for action in ACTIONS - SYSTEM_ACTIONS:
                Grant.objects.create(group=group, action=action, effect="allow")
            users = {}
            for key, name in ROLES.items():
                users[key] = User.objects.create_user(
                    key + "@deelvo.example.test",
                    None,
                    full_name=name,
                    street="Fiktive Teststraße 1",
                    postal_code="00000",
                    city="Testort",
                    country="Testland",
                    phone="000000",
                    privacy_version="review-fixture",
                    email_verified_at=clock[0],
                    is_system_admin=key == "system",
                )
            root = inventory.save_tree(
                actor, Location, {"name": "WERK (fiktiv)", "is_active": True}
            )
            eg = inventory.save_tree(
                actor, Location, {"name": "Erdgeschoss", "parent": root, "is_active": True}
            )
            og = inventory.save_tree(
                actor, Location, {"name": "Obergeschoss", "parent": root, "is_active": True}
            )
            places = {}
            for name, parent in [
                ("Holzwerkstatt", eg),
                ("Metallwerkstatt", eg),
                ("Fahrradwerkstatt", eg),
                ("Lager", eg),
                ("Digitalwerkstatt", og),
                ("Besprechungsraum", og),
                ("Siebdruck", og),
                ("Außenbereich", root),
            ]:
                places[name] = inventory.save_tree(
                    actor, Location, {"name": name, "parent": parent, "is_active": True}
                )
            categories = {
                name: inventory.save_tree(actor, Category, {"name": name, "is_active": True})
                for name in ("Werkzeuge", "Maschinen", "Veranstaltung", "Fahrzeuge", "Inventar")
            }
            normal = Group.objects.create(name="Review · normale Nutzung")
            for a in ("booking.create_own", "booking.cancel_own"):
                Grant.objects.create(
                    group=normal,
                    action=a,
                    effect="allow",
                    max_horizon_days=30 if a == "booking.create_own" else None,
                )
            role_actions = {
                "ausleihe": [
                    "loan.checkout",
                    "loan.return",
                    "loan.extend",
                    "loan.read",
                    "loan.inspect_identity",
                    "borrower.read_contact",
                    "booking.create_for_others",
                    "booking.read_all",
                    "booking.manage_all",
                    "identifier.resolve",
                ],
                "inventar": [
                    "asset.read",
                    "asset.manage",
                    "asset.move",
                    "asset.archive",
                    "asset.read_sensitive",
                    "asset.attach",
                    "asset.export",
                    "asset.import",
                    "identifier.resolve",
                    "identifier.assign",
                    "identifier.retire",
                    "identifier.namespace_manage",
                    "location.read",
                    "location.manage",
                    "category.read",
                    "category.manage",
                    "custom_field.manage",
                ],
                "admin": list(ACTIONS - SYSTEM_ACTIONS),
                "werkstatt": [
                    "asset.read",
                    "asset.manage",
                    "asset.move",
                    "identifier.resolve",
                    "resource.manage",
                    "resource.publish",
                    "catalog.view_private",
                    "booking.read_all",
                    "booking.configure",
                    "booking.block",
                ],
            }
            for key, user in users.items():
                if key != "system":
                    Membership.objects.create(user=user, group=normal)
                if key in role_actions:
                    g = Group.objects.create(name="Review · " + ROLES[key])
                    Membership.objects.create(user=user, group=g)
                    for a in role_actions[key]:
                        extra = (
                            {
                                "scope_kind": "location",
                                "scope_id": places["Digitalwerkstatt"].pk,
                                "inherit": True,
                            }
                            if key == "werkstatt"
                            else {}
                        )
                        Grant.objects.create(group=g, action=a, effect="allow", **extra)
            assets = {}
            specs = [
                ("DRILL-01", "Akkuschrauber 1", "Holzwerkstatt", "Werkzeuge"),
                ("DRILL-02", "Akkuschrauber 2", "Holzwerkstatt", "Werkzeuge"),
                ("DRILL-03", "Akkuschrauber 3", "Holzwerkstatt", "Werkzeuge"),
                (
                    "BATTERY",
                    "Akku (Inventar, keine automatische Pflichtallokation)",
                    "Lager",
                    "Werkzeuge",
                ),
                ("CHARGER", "Ladegerät (Inventar)", "Lager", "Werkzeuge"),
                ("PRUSA", "Prusa 3D-Drucker (fiktiv)", "Digitalwerkstatt", "Maschinen"),
                ("CNC", "CNC-Fräse (Testbetrieb)", "Digitalwerkstatt", "Maschinen"),
                ("PROJECTOR", "Projektor", "Besprechungsraum", "Veranstaltung"),
                ("POWER", "Powerstation", "Lager", "Veranstaltung"),
                ("BIKE", "Fahrrad", "Fahrradwerkstatt", "Fahrzeuge"),
                ("CARGO", "Lastenrad", "Außenbereich", "Fahrzeuge"),
                ("CABLE", "Kabeltrommel", "Lager", "Veranstaltung"),
                ("SCREEN", "Siebdruckrahmen", "Siebdruck", "Inventar"),
                ("STOCK", "Werkbank (nur Inventar)", "Holzwerkstatt", "Inventar"),
                ("DAMAGE", "Beschädigtes Werkzeug", "Metallwerkstatt", "Werkzeuge"),
                ("RETIRED", "Ausgemusterter Testgegenstand", "Lager", "Inventar"),
            ]
            for code, name, place, cat in specs:
                assets[code] = inventory.save_asset(
                    actor,
                    {
                        "inventory_number": "UXR-" + code,
                        "name": name,
                        "location": places[place],
                        "category": categories[cat],
                        "description": "Vollständig fiktiver UX-Testgegenstand.",
                    },
                )
            damaged = assets["DAMAGE"]
            inventory.save_asset(
                actor,
                {"condition": "damaged", "lifecycle": "maintenance"},
                asset_id=damaged.pk,
                expected_revision=damaged.revision,
            )
            retired = assets["RETIRED"]
            inventory.archive_asset(actor, retired.pk, retired.revision, "Fiktives Archivbeispiel")
            ns = inventory.save_namespace(actor, "review-legacy", "Review-Altcode", "exact-v1")
            inventory.assign_identifier(
                actor, assets["DRILL-01"].pk, ns.pk, "WERK-TEST-001", "barcode", "Fiktiver Alias"
            )
            definition = extensions.create_field(
                actor,
                {
                    "key": "review_voltage",
                    "label": "Spannung (V)",
                    "kind": "number",
                    "is_sensitive": False,
                },
            )
            extensions.set_custom_value(
                actor, assets["DRILL-01"].pk, definition.pk, 18, assets["DRILL-01"].revision
            )
            buf = io.BytesIO()
            img = Image.new("RGB", (640, 400), "#F6F3E9")
            draw = ImageDraw.Draw(img)
            draw.rectangle((80, 120, 490, 280), fill="#5590BF")
            draw.text((100, 150), "DEELVO - FICTIONAL REVIEW ITEM", fill="#11140F")
            img.save(buf, format="PNG")
            extensions.upload_media(
                actor,
                assets["DRILL-01"].pk,
                SimpleUploadedFile("review-drill.png", buf.getvalue(), content_type="image/png"),
                is_sensitive=False,
            )
            types = {
                k: resources.save_type(actor, {"key": "review-" + k, "name": name})
                for k, name in [
                    ("room", "Raum"),
                    ("machine", "Maschine"),
                    ("tool", "Werkzeug"),
                    ("vehicle", "Fahrzeug"),
                    ("equipment", "Ausstattung"),
                ]
            }
            offers = {}
            definitions = [
                ("raum", "Besprechungsraum", "room", "Besprechungsraum", [], "onsite"),
                (
                    "cnc",
                    "CNC-Fräse (Testbetrieb ohne Einweisungsgate)",
                    "machine",
                    "Digitalwerkstatt",
                    ["CNC"],
                    "onsite",
                ),
                ("drucker", "3D-Drucker", "machine", "Digitalwerkstatt", ["PRUSA"], "onsite"),
                (
                    "bohrer",
                    "Akkuschrauber",
                    "tool",
                    "Holzwerkstatt",
                    ["DRILL-01", "DRILL-02", "DRILL-03"],
                    "physical_loan",
                ),
                ("lastenrad", "Lastenrad", "vehicle", "Außenbereich", ["CARGO"], "physical_loan"),
                (
                    "powerstation",
                    "Powerstation-Set (Zubehörcheckliste, kein Bundle)",
                    "equipment",
                    "Lager",
                    ["POWER"],
                    "physical_loan",
                ),
                ("kabel", "Kabeltrommel", "equipment", "Lager", ["CABLE"], "physical_loan"),
            ]
            for key, title, kind, place, codes, mode in definitions:
                r = resources.save_resource(
                    actor,
                    {
                        "title": title,
                        "slug": "review-" + key,
                        "type": types[kind],
                        "location": places[place],
                        "location_label": "WERK (fiktiv) · " + place,
                        "visibility": "public",
                        "booking_enabled": True,
                        "is_featured": True,
                        "categories": [
                            categories[
                                {
                                    "room": "Inventar",
                                    "machine": "Maschinen",
                                    "tool": "Werkzeuge",
                                    "vehicle": "Fahrzeuge",
                                    "equipment": "Veranstaltung",
                                }[kind]
                            ]
                        ],
                        ("description"): (
                            "Fiktives Angebot für Teamtests. Keine echte Nutzung vereinbaren."
                        ),
                        ("safety_notes"): (
                            "Nur Softwaretest. Einweisungen/Bundles sind noch nicht umgesetzt;"
                            " dies ist keine Freigabe realer Geräte."
                        ),
                        ("pickup_notes"): (
                            "Review-Zeitfenster 00:00–24:00, damit das Team alle Abläufe "
                            "unabhängig von Uhrzeit testen kann."
                        ),
                    },
                )
                units = (
                    [
                        resources.save_unit(
                            actor, r.pk, {"name": assets[c].name, "asset": assets[c]}
                        )
                        for c in codes
                    ]
                    if codes
                    else [resources.save_unit(actor, r.pk, {"name": "Raumeinheit"})]
                )
                if key == "bohrer":
                    resources.save_pool(actor, r.pk, "Fiktive äquivalente Akkuschrauber", units)
                booking.save_policy(
                    actor,
                    r.pk,
                    {
                        "use_mode": mode,
                        "max_horizon_days": 90,
                        "max_duration_minutes": 14 * 1440,
                        "max_parallel": 20,
                    },
                )
                for day in range(7):
                    for purpose in ("usage", "access", "opening", "pickup", "return"):
                        booking.save_schedule(
                            actor,
                            {
                                "resource": r,
                                "purpose": purpose,
                                "weekday": day,
                                "start_time": time(0),
                                "end_time": time(0),
                                "end_next_day": True,
                            },
                        )
                resources.publication(actor, r.pk, r.revision, "publish", "Fiktives UX-Angebot")
                offers[key] = r
            resources.upload_image(
                actor,
                offers["bohrer"].pk,
                SimpleUploadedFile("review-offer.png", buf.getvalue(), content_type="image/png"),
                "Fiktive illustrative Testgrafik eines Gegenstands",
            )
            for kind in ("general", "insurance"):
                a = agreements.create_agreement(actor, "Fiktiver Reviewtext: " + kind, kind)
                v = agreements.save_version(
                    actor,
                    a.pk,
                    (
                        "Ausschließlich Softwaretest mit fiktiven Personen und "
                        "Gegenständen. Keine echte Nutzungsvereinbarung, "
                        "Versicherungserklärung oder reale Ausleihe. Für den UX-Test diese"
                        " Textversion bestätigen."
                    ),
                )
                agreements.publish_version(actor, v.pk)
            for user in users.values():
                agreements.accept(
                    user, [v.pk for v in agreements.required_versions(offers["bohrer"])]
                )
                lending.identity_check(actor, user.pk)

            def at(offset, hour):
                return local_instant(
                    datetime.combine(anchor + timedelta(days=offset), time(hour)), "Europe/Berlin"
                )

            def reserve(key, unit, offset, start_hour, end_hour):
                start = at(offset, start_hour)
                end = at(offset, end_hour)
                mode = offers[key].bookingpolicy.use_mode
                return booking.confirm(
                    users["nutzer"],
                    offers[key].pk,
                    start.astimezone(timezone.get_current_timezone()).replace(tzinfo=None),
                    end.astimezone(timezone.get_current_timezone()).replace(tzinfo=None),
                    uuid4(),
                    unit_id=unit.pk if unit else None,
                    **(
                        {"pickup_at": start, "return_at": end - timedelta(minutes=15)}
                        if mode == "physical_loan"
                        else {}
                    ),
                )

            clock[0] = at(-3, 8)
            reserve("raum", None, 0, 14, 16)
            reserve("raum", None, 1, 10, 12)
            reserve("lastenrad", None, 0, 0, 23)
            drill_units = list(offers["bohrer"].units.order_by("asset__inventory_number"))
            out1 = reserve("bohrer", drill_units[0], -1, 10, 23)
            out2 = reserve("bohrer", drill_units[1], -1, 10, 23)
            # Overdue loan with two lines for partial return testing.
            clock[0] = at(-1, 10) + timedelta(minutes=1)
            lending.checkout(
                actor,
                users["nutzer"].pk,
                [out1.pk, out2.pk],
                uuid4(),
                checks={
                    str(b.pk): {
                        "condition": "good",
                        "accessories_checked": True,
                        "accessories": "Fiktive Zubehörkontrolle",
                    }
                    for b in (out1, out2)
                },
            )
            clock[0] = at(-3, 8)
            power = booking.confirm(
                users["nutzer"],
                offers["powerstation"].pk,
                at(-1, 10).astimezone(timezone.get_current_timezone()).replace(tzinfo=None),
                at(0, 23).astimezone(timezone.get_current_timezone()).replace(tzinfo=None),
                uuid4(),
                pickup_at=at(-1, 10),
                return_at=at(0, 22),
            )
            clock[0] = at(-1, 10) + timedelta(minutes=1)
            lending.checkout(
                actor,
                users["nutzer"].pk,
                [power.pk],
                uuid4(),
                checks={
                    str(power.pk): {
                        "condition": "good",
                        "accessories_checked": True,
                        "accessories": "Fiktive Kabelcheckliste; keine exklusive Bundleallokation",
                    }
                },
            )
            clock[0] = at(-3, 8)
            reserve("bohrer", drill_units[0], 1, 10, 23)
            clock[0] = at(0, 8)
            lending.mark_overdue()
            booking.set_block(
                actor,
                {
                    "resource": offers["drucker"],
                    "start": at(0, 0),
                    "end": at(2, 0),
                    "reason": "Fiktiver Wartungshinweis für den Teamtest",
                },
            )
            # Own-account and operational state carry real records, never fake dashboard counts.
            actor.is_active = False
            actor.save(update_fields=["is_active"])
            group.is_active = False
            group.save(update_fields=["is_active"])
            dataset = ReviewDataset.objects.create(
                anchor_date=anchor, accounts={k: str(u.pk) for k, u in users.items()}
            )
            return dataset, True
