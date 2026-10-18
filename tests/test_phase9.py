from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from accounts import services as accounts
from accounts.models import Grant
from bookings import recurrence
from bookings import services as bookings
from bookings.models import Booking
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from icalendar import Calendar
from notifications import calendars, reminders, services
from notifications.models import CalendarFeed, Delivery, NotificationPreference
from test_bookings import configured as configured_fixture
from test_lending import lending_setup as lending_fixture
from test_phase8 import setup as series_fixture

configured = configured_fixture
lending_setup = lending_fixture
setup = series_fixture
pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture(autouse=True)
def local_mail(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


def reserve(c):
    _, r, _, _, user, s, e = c
    return bookings.confirm(user, r.pk, s, e, uuid4())


def events(raw):
    return Calendar.from_ical(raw).walk("VEVENT")


def test_transactional_encrypted_outbox_idempotent_delivery(configured):
    row = reserve(configured)
    delivery = Delivery.objects.get(kind="booking.confirmed")
    assert row.beneficiary.email.encode() not in bytes(delivery.payload)
    assert services.deliver_due() == 1 and len(mail.outbox) == 1
    assert services.deliver_due() == 0 and len(mail.outbox) == 1
    assert "Message-ID" in mail.outbox[0].extra_headers
    key = uuid4()
    _, r, _, _, user, s, e = configured
    bookings.confirm(user, r.pk, s + timedelta(days=1), e + timedelta(days=1), key)
    bookings.confirm(user, r.pk, s + timedelta(days=1), e + timedelta(days=1), key)
    assert Delivery.objects.count() == 2


def test_mail_failure_never_rolls_back_booking_and_retries_bounded(configured, monkeypatch):
    row = reserve(configured)
    delivery = Delivery.objects.get(kind="booking.confirmed")
    with patch(
        "notifications.services.EmailMessage.send",
        side_effect=OSError("SECRET SMTP recipient@example.test"),
    ):
        assert not services.deliver_one(delivery.pk)
    delivery.refresh_from_db()
    assert delivery.status == "pending" and delivery.error_code == "delivery_failed"
    assert delivery.attempts == 1 and row.claim.is_active
    assert "SECRET" not in delivery.error_code
    monkeypatch.setattr(timezone, "now", lambda: delivery.next_attempt + timedelta(seconds=1))
    assert services.deliver_one(delivery.pk)
    assert Booking.objects.get(pk=row.pk).status == "confirmed"


def test_rolled_back_domain_has_no_outbox(configured):
    with pytest.raises(RuntimeError), transaction.atomic():
        reserve(configured)
        raise RuntimeError("Rollback")
    assert not Delivery.objects.exists() and not Booking.objects.exists()


def test_revoked_or_suspended_recipient_gets_no_pending_mail(configured):
    row = reserve(configured)
    delivery = Delivery.objects.get(kind="booking.confirmed")
    user = row.beneficiary
    user.is_active = False
    user.save()
    assert not services.deliver_one(delivery.pk)
    delivery.refresh_from_db()
    assert delivery.status == "skipped"


def test_auth_tokens_encrypted_outbox_and_immediate_delivery(configured):
    *_, user, s, e = configured
    raw = accounts.issue_token(user, "reset")
    delivery = Delivery.objects.get(kind="auth.reset")
    assert raw.encode() not in bytes(delivery.payload)
    accounts.email_token(user, "reset", raw)
    assert raw in mail.outbox[0].body
    assert Delivery.objects.filter(kind="auth.reset").count() == 1
    raw2 = accounts.issue_token(user, "reset")
    accounts.issue_token(user, "reset")
    old = Delivery.objects.get(
        key="token:" + __import__("hashlib").sha256(raw2.encode()).hexdigest()
    )
    assert not services.deliver_one(old.pk)


def test_feed_stable_uid_revision_cancel_no_pii(configured):
    row = reserve(configured)
    user = row.beneficiary
    first = calendars.serialize(user)
    event = events(first)[0]
    assert str(event["UID"]) == str(row.pk) + "@deelvo.invalid"
    assert (
        user.email.encode() not in first and user.full_name.encode() not in first
        if user.full_name
        else user.email.encode() not in first
    )
    assert calendars.serialize(user) == first
    bookings.cancel(user, row.pk, row.revision, "Nicht benötigt")
    changed = events(calendars.serialize(user))[0]
    assert changed["UID"] == event["UID"] and changed["STATUS"] == "CANCELLED"
    assert changed["SEQUENCE"] > event["SEQUENCE"]
    assert b"\r\n" in first


def test_ics_escaping_octets_and_injection(configured):
    _, r, _, _, user, _, _ = configured
    r.title = "ÄÖÜ" * 35 + "\r\nBEGIN:VEVENT,semi;back\\"
    r.save()
    reserve(configured)
    raw = calendars.serialize(user)
    assert all(len(line) <= 75 for line in raw.split(b"\r\n"))
    parsed = events(raw)
    assert len(parsed) == 1 and str(parsed[0]["SUMMARY"]) == r.title.replace("\r\n", "\n")


def test_series_move_retains_logical_uid_and_cancellation(setup):
    staff, r, _, _, user, s, e = setup
    proposal = recurrence.create_approved(
        staff,
        r.pk,
        s,
        e,
        uuid4(),
        beneficiary=user,
        weekdays=[s.weekday()],
        count=2,
        reason="Geprüft",
    )
    row = proposal.occurrences.first()
    before = {str(ev["UID"]): ev for ev in events(calendars.serialize(user))}
    uid = str(row.pk) + "@deelvo.invalid"
    change = recurrence.exception(
        staff,
        row.pk,
        row.booking.revision,
        "Später",
        start=s + timedelta(hours=2),
        end=e + timedelta(hours=2),
    )
    after = {str(ev["UID"]): ev for ev in events(calendars.serialize(user))}
    assert set(before) == set(after) and after[uid]["SEQUENCE"] > before[uid]["SEQUENCE"]
    recurrence.exception(user, row.pk, change.replacement.revision, "Entfällt")
    final = {str(ev["UID"]): ev for ev in events(calendars.serialize(user))}
    assert final[uid]["STATUS"] == "CANCELLED" and set(final) == set(before)


def test_feed_token_hash_revocation_regeneration_and_scope(configured, client):
    staff, r, _, _, user, _, _ = configured
    reserve(configured)
    feed, raw = calendars.create(user, "Mein Kalender", "personal")
    assert raw not in feed.digest and len(feed.digest) == 64
    response = client.get(reverse("calendar_subscription", args=[raw]))
    assert response.status_code == 200 and response["Cache-Control"] == "no-store, private"
    assert response["Referrer-Policy"] == "no-referrer"
    _, new = calendars.regenerate(user, feed.pk)
    assert client.get(reverse("calendar_subscription", args=[raw])).status_code == 404
    assert client.get(reverse("calendar_subscription", args=[new])).status_code == 200
    calendars.revoke(user, feed.pk)
    assert client.get(reverse("calendar_subscription", args=[new])).status_code == 404
    with pytest.raises(PermissionDenied):
        calendars.create(user, "Alles", "organization")
    with pytest.raises(CalendarFeed.DoesNotExist):
        calendars.revoke(staff, feed.pk)


def test_resource_feed_filters_current_acl_and_never_borrower_details(configured, client):
    staff, r, _, _, user, _, _ = configured
    reserve(configured)
    feed, raw = calendars.create(staff, "Raum", "resource", r.pk)
    assert user.email.encode() not in calendars.fetch(raw)
    Grant.objects.filter(group__membership__user=staff, action="booking.read_all").delete()
    assert client.get(reverse("calendar_subscription", args=[raw])).status_code == 404


def test_web_calendar_forms_csrf_and_preferences(configured, client):
    staff, r, _, _, user, s, e = configured
    reserve(configured)
    client.force_login(user)
    assert (
        client.get(reverse("personal_calendar"), {"day": s.date().isoformat()}).status_code == 200
    )
    response = client.post(
        reverse("calendar_feeds"), dict(action="create", label="Test", scope="personal", days=30)
    )
    assert response.status_code == 200 and response.context["raw_url"]
    raw = response.context["raw_url"].rsplit("/", 1)[-1].removesuffix(".ics")
    assert raw.encode() not in client.get(reverse("calendar_feeds")).content
    secure = Client(enforce_csrf_checks=True)
    secure.force_login(user)
    assert (
        secure.post(
            reverse("calendar_feeds"), dict(action="create", label="x", scope="personal", days=30)
        ).status_code
        == 403
    )
    assert client.get(reverse("notification_admin")).status_code == 404
    client.post(reverse("notification_preferences"), {"locale": "en"})
    assert NotificationPreference.objects.get(user=user).locale == "en"


def test_reminders_idempotent_actual_custody_and_return(lending_setup, monkeypatch):
    from lending import services as lending

    staff, r, _, _, user, s, e, pickup, due, _ = lending_setup
    booking = bookings.confirm(user, r.pk, s, e, uuid4(), pickup_at=pickup, return_at=due)
    monkeypatch.setattr(timezone, "now", lambda: pickup - timedelta(hours=1))
    reminders.schedule()
    reminders.schedule()
    assert Delivery.objects.filter(kind="pickup").count() == 1
    lending.identity_check(staff, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    lending.checkout(
        staff,
        user.pk,
        [booking.pk],
        uuid4(),
        checks={str(booking.pk): {"condition": "good", "accessories_checked": True}},
    )
    reminders.schedule()
    reminders.schedule()
    assert Delivery.objects.filter(kind="return").count() == 1
    monkeypatch.setattr(timezone, "now", lambda: due + timedelta(hours=1))
    reminders.schedule()
    reminders.schedule()
    assert Delivery.objects.filter(kind="overdue").count() == 1


def test_attempt_cap_and_terminal_payload_purge(configured, monkeypatch):
    reserve(configured)
    delivery = Delivery.objects.get(kind="booking.confirmed")
    current = timezone.now()
    monkeypatch.setattr(timezone, "now", lambda: current)
    with patch("notifications.services.EmailMessage.send", side_effect=OSError("PRIVATE")):
        for _ in range(5):
            services.deliver_one(delivery.pk)
            delivery.refresh_from_db()
            current = delivery.next_attempt + timedelta(seconds=1)
    assert delivery.status == "failed" and delivery.attempts == 5
    assert not services.deliver_one(delivery.pk)
    current += timedelta(days=31)
    assert services.purge_payloads() == 1
    delivery.refresh_from_db()
    assert not delivery.payload
    with pytest.raises(IntegrityError), transaction.atomic():
        Delivery.objects.filter(pk=delivery.pk).update(payload=b"changed envelope")


def test_immutable_feed_scope_expiry_and_token_not_logged(configured, client, caplog, monkeypatch):
    staff, r, _, _, user, _, _ = configured
    reserve(configured)
    feed, raw = calendars.create(user, "Privat", "personal", days=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        CalendarFeed.objects.filter(pk=feed.pk).update(scope="organization")
    client.get(reverse("calendar_subscription", args=[raw]))
    assert raw not in caplog.text
    future = timezone.now() + timedelta(days=2)
    monkeypatch.setattr(timezone, "now", lambda: future)
    assert client.get(reverse("calendar_subscription", args=[raw])).status_code == 404


def test_calendar_dates_across_dst_are_true_exclusive_dates(configured):
    from datetime import time

    from bookings.models import ScheduleWindow

    staff, r, _, p, user, _, _ = configured
    bookings.save_policy(staff, r.pk, {"time_mode": "days"}, p.revision)
    ScheduleWindow.objects.filter(resource=r).delete()
    for weekday in range(7):
        for purpose in ("usage", "access", "opening"):
            bookings.save_schedule(
                staff,
                dict(
                    resource=r,
                    purpose=purpose,
                    weekday=weekday,
                    start_time=time(0),
                    end_time=time(0),
                    end_next_day=True,
                ),
            )
    row = bookings.confirm(user, r.pk, date(2026, 10, 24), date(2026, 10, 26), uuid4())
    event = events(calendars.serialize(user))[0]
    assert event.decoded("DTSTART") == date(2026, 10, 24)
    assert event.decoded("DTEND") == date(2026, 10, 27)
    assert row.end - row.start == timedelta(hours=73)


def test_template_admin_localization_and_no_operational_pii(configured, client):
    staff, r, _, _, user, s, e = configured
    with pytest.raises(PermissionDenied):
        services.save_template(staff, "booking.confirmed", "de", "Betreff", "${url}")
    staff.is_system_admin = True
    staff.save()
    with pytest.raises(ValidationError):
        services.save_template(staff, "booking.confirmed", "de", "bad\nheader", "${url}")
    with pytest.raises(ValidationError):
        services.save_template(staff, "booking.confirmed", "de", "Betreff", "${password}")
    services.save_template(staff, "booking.confirmed", "en", "Deelvo reservation", "View: ${url}")
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    pref.locale = "en"
    pref.save()
    reserve(configured)
    assert services.deliver_due() == 1 and mail.outbox[0].subject == "Deelvo reservation"
    client.force_login(staff)
    response = client.get(reverse("notification_admin"))
    assert response.status_code == 200 and user.email.encode() not in response.content
    services.save_settings(staff, {"qualification_enabled": True})
    pref.qualification_email = False
    pref.save()
    row = services.enqueue(
        user, "qualification.issued", "optional-test", url="http://localhost/konto/"
    )
    assert not services.deliver_one(row.pk)


def test_feed_category_location_current_denies_and_foreign_bookings(configured):
    staff, r, _, _, user, _, _ = configured
    from inventory.models import Category

    category = Category.objects.create(name="Kalendergruppe")
    r.categories.add(category)
    reserve(configured)
    assert len(events(calendars.serialize(staff, "category", category.pk))) == 1
    assert len(events(calendars.serialize(staff, "location", r.location_id))) == 1
    group = staff.membership_set.get(removed_at=None).group
    Grant.objects.create(
        group=group, action="booking.read_all", scope_kind="resource", scope_id=r.pk, effect="deny"
    )
    assert not events(calendars.serialize(staff, "category", category.pk))
    assert not events(calendars.serialize(staff, "organization"))


@pytest.mark.django_db(transaction=True)
def test_concurrent_workers_send_once(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    reserve(configured)
    delivery = Delivery.objects.get(kind="booking.confirmed")
    barrier = Barrier(4)

    def worker(_):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            return services.deliver_one(delivery.pk)
        finally:
            close_old_connections()

    with patch("notifications.services.EmailMessage.send", return_value=1) as sender:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(worker, range(4)))
    assert results.count(True) == 1 and sender.call_count == 1
    delivery.refresh_from_db()
    assert delivery.status == "sent" and delivery.attempts == 1


def test_series_preview_has_no_mail_side_effect_and_approval_one_summary(setup):
    staff, r, _, _, user, s, e = setup
    proposal = recurrence.submit(user, r.pk, s, e, uuid4(), weekdays=[s.weekday()], count=3)
    before = Delivery.objects.count()
    recurrence.preview(staff, proposal.pk)
    assert Delivery.objects.count() == before
    recurrence.approve(staff, proposal.pk, 1, "Geprüft")
    assert services.deliver_due() == 2  # request receipt plus one approval summary
    assert Delivery.objects.filter(kind="booking.confirmed", status="skipped").count() == 3


def test_bundle_confirmation_one_mail_and_reminders_skip_returned_custody(configured):
    from resources import bundles
    from test_phase7 import component

    staff, r, _, _, _, _, _ = configured
    child = component(configured)
    bundles.configure(staff, r.pk, [(child, True)], r.revision)
    reserve(configured)
    assert services.deliver_due() == 1
    assert Delivery.objects.filter(status="skipped").count() == 1


def test_return_clears_pending_reminders_without_replaying_them(lending_setup, monkeypatch):
    from lending import services as lending

    staff, r, _, _, user, s, e, pickup, due, _ = lending_setup
    booking = bookings.confirm(user, r.pk, s, e, uuid4(), pickup_at=pickup, return_at=due)
    monkeypatch.setattr(timezone, "now", lambda: pickup - timedelta(hours=1))
    reminders.schedule()
    lending.identity_check(staff, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    loan = lending.checkout(
        staff,
        user.pk,
        [booking.pk],
        uuid4(),
        checks={str(booking.pk): {"condition": "good", "accessories_checked": True}},
    )
    reminders.schedule()
    monkeypatch.setattr(timezone, "now", lambda: due + timedelta(hours=1))
    reminders.schedule()
    line = loan.lines.get()
    lending.return_lines(
        staff, loan.pk, {str(line.pk): {"condition": "good", "accessories_checked": True}}, uuid4()
    )
    for row in Delivery.objects.filter(kind__in=["pickup", "return", "overdue"]):
        assert not services.deliver_one(row.pk)
        row.refresh_from_db()
        assert row.status == "skipped"
    assert Delivery.objects.filter(kind="loan.returned").count() == 1


def test_calendar_view_normal_day_has_no_false_filter_errors(configured, client):
    _, r, _, _, user, s, _ = configured
    client.force_login(user)
    response = client.get(reverse("personal_calendar"), {"day": s.date().isoformat()})
    assert response.status_code == 200 and not response.context["chooser"].is_bound
    assert client.get(reverse("personal_calendar"), {"day": "bad-date"}).status_code == 404
