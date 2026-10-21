import io
from datetime import timedelta

import pytest
from accounts.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone
from inventory.models import Asset, AssetMedia
from lending.models import LoanLine
from resources.models import Resource
from review.models import ReviewDataset
from review.seed import seed

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


def test_seed_guard(settings):
    settings.REVIEW_MODE = False
    with pytest.raises(CommandError, match="REVIEW_MODE"):
        seed(timezone.localdate())
    settings.REVIEW_MODE = True
    User.objects.create_user("existing@example.test", None, privacy_version="test")
    with pytest.raises(CommandError, match="nonempty"):
        seed(timezone.localdate())
    assert not ReviewDataset.objects.exists()


def test_legacy_take_home_correction_is_explicit_idempotent_and_preserves_data(settings, tmp_path):
    from bookings.models import Booking, BookingPolicy

    settings.REVIEW_MODE = True
    settings.MEDIA_ROOT = tmp_path / "media"
    seed(timezone.localdate())
    bookings = list(Booking.objects.values().order_by("pk"))
    users = list(User.objects.values("pk", "password", "session_revision").order_by("pk"))
    call_command("correct_review_lending_dates")
    call_command("correct_review_lending_dates")
    assert BookingPolicy.objects.get(resource__slug="review-bohrer").time_mode == "days"
    assert BookingPolicy.objects.get(resource__slug="review-raum").time_mode == "slots"
    assert list(Booking.objects.values().order_by("pk")) == bookings
    assert list(User.objects.values("pk", "password", "session_revision").order_by("pk")) == users


def test_seed_preserves_review_and_real_states(settings, tmp_path, client):
    settings.REVIEW_MODE = True
    settings.REVIEW_BUILD = "abcdef0"
    settings.MEDIA_ROOT = tmp_path / "media"
    anchor = timezone.localdate()
    row, created = seed(anchor)
    assert created
    assert Asset.objects.count() == 16
    assert Resource.objects.count() == 7
    assert all(r.categories.exists() for r in Resource.objects.all())
    assert AssetMedia.objects.exists()
    assert LoanLine.objects.filter(
        expected_return__lt=timezone.now(), returned_at__isnull=True
    ).exists()
    assert LoanLine.objects.filter(returned_at__isnull=True).count() == 3
    assert len(row.accounts) == 6
    user = User.objects.get(pk=row.accounts["nutzer"])
    assert not user.has_usable_password()
    password_file = tmp_path / "password"
    password_file.write_text("Fictional-Review-Only-58!\n")
    password_file.chmod(0o644)
    with pytest.raises(CommandError, match="private"):
        call_command("set_review_password", role="nutzer", password_file=str(password_file))
    password_file.chmod(0o600)
    call_command("set_review_password", role="nutzer", password_file=str(password_file))
    user.refresh_from_db()
    assert user.check_password("Fictional-Review-Only-58!")
    user.full_name = "Changed during team review"
    user.save(update_fields=["full_name"])
    assert seed(anchor)[1] is False
    user.refresh_from_db()
    assert user.full_name == "Changed during team review"
    assert user.check_password("Fictional-Review-Only-58!")
    with pytest.raises(CommandError, match="another date"):
        seed(anchor + timedelta(days=1))
    listing = io.StringIO()
    call_command("review_identifiers", stdout=listing)
    assert "UXR-DRILL-01" in listing.getvalue()
    assert "WERK-TEST-001" in listing.getvalue()
    client.force_login(user)
    assert client.get("/inventar/").status_code == 404
    assert client.get("/entdecken/").status_code == 200
    inventory_user = User.objects.get(pk=row.accounts["inventar"])
    client.force_login(inventory_user)
    assert client.get("/inventar/").status_code == 200
    assert client.get("/ausleihen/betrieb/").status_code == 404
    workshop_user = User.objects.get(pk=row.accounts["werkstatt"])
    client.force_login(workshop_user)
    cnc = Asset.objects.get(inventory_number="UXR-CNC")
    drill = Asset.objects.get(inventory_number="UXR-DRILL-01")
    assert client.get(reverse("asset_detail", args=[cnc.pk])).status_code == 200
    assert client.get(reverse("asset_detail", args=[drill.pk])).status_code == 404


def test_marker_configuration(settings, client):
    settings.REVIEW_MODE = False
    assert b"TESTINSTANZ" not in client.get("/").content
    settings.REVIEW_MODE = True
    settings.REVIEW_BUILD = "abcdef0"
    response = client.get("/")
    assert b"TESTINSTANZ" in response.content
    assert b"abcdef0" in response.content
    assert b"accounts.css?v=abcdef0" in response.content


