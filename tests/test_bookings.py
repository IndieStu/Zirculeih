from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from accounts.models import Grant, Group, Membership, User
from bookings import services
from bookings.models import AllocationClaim, Booking, BookingIncident, ScheduleWindow
from bookings.time_rules import interval, local_instant
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from psycopg.types.range import Range
from resources import services as resources

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture
def configured(staff, registry, monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 10, 15, 12, tzinfo=UTC))
    group = staff.membership_set.get(removed_at=None).group
    for action in (
        "resource.manage",
        "resource.publish",
        "resource.type_manage",
        "catalog.view_private",
        "booking.configure",
        "booking.block",
        "booking.read_all",
        "booking.manage_all",
        "booking.create_own",
        "booking.cancel_own",
    ):
        Grant.objects.create(group=group, action=action, effect="allow")
    kind = resources.save_type(staff, {"key": "room", "name": "Raum"})
    resource = resources.save_resource(
        staff,
        {
            "title": "Buchbarer Raum",
            "slug": "raum",
            "location": registry[1],
            "type": kind,
            "visibility": "public",
            "booking_enabled": True,
        },
    )
    unit = resources.save_unit(staff, resource.pk, {"name": "Raum"})
    resource = resources.publication(staff, resource.pk, resource.revision, "publish", "Reviewed")
    policy = services.save_policy(staff, resource.pk, {"use_mode": "onsite", "max_parallel": 20})
    for day in range(7):
        for purpose in ("usage", "access", "opening"):
            services.save_schedule(
                staff,
                {
                    "resource": resource,
                    "purpose": purpose,
                    "weekday": day,
                    "start_time": time(9),
                    "end_time": time(17),
                },
            )
    user = User.objects.create_user(
        "borrower@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name="Borrowers")
    Membership.objects.create(user=user, group=group)
    for action in ("booking.create_own", "booking.cancel_own"):
        Grant.objects.create(
            group=group,
            action=action,
            effect="allow",
            max_horizon_days=90 if action == "booking.create_own" else None,
        )
    start = (
        (timezone.now() + timedelta(days=7))
        .astimezone(ZoneInfo(policy.timezone))
        .replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=None)
    )
    return staff, resource, unit, policy, user, start, start + timedelta(hours=1)


def book(c, **kwargs):
    _, r, _, _, user, s, e = c
    return services.confirm(user, r.pk, s, e, uuid4(), **kwargs)


def test_confirm_claim_and_adjacent_intervals(configured):
    _, r, u, _, user, s, e = configured
    first = book(configured)
    assert first.status == "confirmed" and first.unit_id == u.pk
    assert first.claim.during.lower == local_instant(s, "Europe/Berlin")
    assert services.availability(user, r.pk, s, e).code == "reserved"
    assert services.availability(user, r.pk, e, e + timedelta(hours=1)).code == "reserved"
    second = services.confirm(
        user, r.pk, e + timedelta(minutes=30), e + timedelta(minutes=90), uuid4()
    )
    assert second.pk != first.pk and AllocationClaim.objects.filter(is_active=True).count() == 2


def test_idempotency_retry_and_changed_payload(configured):
    _, r, _, _, user, s, e = configured
    key = uuid4()
    a = services.confirm(user, r.pk, s, e, key)
    assert services.confirm(user, r.pk, s, e, key).pk == a.pk
    with pytest.raises(ValidationError):
        services.confirm(user, r.pk, s, e + timedelta(hours=1), key)
    assert Booking.objects.count() == 1


def test_cancel_releases_claim_and_preserves_history(configured):
    _, r, _, _, user, s, e = configured
    row = book(configured)
    services.cancel(user, row.pk, row.revision, "Plan geändert")
    row.refresh_from_db()
    assert row.status == "cancelled" and not row.claim.is_active
    assert services.availability(user, r.pk, s, e).code == "available"
    with pytest.raises(ValidationError):
        services.cancel(user, row.pk, row.revision, "Again")
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=row.pk).update(status="confirmed")


