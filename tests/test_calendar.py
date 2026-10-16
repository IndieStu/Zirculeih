from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest
from bookings import services
from bookings.models import Booking, BookingPolicy, ScheduleException
from bookings.occupancy import Occupancy
from bookings.time_rules import local_instant
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from resources.calendar import calendar, midnight, validate_period
from test_bookings import configured as configured_fixture
from test_lending import lending_setup as lending_fixture

configured = configured_fixture
lending_setup = lending_fixture

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


def point(view, label):
    return next(p["value"] for p in view["data"]["points"] if p["label"] == label)


def test_month_starts_without_slot_cards_and_has_bounded_navigation(configured, client):
    _, resource, _, _, _, start, _ = configured
    view = calendar(resource)
    assert view["day"] is None and view["segments"] == []
    assert view["previous_month"] is None
    assert view["next_month"] == "2026-11"
    assert all(len(week) == 7 for week in view["weeks"])
    response = client.get(reverse("resource_detail", args=[resource.slug]))
    assert response.status_code == 200
    assert b"month-calendar" in response.content
    assert b"availability-slots" not in response.content
    assert b"Europe/Berlin" not in response.content
    assert "Belegung ohne persönliche Daten" not in response.content.decode()
    assert calendar(resource, month="9999-12")["month"].year == 2027
    assert calendar(resource, start.date().isoformat())["day"] == start.date()


@pytest.mark.parametrize("kind", ["room", "machine"])
def test_minimum_transition_blocks_both_sides_and_is_visual(configured, kind):
    actor, resource, _, policy, user, start, end = configured
    resource.type.key = kind
    resource.type.save(update_fields=["key"])
    assert policy.buffer_after_minutes == 30
    services.confirm(user, resource.pk, start, end, uuid4())
    assert (
        services.availability(
            user, resource.pk, end + timedelta(minutes=15), end + timedelta(minutes=45)
        ).code
        == "reserved"
    )
    assert (
        services.availability(
            user, resource.pk, end + timedelta(minutes=30), end + timedelta(minutes=60)
        ).code
        == "available"
    )
    assert (
        services.availability(
            user, resource.pk, start - timedelta(hours=1), start - timedelta(minutes=15)
        ).code
        == "reserved"
    )
    assert (
        services.availability(
            user, resource.pk, start - timedelta(hours=1), start - timedelta(minutes=30)
        ).code
        == "available"
    )
    view = calendar(resource, start.date().isoformat())
    assert {s["state"] for s in view["segments"]} >= {"available", "booked", "transition", "closed"}
    assert point(view, "11:15") not in view["data"]["starts"]
    assert point(view, "11:30") in view["data"]["starts"]
    assert point(view, "09:30") in view["data"]["ends"][str(point(view, "09:00"))]
    with pytest.raises(ValidationError):
        services.save_policy(actor, resource.pk, {"buffer_after_minutes": 29}, policy.revision)


def test_configurable_transition_and_legacy_claims_are_not_rewritten(configured):
    actor, resource, _, policy, user, start, end = configured
    # Reproduce an existing pre-correction promise with no stored transition.
    BookingPolicy.objects.filter(resource=resource).update(buffer_after_minutes=0)
    old = services.confirm(user, resource.pk, start, end, uuid4())
    before = old.claim.during
    policy.refresh_from_db()
    services.save_policy(actor, resource.pk, {"buffer_after_minutes": 45}, policy.revision)
    assert (
        services.availability(
            user, resource.pk, end + timedelta(minutes=30), end + timedelta(minutes=60)
        ).code
        == "reserved"
    )
    assert (
        services.availability(
            user, resource.pk, end + timedelta(minutes=45), end + timedelta(minutes=75)
        ).code
        == "available"
    )
    old.claim.refresh_from_db()
    assert old.claim.during == before
    view = calendar(resource, start.date().isoformat())
    assert point(view, "11:30") not in view["data"]["starts"]
    assert point(view, "11:45") in view["data"]["starts"]