def test_review_configuration_forces_local_mail():
    import os
    import subprocess
    import sys

    env = os.environ | {
        "DEELVO_REVIEW_MODE": "true",
        "DEELVO_REVIEW_BUILD": "abcdef0",
        "DJANGO_DEBUG": "false",
        "OIDC_ENABLED": "false",
        "EMAIL_HOST": "smtp.example.test",
        "REVIEW_EMAIL_DIR": "/tmp/deelvo-mail-test",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from config import settings; "
            "assert settings.EMAIL_BACKEND == 'django.core.mail.backends.filebased.EmailBackend'; "
            "assert settings.EMAIL_FILE_PATH == '/tmp/deelvo-mail-test'",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for name, value in [("DJANGO_DEBUG", "true"), ("DEELVO_REVIEW_BUILD", "not-a-build")]:
        invalid = subprocess.run(
            [sys.executable, "-c", "from config import settings"],
            env=env | {name: value},
            capture_output=True,
            text=True,
            check=False,
        )
        assert invalid.returncode != 0


def test_additive_ux_upgrade_preserves_review_state(settings, tmp_path):
    from accounts.authorization import allowed
    from lending.models import Acceptance
    from resources.models import UserQualification

    settings.REVIEW_MODE = True
    settings.MEDIA_ROOT = tmp_path / "media"
    marker, _ = seed(timezone.localdate())
    original = dict(User.objects.values_list("pk", "password"))
    bookings = set(
        __import__("bookings.models", fromlist=["Booking"]).Booking.objects.values_list(
            "pk", flat=True
        )
    )
    call_command("enhance_review_ux")
    marker.refresh_from_db()
    assert len(marker.accounts) == 10
    assert (
        Resource.objects.filter(slug__in=["review-mini", "review-mk3s", "review-mk4"]).count() == 3
    )
    for uid, password in original.items():
        assert User.objects.get(pk=uid).password == password
    assert bookings.issubset(
        set(
            __import__("bookings.models", fromlist=["Booking"]).Booking.objects.values_list(
                "pk", flat=True
            )
        )
    )
    admin = User.objects.get(pk=marker.accounts["admin"])
    assert allowed(admin, "permissions.manage") and allowed(admin, "resource.manage")
    ready = User.objects.get(pk=marker.accounts["ux_ready"])
    old = User.objects.get(pk=marker.accounts["ux_old"])
    assert not allowed(ready, "permissions.manage")
    assert Acceptance.objects.filter(user=ready, version__number=2).exists()
    assert Acceptance.objects.filter(user=old, version__number=1).exists()
    assert not Acceptance.objects.filter(user=old, version__number=2).exists()
    assert UserQualification.objects.filter(user=ready).count() == 2
    count = Resource.objects.count()
    call_command("enhance_review_ux")
    assert Resource.objects.count() == count


def test_calendar_review_additions_preserve_existing_records(settings, tmp_path):
    from bookings.models import Booking, ResourceBlock, ScheduleException
    from resources.calendar import calendar

    settings.REVIEW_MODE = True
    settings.MEDIA_ROOT = tmp_path / "media"
    marker, _ = seed(timezone.localdate())
    call_command("enhance_review_ux")
    before = dict(User.objects.values_list("pk", "password"))
    prior = set(Booking.objects.values_list("pk", flat=True))
    call_command("enhance_review_calendar")
    marker.refresh_from_db()
    assert marker.calendar_revision == 1 and marker.calendar_anchor.weekday() == 2
    assert prior.issubset(set(Booking.objects.values_list("pk", flat=True)))
    assert Booking.objects.count() == len(prior) + 4
    assert all(User.objects.get(pk=pk).password == password for pk, password in before.items())
    room = Resource.objects.get(slug="review-raum")
    assert room.bookingpolicy.max_duration_minutes == 240
    assert room.bookingpolicy.buffer_after_minutes >= 30
    assert ScheduleException.objects.filter(
        category__name="Kalenderreview · Vor-Ort-Nutzung", is_closed=True
    ).exists()
    assert ResourceBlock.objects.filter(reason="Fiktive Wartung für Kalenderreview").exists()
    day = calendar(room, marker.calendar_anchor.isoformat())
    assert {"booked", "transition", "available", "closed"}.issubset(
        {r["state"] for r in day["segments"]}
    )
    call_command("enhance_review_calendar")
    assert Booking.objects.count() == len(prior) + 4


def test_phase7_examples_are_explicit_additive_and_idempotent(settings, tmp_path):
    settings.REVIEW_MODE = True
    settings.MEDIA_ROOT = tmp_path / "media"
    marker, _ = seed(timezone.localdate())
    call_command("enhance_review_ux")
    before = dict(User.objects.values_list("pk", "password"))
    old_resources = set(Resource.objects.values_list("pk", flat=True))
    from bookings.models import Booking

    old_bookings = list(Booking.objects.values())
    call_command("enhance_review_phase7")
    assert Resource.objects.count() == len(old_resources) + 4
    assert old_resources.issubset(set(Resource.objects.values_list("pk", flat=True)))
    assert list(Booking.objects.values()) == old_bookings
    assert all(User.objects.get(pk=pk).password == password for pk, password in before.items())
    root = Resource.objects.get(slug="review-p7-bike")
    assert root.bundle_components.filter(required=True).count() == 3
    call_command("enhance_review_phase7")
    assert Resource.objects.count() == len(old_resources) + 4