def test_grant_horizons_and_complete_profiles(configured):
    _, r, _, _, user, s, _ = configured
    group = user.membership_set.get(removed_at=None).group
    Grant.objects.filter(group=group, action="booking.create_own").delete()
    Grant.objects.create(
        group=group,
        action="booking.create_own",
        effect="allow",
        max_horizon_days=90,
        max_duration_minutes=120,
    )
    Grant.objects.create(
        group=group,
        action="booking.create_own",
        effect="allow",
        max_horizon_days=30,
        max_duration_minutes=480,
    )
    s = s + timedelta(days=55)
    assert services.availability(user, r.pk, s, s + timedelta(hours=1)).code == "available"
    assert services.availability(user, r.pk, s, s + timedelta(hours=6)).code == "permission_denied"
    Grant.objects.create(
        group=group,
        action="booking.create_own",
        effect="deny",
        scope_kind="resource",
        scope_id=r.pk,
    )
    assert services.availability(user, r.pk, s, s + timedelta(hours=1)).code == "permission_denied"


def test_unstaffed_does_not_bypass_usage_access_or_closure(configured):
    actor, r, _, p, user, s, e = configured
    ScheduleWindow.objects.filter(resource=r, purpose="opening").delete()
    assert services.availability(user, r.pk, s, e).code == "outside_staffed_hours"
    group = user.membership_set.get(removed_at=None).group
    Grant.objects.create(
        group=group,
        action="resource.use_unstaffed",
        effect="allow",
        scope_kind="resource",
        scope_id=r.pk,
    )
    assert services.availability(user, r.pk, s, e).code == "available"
    assert (
        services.availability(user, r.pk, s.replace(hour=8), s.replace(hour=9)).code
        == "outside_usage_hours"
    )
    services.set_block(
        actor,
        {
            "resource": r,
            "start": local_instant(s, p.timezone),
            "end": local_instant(e, p.timezone),
            "reason": "Hard closure",
        },
    )
    assert services.availability(user, r.pk, s, e).code == "hard_block"


def test_exception_preserves_existing_booking_and_marks_incident(configured):
    actor, r, _, _, user, s, e = configured
    row = book(configured)
    services.save_schedule(
        actor,
        {"resource": r, "purpose": "usage", "date": s.date(), "is_closed": True},
        exception=True,
    )
    assert services.availability(user, r.pk, s, e).code == "outside_usage_hours"
    row.refresh_from_db()
    assert row.status == "confirmed" and row.claim.is_active
    assert BookingIncident.objects.filter(booking=row, code="schedule_changed").exists()


def test_hard_location_block_wins_and_does_not_delete_claim(configured, registry):
    actor, r, _, p, user, s, e = configured
    row = book(configured)
    block = services.set_block(
        actor,
        {
            "location": registry[0],
            "start": local_instant(s, p.timezone),
            "end": local_instant(e, p.timezone),
            "reason": "Building closed",
        },
    )
    assert row.claim.is_active and row.incidents.filter(code="hard_block").exists()
    assert services.availability(user, r.pk, s, e).code == "hard_block"
    services.lift_block(actor, block.pk, block.revision, "Resolved")
    assert services.availability(user, r.pk, s, e).code == "reserved"


def test_dst_gap_fold_and_day_semantics():
    with pytest.raises(ValidationError):
        local_instant(datetime(2027, 3, 28, 2, 30), "Europe/Berlin")
    ambiguous = datetime(2026, 10, 25, 2, 30)
    with pytest.raises(ValidationError):
        local_instant(ambiguous, "Europe/Berlin")
    a = local_instant(ambiguous, "Europe/Berlin", 0)
    b = local_instant(ambiguous, "Europe/Berlin", 1)
    assert b - a == timedelta(hours=1)
    from bookings.models import BookingPolicy

    policy = BookingPolicy(time_mode="days", timezone="Europe/Berlin")
    s, e, minutes, d1, d2 = interval(policy, date(2027, 3, 27), date(2027, 3, 29))
    assert (d2 - d1).days == 3 and minutes == 3 * 1440 and e - s == timedelta(hours=71)