def test_continuous_selection_max_duration_and_direct_server_gate(configured, client):
    actor, resource, _, policy, user, start, _ = configured
    services.save_policy(actor, resource.pk, {"max_duration_minutes": 120}, policy.revision)
    view = calendar(resource, start.date().isoformat())
    first = point(view, "14:00")
    assert max(view["data"]["ends"][str(first)]) == point(view, "16:00")
    url = reverse("calendar_select", args=[resource.slug])
    valid = {"start": start.replace(hour=14).isoformat(), "end": start.replace(hour=16).isoformat()}
    response = client.get(url, valid)
    assert (
        response.status_code == 302
        and reverse("booking_create", args=[resource.pk]) in response.url
    )
    assert not Booking.objects.exists()
    response = client.get(url, {**valid, "end": start.replace(hour=16, minute=15).isoformat()})
    assert response.status_code == 400
    assert b"Maximal 2 Stunden" in response.content
    with pytest.raises(ValidationError):
        services.confirm(
            user, resource.pk, start.replace(hour=14), start.replace(hour=16, minute=15), uuid4()
        )


def test_closures_usage_hours_blocks_grid_and_privacy(configured, client):
    actor, resource, _, policy, user, start, end = configured
    services.confirm(user, resource.pk, start, end, uuid4())
    services.set_block(
        actor,
        {
            "resource": resource,
            "start": local_instant(start.replace(hour=13), policy.timezone),
            "end": local_instant(start.replace(hour=14), policy.timezone),
            "reason": "Private internal maintenance note",
        },
    )
    view = calendar(resource, start.date().isoformat())
    assert any(s["state"] == "blocked" for s in view["segments"])
    for p in view["data"]["points"]:
        local = datetime.fromtimestamp(p["value"] / 1000, UTC).astimezone(
            __import__("zoneinfo").ZoneInfo(policy.timezone)
        )
        assert (local.hour * 60 + local.minute) % policy.granularity_minutes == 0
    assert point(view, "08:00") not in view["data"]["starts"]
    response = client.get(
        reverse("resource_detail", args=[resource.slug]), {"day": start.date().isoformat()}
    )
    assert user.email.encode() not in response.content
    assert b"Private internal maintenance note" not in response.content
    assert b"AllocationClaim" not in response.content
    ScheduleException.objects.create(
        organization=True, purpose="usage", date=start.date(), is_closed=True
    )
    closed = calendar(resource, start.date().isoformat())
    assert closed["data"]["starts"] == []
    assert not next(c for w in closed["weeks"] for c in w if c["date"] == start.date())["bookable"]


@pytest.mark.parametrize(
    "selected,hours,absent", [("2026-10-25", 25, False), ("2027-03-28", 23, True)]
)
def test_dst_timeline_uses_real_day_length_and_unambiguous_choices(
    configured, monkeypatch, selected, hours, absent
):
    actor, resource, _, policy, _, _, _ = configured
    day = datetime.fromisoformat(selected).date()
    monkeypatch.setattr(
        timezone, "now", lambda: datetime.combine(day - timedelta(days=2), time(8), UTC)
    )
    for purpose in ("usage", "access", "opening"):
        services.save_schedule(
            actor,
            {
                "resource": resource,
                "purpose": purpose,
                "weekday": day.weekday(),
                "start_time": time(0),
                "end_time": time(0),
                "end_next_day": True,
            },
        )
    view = calendar(resource, selected)
    assert view["data"]["dayEnd"] - view["data"]["dayStart"] == hours * 3600 * 1000
    labels = [p["label"] for p in view["data"]["points"]]
    if absent:
        assert not any(label.startswith("02:") for label in labels)
    else:
        assert "02:00 (früher)" in labels and "02:00 (später)" in labels