def test_selected_dst_fold_is_used_in_confirmation(configured):
    actor, r, _, p, user, _, _ = configured
    ScheduleWindow.objects.filter(resource=r).delete()
    for purpose in ("usage", "opening", "access"):
        services.save_schedule(
            actor,
            {
                "resource": r,
                "purpose": purpose,
                "weekday": 6,
                "start_time": time(0),
                "end_time": time(0),
                "end_next_day": True,
            },
        )
    s = datetime(2026, 10, 25, 2, 15)
    e = datetime(2026, 10, 25, 2, 45)
    row = services.confirm(user, r.pk, s, e, uuid4(), start_fold=1, end_fold=1)
    assert row.start == local_instant(s, p.timezone, 1)
    assert row.end - row.start == timedelta(minutes=30)


def test_loan_and_qualification_gates_fail_closed(configured):
    actor, r, _, p, user, s, e = configured
    p = services.save_policy(actor, r.pk, {"use_mode": "physical_loan"}, p.revision)
    assert services.availability(user, r.pk, s, e).code == "lending_setup_required"
    with pytest.raises(ValidationError):
        book(configured)
    p = services.save_policy(
        actor, r.pk, {"use_mode": "onsite", "requires_qualification": True}, p.revision
    )
    assert services.availability(user, r.pk, s, e).code == "qualification_required"
    p = services.save_policy(
        actor, r.pk, {"requires_qualification": False, "requires_agreement": True}, p.revision
    )
    assert services.availability(user, r.pk, s, e).code == "agreement_required"
    assert not Booking.objects.exists()


def test_cross_resource_parallel_limit_and_actor_beneficiary(configured):
    actor, r, _, p, user, s, e = configured
    services.save_policy(actor, r.pk, {"max_parallel": 1}, p.revision)
    book(configured)
    assert services.availability(user, r.pk, s, e).code == "parallel_limit"
    with pytest.raises(ValidationError):
        services.confirm(actor, r.pk, s, e, uuid4(), beneficiary=user)


def test_direct_database_overlap_and_unit_claim_identity(configured):
    _, _, unit, _, _, _, _ = configured
    row = book(configured)
    with pytest.raises(IntegrityError), transaction.atomic():
        AllocationClaim.objects.filter(pk=row.claim.pk).update(
            during=(row.start, row.end + timedelta(hours=1))
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        AllocationClaim.objects.filter(pk=row.claim.pk).update(
            during=Range(row.start, row.end, "[]")
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=row.pk).update(start=row.start - timedelta(minutes=15))
    with pytest.raises(IntegrityError), transaction.atomic():
        row.claim.delete()


@pytest.mark.django_db(transaction=True)
def test_twenty_concurrent_requests_have_exactly_one_winner(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    _, r, _, _, user, s, e = configured
    barrier = Barrier(20)

    def attempt(_):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            try:
                return str(services.confirm(user, r.pk, s, e, uuid4()).pk)
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(attempt, range(20)))
    assert results.count("conflict") == 19
    assert (
        Booking.objects.count() == 1 and AllocationClaim.objects.filter(is_active=True).count() == 1
    )


def test_ui_preview_confirmation_retry_and_owner_detail(configured, client):
    from django.urls import reverse

    _, r, _, _, user, s, e = configured
    client.force_login(user)
    url = reverse("booking_create", args=[r.pk])
    response = client.get(url)
    assert response.status_code == 200
    key = uuid4()
    data = {"start": s.isoformat(), "end": e.isoformat(), "key": key, "action": "preview"}
    response = client.post(url, data)
    assert response.status_code == 200 and response.context["result"].code == "available"
    assert b"Reservieren" in response.content and not Booking.objects.exists()
    response = client.post(url, {**data, "action": "confirm"})
    assert response.status_code == 302
    assert client.post(url, {**data, "action": "confirm"}).url == response.url
    assert client.get(response.url).status_code == 200
    assert Booking.objects.count() == 1
    assert client.get(reverse("own_bookings")).context["page_obj"].paginator.count == 1
    booking = Booking.objects.get()
    assert (
        client.post(
            reverse("booking_cancel", args=[booking.pk]),
            {"revision": booking.revision, "reason": "Changed"},
        ).status_code
        == 302
    )


def test_booking_idor_and_csrf(configured, client):
    from django.test import Client
    from django.urls import reverse

    _, r, _, _, user, s, e = configured
    booking = book(configured)
    outsider = User.objects.create_user(
        "outsider@example.test",
        "Quiet-River-8941!Cloud",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    client.force_login(outsider)
    assert client.get(reverse("booking_detail", args=[booking.pk])).status_code == 404
    assert client.get(reverse("booking_operations")).status_code == 404
    assert client.get(reverse("own_bookings")).context["page_obj"].paginator.count == 0
    secure = Client(enforce_csrf_checks=True)
    secure.force_login(user)
    assert (
        secure.post(
            reverse("booking_create", args=[r.pk]),
            {"start": s.isoformat(), "end": e.isoformat(), "key": uuid4(), "action": "confirm"},
        ).status_code
        == 403
    )
    assert (
        secure.get(reverse("booking_detail", args=[booking.pk]))["Cache-Control"]
        == "no-store, private"
    )


def test_operational_configuration_forms_and_scopes(configured, registry, client):
    from django.urls import reverse

    actor, r, _, _, user, s, e = configured
    client.force_login(actor)
    for name in ("booking_operations", "schedule_add", "schedule_exception_add", "booking_block"):
        response = client.get(reverse(name))
        assert response.status_code == 200
    assert client.get(reverse("booking_policy", args=[r.pk])).status_code == 200
    response = client.post(
        reverse("schedule_exception_add"),
        {"resource": r.pk, "purpose": "usage", "date": s.date().isoformat(), "is_closed": "on"},
    )
    assert response.status_code == 302
    assert (
        client.post(
            reverse("booking_block"),
            {
                "resource": r.pk,
                "local_start": s.isoformat(),
                "local_end": e.isoformat(),
                "timezone_name": "Europe/Berlin",
                "reason": "Test closure",
            },
        ).status_code
        == 302
    )
    assert client.get(reverse("booking_operations")).status_code == 200
    client.force_login(user)
    assert client.get(reverse("booking_policy", args=[r.pk])).status_code == 404
    assert client.get(reverse("schedule_add")).status_code == 404


def test_current_permission_and_suspension_rechecked_before_commit(configured):
    _, r, _, _, user, s, e = configured
    assert services.availability(user, r.pk, s, e).code == "available"
    Grant.objects.filter(group__membership__user=user, action="booking.create_own").delete()
    with pytest.raises(ValidationError):
        book(configured)
    user.is_active = False
    user.save()
    with pytest.raises(PermissionDenied):
        book(configured)
    assert not Booking.objects.exists()


def test_buffers_and_granularity(configured):
    actor, r, _, p, user, s, e = configured
    services.save_policy(actor, r.pk, {"buffer_after_minutes": 45}, p.revision)
    book(configured)
    assert services.availability(user, r.pk, e, e + timedelta(hours=1)).code == "reserved"
    assert (
        services.availability(
            user, r.pk, e + timedelta(minutes=45), e + timedelta(minutes=105)
        ).code
        == "available"
    )
    assert (
        services.availability(user, r.pk, s + timedelta(minutes=1), e + timedelta(minutes=1)).code
        == "granularity_not_allowed"
    )


def test_building_schedule_is_intersected_with_resource_windows(configured, registry):
    actor, r, _, _, user, s, e = configured
    services.save_schedule(
        actor,
        {
            "location": registry[0],
            "purpose": "access",
            "weekday": s.weekday(),
            "start_time": time(12),
            "end_time": time(16),
        },
    )
    assert services.availability(user, r.pk, s, e).code == "outside_access_hours"
    assert (
        services.availability(user, r.pk, s.replace(hour=12), e.replace(hour=13)).code
        == "available"
    )


def test_closed_exception_cuts_overnight_carry_over(configured):
    actor, r, _, _, user, s, e = configured
    ScheduleWindow.objects.filter(resource=r, purpose="usage").delete()
    previous = (s.date() - timedelta(days=1)).weekday()
    services.save_schedule(
        actor,
        {
            "resource": r,
            "purpose": "usage",
            "weekday": previous,
            "start_time": time(22),
            "end_time": time(12),
            "end_next_day": True,
        },
    )
    assert services.availability(user, r.pk, s, e).code == "available"
    services.save_schedule(
        actor,
        {"resource": r, "purpose": "usage", "date": s.date(), "is_closed": True},
        exception=True,
    )
    assert services.availability(user, r.pk, s, e).code == "outside_usage_hours"


def test_direct_sql_exclusion_and_deferred_missing_claim(configured):
    actor, r, u, _, user, s, e = configured
    row = book(configured)
    data = {
        "actor": actor,
        "beneficiary": user,
        "resource": r,
        "unit": u,
        "start": row.start,
        "end": row.end,
        "timezone": row.timezone,
        "policy_snapshot": row.policy_snapshot,
    }
    with pytest.raises(IntegrityError), transaction.atomic():
        other = Booking.objects.create(**data)
        AllocationClaim.objects.create(
            booking=other, unit=u, during=Range(row.start, row.end, "[)")
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.create(**{**data, "start": row.end, "end": row.end + timedelta(hours=1)})
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS booking_claim_consistent IMMEDIATE")
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")


def test_calendar_day_confirmation_across_dst_without_seconds_arithmetic(configured):
    actor, r, _, p, user, _, _ = configured
    p = services.save_policy(
        actor, r.pk, {"time_mode": "days", "max_horizon_days": 366}, p.revision
    )
    group = user.membership_set.get(removed_at=None).group
    Grant.objects.filter(group=group, action="booking.create_own").update(max_horizon_days=366)
    ScheduleWindow.objects.filter(resource=r).delete()
    for day in range(7):
        for purpose in ("usage", "access", "opening"):
            services.save_schedule(
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
    row = services.confirm(user, r.pk, date(2027, 3, 27), date(2027, 3, 29), uuid4())
    assert row.end_date_exclusive == date(2027, 3, 30)
    assert row.end - row.start == timedelta(hours=71)


def test_incidents_after_resource_or_asset_change_and_resolution(configured, registry):
    actor, r, unit, _, _, _, _ = configured
    row = book(configured)
    resources.save_unit(
        actor, r.pk, {"is_active": False}, unit_id=unit.pk, expected_revision=unit.revision
    )
    incident = row.incidents.get(is_open=True)
    assert row.claim.is_active
    services.resolve_incident(actor, incident.pk, "Unit restored and confirmed with team")
    assert not row.incidents.filter(is_open=True).exists()


def test_onsite_state_job_never_records_loan_or_return(configured):
    from unittest.mock import patch

    _, _, _, _, _, _, _ = configured
    row = book(configured)
    with patch("bookings.services.timezone.now", return_value=row.start + timedelta(minutes=5)):
        assert services.advance_onsite_bookings() == 1
    row.refresh_from_db()
    assert row.status == "active" and row.claim.is_active
    with patch("bookings.services.timezone.now", return_value=row.end + timedelta(minutes=5)):
        assert services.advance_onsite_bookings() == 1
    row.refresh_from_db()
    assert row.status == "completed" and not row.claim.is_active


def test_pickup_and_return_schedules_do_not_restrict_onsite_usage(configured):
    actor, r, _, _, user, s, e = configured
    for purpose in ("pickup", "return"):
        services.save_schedule(
            actor,
            {"resource": r, "purpose": purpose, "date": s.date(), "is_closed": True},
            exception=True,
        )
    assert services.availability(user, r.pk, s, e).code == "available"


def test_bare_admin_and_private_unknown_resource_do_not_bypass_booking(configured):
    _, r, _, _, user, s, e = configured
    admin = User.objects.create_user(
        "bare-admin@example.test",
        "Quiet-River-8941!Cloud",
        is_system_admin=True,
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    assert services.availability(admin, r.pk, s, e).code == "permission_denied"
    r.visibility = "private"
    r.save()
    assert services.availability(user, r.pk, s, e).code == "permission_denied"
    assert services.availability(user, uuid4(), s, e).code == "permission_denied"
    with pytest.raises(PermissionDenied):
        book(configured)


def test_claim_unbounded_or_infinite_ranges_rejected_by_database(configured):
    actor, r, u, _, user, _, _ = configured
    row = book(configured)
    for during in (Range(None, None, "[)"), Range(row.end, row.end, "[)")):
        with pytest.raises(IntegrityError), transaction.atomic():
            other = Booking.objects.create(
                actor=actor,
                beneficiary=user,
                resource=r,
                unit=u,
                start=row.end,
                end=row.end + timedelta(hours=1),
                timezone=row.timezone,
                policy_snapshot=row.policy_snapshot,
            )
            AllocationClaim.objects.create(booking=other, unit=u, during=during)
    with pytest.raises(IntegrityError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE bookings_allocationclaim "
                "SET during='[-infinity,infinity)'::tstzrange WHERE booking_id=%s",
                [row.pk],
            )


def test_stale_cancel_and_scoped_operational_dashboard(configured, client):
    from django.urls import reverse

    actor, r, _, _, user, _, _ = configured
    row = book(configured)
    with pytest.raises(ValidationError):
        services.cancel(user, row.pk, row.revision + 1, "Stale")
    client.force_login(user)
    assert client.get(reverse("inventory_dashboard")).status_code == 302
    client.force_login(actor)
    response = client.get(reverse("inventory_dashboard"))
    assert response.status_code == 200 and b"Buchungen pr" in response.content
    Grant.objects.filter(group__membership__user=actor, action="booking.read_all").delete()
    assert not services.visible_bookings(actor, operational=True).exists()


def test_schedule_owner_and_time_limit_mass_assignment(configured, registry):
    actor, r, _, p, _, s, e = configured
    with pytest.raises(ValidationError):
        services.save_schedule(
            actor,
            {
                "resource": r,
                "location": registry[0],
                "purpose": "usage",
                "weekday": 1,
                "start_time": time(9),
                "end_time": time(17),
            },
        )
    with pytest.raises(ValidationError):
        services.save_policy(actor, r.pk, {"max_horizon_days": 3661}, p.revision)
    with pytest.raises(ValidationError):
        services.save_schedule(
            actor,
            {
                "resource": r,
                "purpose": "usage",
                "weekday": 1,
                "start_time": time(9),
                "end_time": time(17),
                "end_next_day": True,
            },
        )


@pytest.mark.django_db(transaction=True)
def test_parallel_idempotency_retries_return_one_booking(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    _, r, _, _, user, s, e = configured
    key, barrier = uuid4(), Barrier(4)

    def attempt(_):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            return services.confirm(user, r.pk, s, e, key).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert len(set(results)) == 1 and Booking.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_block_and_confirmation_race_retains_or_prevents_promise(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    actor, r, _, _, user, s, e = configured
    barrier = Barrier(2)

    def attempt(kind):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            if kind == "block":
                services.set_block(
                    actor,
                    {
                        "resource": r,
                        "start": local_instant(s, "Europe/Berlin"),
                        "end": local_instant(e, "Europe/Berlin"),
                        "reason": "Synthetic closure",
                    },
                )
                return "blocked"
            try:
                return services.confirm(user, r.pk, s, e, uuid4()).pk
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(attempt, ("block", "confirm")))
    assert services.availability(user, r.pk, s, e).code == "hard_block"
    assert Booking.objects.count() <= 1
    assert (
        BookingIncident.objects.filter(code="hard_block", is_open=True).count()
        == Booking.objects.count()
    )


def test_policy_post_and_malformed_exception_are_safe(configured, client):
    from django.forms.models import model_to_dict
    from django.urls import reverse

    actor, r, _, policy, _, _, _ = configured
    client.force_login(actor)
    payload = model_to_dict(policy, exclude=["resource", "revision"])
    payload.update(expected_revision=policy.revision, max_parallel=7)
    response = client.post(reverse("booking_policy", args=[r.pk]), payload)
    assert response.status_code == 302
    policy.refresh_from_db()
    assert policy.max_parallel == 7
    with pytest.raises(ValidationError):
        services.save_schedule(
            actor,
            {
                "resource": r,
                "purpose": "usage",
                "date": date(2026, 10, 22),
                "is_closed": True,
                "end_next_day": True,
            },
            exception=True,
        )
    with pytest.raises(ValidationError):
        services.save_policy(actor, r.pk, {"buffer_after_minutes": 10**9}, policy.revision)


def test_extreme_calendar_input_returns_validation_error(configured):
    _, _, _, policy, _, _, _ = configured
    policy.time_mode = "days"
    with pytest.raises(ValidationError):
        interval(policy, date(9999, 12, 31), date(9999, 12, 31))
    with pytest.raises(ValidationError):
        local_instant(datetime(1, 1, 1), "Europe/Berlin")


@pytest.mark.parametrize(
    "agreement_required,qualification_required",
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_resource_requirements_enforced_without_ui(
    configured, agreement_required, qualification_required
):
    from lending import agreements
    from lending.models import Acceptance
    from resources import requirements
    from resources.models import UserQualification

    staff, resource, _, _, user, start, end = configured
    group = staff.membership_set.get(removed_at=None).group
    for action in (
        "agreement.edit",
        "agreement.publish",
        "agreement.assign",
        "qualification.issue",
    ):
        Grant.objects.create(group=group, action=action, effect="allow")
    text = agreements.create_agreement(staff, "Besondere Nutzung", "additional")
    version = agreements.save_version(staff, text.pk, "Gültiger Text 1")
    agreements.publish_version(staff, version.pk)
    qualification = requirements.create_type(staff, "Einweisung Maschine")
    requirements.configure(
        staff,
        resource.pk,
        [text.pk] if agreement_required else [],
        [qualification.pk] if qualification_required else [],
    )
    code = (
        "qualification_required"
        if qualification_required
        else "agreement_required"
        if agreement_required
        else "available"
    )
    assert services.availability(user, resource.pk, start, end).code == code
    if code != "available":
        with pytest.raises(ValidationError):
            services.confirm(user, resource.pk, start, end, uuid4())
        assert not Booking.objects.exists()
    if qualification_required:
        with pytest.raises(PermissionDenied):
            requirements.issue(user, user.pk, qualification.pk)
        evidence = requirements.issue(staff, user.pk, qualification.pk)
        assert requirements.issue(staff, user.pk, qualification.pk).pk == evidence.pk
        with pytest.raises(IntegrityError), transaction.atomic():
            UserQualification.objects.filter(pk=evidence.pk).update(note="Changed")
    if agreement_required:
        agreements.accept(user, [version.pk])
        agreements.accept(user, [version.pk])
        assert Acceptance.objects.filter(user=user, version=version).count() == 1
        newer = agreements.save_version(staff, text.pk, "Gültiger Text 2")
        agreements.publish_version(staff, newer.pk)
        assert services.availability(user, resource.pk, start, end).code == "agreement_required"
        assert Acceptance.objects.filter(user=user, version=version).exists()
        agreements.accept(user, [newer.pk])
    assert services.confirm(user, resource.pk, start, end, uuid4()).status == "confirmed"


def test_anonymous_calendar_capacity_and_privacy(configured, client):
    from resources.calendar import calendar

    _, resource, _, _, user, start, end = configured
    before = calendar(resource, start.date().isoformat())
    instant = next(p["value"] for p in before["data"]["points"] if p["label"] == "10:00")
    assert instant in before["data"]["starts"]
    services.confirm(user, resource.pk, start, end, uuid4())
    after = calendar(resource, start.date().isoformat())
    assert instant not in after["data"]["starts"]
    response = client.get(f"/entdecken/{resource.slug}/", {"day": start.date().isoformat()})
    assert response.status_code == 200
    assert user.email.encode() not in response.content
    assert b"Verf" in response.content


def test_booking_form_dst_only_when_needed(configured):
    from bookings.forms import BookingForm
    from django.forms import HiddenInput, Select

    _, _, _, policy, _, _, _ = configured
    ordinary = BookingForm(
        policy, {"start": "2026-10-22T10:00", "end": "2026-10-22T11:00", "key": uuid4()}
    )
    assert isinstance(ordinary.fields["start_fold"].widget, HiddenInput)
    assert ordinary.is_valid()
    repeated = BookingForm(
        policy, {"start": "2026-10-25T02:00", "end": "2026-10-25T03:00", "key": uuid4()}
    )
    assert isinstance(repeated.fields["start_fold"].widget, Select)
    assert not repeated.is_valid()
    skipped = BookingForm(
        policy, {"start": "2027-03-28T02:00", "end": "2027-03-28T03:00", "key": uuid4()}
    )
    assert isinstance(skipped.fields["start_fold"].widget, HiddenInput)
    assert not skipped.is_valid()
    assert skipped.errors.as_data()["start"][0].code == "nonexistent_time"


def test_organization_category_closures_intersect_resource_hours(configured):
    _, resource, _, policy, _, start, end = configured
    from bookings import schedules
    from bookings.models import ScheduleException

    a = local_instant(start, policy.timezone)
    b = local_instant(end, policy.timezone)
    assert schedules.covers(resource, policy, "usage", a, b)
    ScheduleException.objects.create(
        organization=True, purpose="usage", date=start.date(), is_closed=True
    )
    assert not schedules.covers(resource, policy, "usage", a, b)
    assert schedules.covers(resource, policy, "usage", a + timedelta(days=1), b + timedelta(days=1))


def test_hours_admin_filters_paginates_and_checks_permission(configured, client):
    actor, resource, _, _, user, _, _ = configured
    for weekday in range(7):
        for purpose in ("usage", "access", "opening"):
            services.save_schedule(
                actor,
                {
                    "organization": True,
                    "purpose": purpose,
                    "weekday": weekday,
                    "start_time": time(9),
                    "end_time": time(17),
                },
            )
    client.force_login(actor)
    response = client.get("/buchungen/betrieb/zeiten/")
    assert response.status_code == 200
    assert response.context["windows"].paginator.count == 42
    assert len(response.context["windows"]) == 30
    response = client.get(
        "/buchungen/betrieb/zeiten/", {"owner": "resource:" + str(resource.pk), "purpose": "usage"}
    )
    assert response.context["windows"].paginator.count == 7
    assert all(row.resource_id == resource.pk for row in response.context["windows"])
    client.force_login(user)
    assert client.get("/buchungen/betrieb/zeiten/").status_code == 404