def test_day_based_range_retains_inclusive_dates_and_max_days(lending_setup, client):
    actor, resource, _, policy, _, start, _, _, _, _ = lending_setup
    services.save_policy(actor, resource.pk, {"time_mode": "days", "max_days": 7}, policy.revision)
    view = calendar(resource)
    assert view["days_mode"] and not view["segments"]
    ends = view["data"]["dateEnds"][start.date().isoformat()]
    assert ends[-1] == (start.date() + timedelta(days=6)).isoformat()
    response = client.get(reverse("resource_detail", args=[resource.slug]))
    assert b"calendar-start-date" in response.content
    assert b'id="day-timeline"' not in response.content
    response = client.get(
        reverse("calendar_select", args=[resource.slug]),
        {"start": start.date().isoformat(), "end": (start.date() + timedelta(days=7)).isoformat()},
    )
    assert response.status_code == 400


def test_projection_checks_one_continuous_unit_and_next_booking_padding(configured):
    actor, resource, unit, policy, user, start, end = configured
    from resources import services as resources

    other = resources.save_unit(actor, resource.pk, {"name": "Zweiter Platz"})
    services.confirm(user, resource.pk, start, end, uuid4(), unit_id=unit.pk)
    services.confirm(
        user,
        resource.pk,
        start + timedelta(hours=3),
        end + timedelta(hours=3),
        uuid4(),
        unit_id=other.pk,
    )
    snapshot = Occupancy(
        resource,
        policy,
        midnight(start.date(), policy),
        midnight(start.date() + timedelta(days=1), policy),
    )
    assert validate_period(snapshot, start, end + timedelta(hours=3)) is not None
    # Exact-range projections must also load a following promise just beyond end.
    close_start = start - timedelta(hours=1)
    close_end = start - timedelta(minutes=15)
    resources.save_unit(
        actor,
        resource.pk,
        {"name": other.name, "is_active": False},
        unit_id=other.pk,
        expected_revision=other.revision,
    )
    snapshot = Occupancy(
        resource,
        policy,
        local_instant(close_start, policy.timezone),
        local_instant(close_end, policy.timezone),
    )
    assert validate_period(snapshot, close_start, close_end) is not None


def test_completed_booking_keeps_transition_in_service_projection_and_database(
    configured, monkeypatch
):
    from bookings.models import AllocationClaim
    from django.db import IntegrityError, transaction
    from psycopg.types.range import Range

    _, resource, _, policy, user, start, end = configured
    original = services.confirm(user, resource.pk, start, end, uuid4())
    due = local_instant(end, policy.timezone)
    monkeypatch.setattr(timezone, "now", lambda: due + timedelta(minutes=1))
    services.advance_onsite_bookings()
    original.refresh_from_db()
    assert original.status == "completed" and not original.claim.is_active
    assert (
        services.availability(
            user, resource.pk, end + timedelta(minutes=15), end + timedelta(hours=1)
        ).code
        == "reserved"
    )
    view = calendar(resource, start.date().isoformat())
    assert any(row["state"] == "transition" for row in view["segments"])
    valid = services.confirm(
        user, resource.pk, end + timedelta(minutes=30), end + timedelta(hours=1), uuid4()
    )
    # Database integrity also rejects a forged direct write against completed history.
    with pytest.raises(IntegrityError), transaction.atomic():
        forged = Booking.objects.create(
            actor=user,
            beneficiary=user,
            resource=resource,
            unit=valid.unit,
            start=due + timedelta(minutes=15),
            end=due + timedelta(minutes=20),
            timezone=policy.timezone,
            policy_snapshot=services.policy_snapshot(policy),
            status="confirmed",
        )
        AllocationClaim.objects.create(
            booking=forged, unit=valid.unit, during=Range(forged.start, forged.end, "[)")
        )
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.django_db(transaction=True)
def test_concurrent_nonoverlapping_usage_cannot_share_transition(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    _, resource, _, _, user, start, end = configured
    barrier = Barrier(2)

    def attempt(offset):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            try:
                services.confirm(
                    user,
                    resource.pk,
                    start + timedelta(minutes=offset),
                    end + timedelta(minutes=offset),
                    uuid4(),
                )
                return "confirmed"
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [0, 75]))
    assert sorted(results) == ["confirmed", "conflict"]
    assert Booking.objects.count() == 1
