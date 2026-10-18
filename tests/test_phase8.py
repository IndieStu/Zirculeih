from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from accounts.models import AuditEvent, Grant, User
from bookings import recurrence, services
from bookings.models import AllocationClaim, Booking, ReservationRequest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from test_bookings import configured as configured_fixture
from test_lending import lending_setup as lending_fixture
from test_phase7 import component

configured = configured_fixture
lending_setup = lending_fixture
pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture
def setup(configured):
    staff, r, u, p, user, s, e = configured
    for owner, actions in (
        (staff, ("booking.approve", "booking.create_for_others", "booking.request_recurrence")),
        (user, ("booking.request_recurrence",)),
    ):
        group = owner.membership_set.get(removed_at=None).group
        for action in actions:
            Grant.objects.create(group=group, action=action, effect="allow")
    return configured


def request(c, count=8, **kwargs):
    _, r, _, _, user, s, e = c
    return recurrence.submit(
        user, r.pk, s, e, uuid4(), weekdays=[s.weekday()], count=count, **kwargs
    )


def test_ac10_nonblocking_atomic_eight_and_single_exception(setup):
    staff, _, _, _, user, _, _ = setup
    proposal = request(setup)
    assert proposal.occurrences.count() == 8
    assert not Booking.objects.exists() and not AllocationClaim.objects.exists()
    preview = recurrence.preview(staff, proposal.pk)
    assert all(r["code"] == "available" for r in preview)
    assert not Booking.objects.exists() and not AllocationClaim.objects.exists()
    recurrence.approve(staff, proposal.pk, 1, "Alle Termine geprüft")
    proposal.refresh_from_db()
    assert proposal.status == "approved" and Booking.objects.count() == 8
    assert set(Booking.objects.values_list("actor_id", flat=True)) == {staff.pk}
    assert set(Booking.objects.values_list("beneficiary_id", flat=True)) == {user.pk}
    row = proposal.occurrences.first()
    recurrence.exception(user, row.pk, row.booking.revision, "Ein Termin entfällt")
    assert AllocationClaim.objects.filter(is_active=True).count() == 7
    assert recurrence.current_booking(row) is None
    assert proposal.occurrences.count() == 8


def test_ac23_all_conflicts_no_partial_commit(setup):
    staff, r, _, _, user, s, e = setup
    proposal = request(setup)
    services.confirm(user, r.pk, s + timedelta(weeks=2), e + timedelta(weeks=2), uuid4())
    services.confirm(user, r.pk, s + timedelta(weeks=5), e + timedelta(weeks=5), uuid4())
    with pytest.raises(recurrence.Conflicts) as caught:
        recurrence.approve(staff, proposal.pk, 1, "Prüfung")
    assert len([r for r in caught.value.rows if r["code"] != "available"]) == 2
    assert (
        Booking.objects.count() == 2
        and not proposal.occurrences.filter(booking__isnull=False).exists()
    )
    proposal.refresh_from_db()
    assert proposal.status == "requested"


def test_current_permissions_suspend_and_employee_marker(setup):
    staff, _, _, _, user, _, _ = setup
    proposal = request(setup, count=2)
    staff.is_employee = True
    staff.save()
    Grant.objects.filter(group__membership__user=staff, action="booking.approve").delete()
    with pytest.raises(PermissionDenied):
        recurrence.approve(staff, proposal.pk, 1, "Kein Recht")
    assert not Booking.objects.exists()
    group = staff.membership_set.get(removed_at=None).group
    Grant.objects.create(group=group, action="booking.approve", effect="allow")
    user.is_active = False
    user.save()
    with pytest.raises(PermissionDenied):
        recurrence.approve(staff, proposal.pk, 1, "Gesperrt")
    assert not Booking.objects.exists()


def test_manual_single_requires_approval_and_no_private_flag_bypass(setup):
    staff, r, _, p, user, s, e = setup
    services.save_policy(staff, r.pk, {"approval_mode": "manual"}, p.revision)
    with pytest.raises(PermissionDenied):
        services.confirm(user, r.pk, s, e, uuid4(), approval=True)
    with pytest.raises(ValidationError):
        services.confirm(staff, r.pk, s, e, uuid4())
    proposal = recurrence.submit(user, r.pk, s, e, uuid4())
    assert not Booking.objects.exists()
    recurrence.approve(staff, proposal.pk, 1, "Einzelantrag genehmigt")
    assert Booking.objects.count() == 1


def test_idempotent_submit_approve_and_stale_reject(setup):
    staff, r, _, _, user, s, e = setup
    key = uuid4()
    proposal = recurrence.submit(user, r.pk, s, e, key)
    assert recurrence.submit(user, r.pk, s, e, key).pk == proposal.pk
    with pytest.raises(ValidationError):
        recurrence.submit(user, r.pk, s, e + timedelta(hours=1), key)
    recurrence.approve(staff, proposal.pk, 1, "OK")
    recurrence.approve(staff, proposal.pk, 1, "OK")
    assert Booking.objects.count() == 1
    with pytest.raises(ValidationError):
        recurrence.reject(staff, proposal.pk, 1, "Veraltet")


def test_configurable_cap_and_bounded_rule(setup):
    staff, r, _, p, _, s, e = setup
    services.save_policy(staff, r.pk, {"max_occurrences": 2}, p.revision)
    with pytest.raises(ValidationError):
        request(setup, count=3)
    assert not ReservationRequest.objects.exists()
    for kwargs in (
        {"weekdays": [s.weekday()]},
        {"weekdays": [7], "count": 2},
        {"weekdays": [s.weekday()], "count": 0},
        {"weekdays": [s.weekday()], "count": 2, "until": s.date()},
    ):
        with pytest.raises(ValidationError):
            recurrence.expand(s, e, **kwargs)
    assert (
        len(recurrence.expand(s, e, weekdays=[s.weekday()], until=(s + timedelta(weeks=1)).date()))
        == 2
    )


def test_dst_local_wall_time_not_utc_week(setup):
    staff, r, _, _, _, s, e = setup
    proposal = request(setup, count=3)
    recurrence.approve(staff, proposal.pk, 1, "DST geprüft")
    bookings = list(Booking.objects.order_by("start"))
    assert bookings[1].start - bookings[0].start == timedelta(hours=169)
    assert all(b.start.astimezone(recurrence.zone(b.timezone)).hour == 10 for b in bookings)
    with pytest.raises(ValidationError):
        recurrence.expand(
            datetime(9999, 12, 30, 10), datetime(9999, 12, 30, 11), weekdays=[0], count=2
        )


def test_occurrence_move_conflict_rolls_back_original(setup):
    staff, r, _, _, user, s, e = setup
    proposal = request(setup, count=2)
    recurrence.approve(staff, proposal.pk, 1, "Geprüft")
    row = proposal.occurrences.first()
    old = row.booking
    with pytest.raises(ValidationError):
        recurrence.exception(
            staff,
            row.pk,
            old.revision,
            "Kollision",
            start=s + timedelta(weeks=1),
            end=e + timedelta(weeks=1),
        )
    old.refresh_from_db()
    assert old.status == "confirmed" and old.claim.is_active
    change = recurrence.exception(
        staff,
        row.pk,
        old.revision,
        "Verschieben",
        start=s + timedelta(hours=2),
        end=e + timedelta(hours=2),
    )
    assert change.replacement.status == "confirmed"
    assert recurrence.current_booking(row).pk == change.replacement_id
    assert (
        Booking.objects.count() == 3 and AllocationClaim.objects.filter(is_active=True).count() == 2
    )
    with pytest.raises(PermissionDenied):
        recurrence.exception(
            user, row.pk, change.replacement.revision, "Ohne Freigaberecht", start=s, end=e
        )


def test_bundle_series_and_component_approval_scope(setup):
    from resources import bundles

    staff, r, _, _, user, s, e = setup
    child = component(setup)
    bundles.configure(staff, r.pk, [(child, True)], r.revision)
    proposal = request(setup, count=2)
    group = staff.membership_set.get(removed_at=None).group
    deny = Grant.objects.create(
        group=group,
        action="booking.approve",
        effect="deny",
        scope_kind="resource",
        scope_id=child.pk,
    )
    assert not recurrence.visible(staff, queue=True).exists()
    with pytest.raises(PermissionDenied):
        recurrence.approve(staff, proposal.pk, 1, "Verbot")
    deny.delete()
    recurrence.approve(staff, proposal.pk, 1, "Bundle geprüft")
    assert Booking.objects.count() == 4
    recurrence.withdraw(user, proposal.pk, 2, "Alles entfällt")
    assert not AllocationClaim.objects.filter(is_active=True).exists()


def test_queue_urls_csrf_and_request_creation(setup, client):
    staff, r, _, _, user, s, e = setup
    client.force_login(user)
    response = client.post(
        reverse("booking_create", args=[r.pk]),
        dict(
            start=s.isoformat(),
            end=e.isoformat(),
            key=uuid4(),
            weekdays=[s.weekday()],
            count=2,
            action="confirm",
        ),
    )
    assert response.status_code == 302
    proposal = ReservationRequest.objects.get()
    assert not Booking.objects.exists()
    assert client.get(reverse("request_detail", args=[proposal.pk])).status_code == 200
    assert client.get(reverse("request_queue")).status_code == 404
    stranger = User.objects.create_user(
        "stranger@example.test", email_verified_at=user.email_verified_at, privacy_version="test"
    )
    client.force_login(stranger)
    assert client.get(reverse("request_detail", args=[proposal.pk])).status_code == 404
    client.force_login(staff)
    assert client.get(reverse("request_queue")).status_code == 200
    before = AuditEvent.objects.count()
    assert (
        client.get(reverse("request_detail", args=[proposal.pk]), {"action": "approve"}).status_code
        == 200
    )
    assert not Booking.objects.exists() and AuditEvent.objects.count() == before
    response = client.post(
        reverse("request_detail", args=[proposal.pk]),
        dict(action="approve", revision=1, reason="Team geprüft"),
    )
    assert response.status_code == 302 and Booking.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_series_approval_race_with_single_booking(setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    staff, r, _, _, user, s, e = setup
    proposal = request(setup, count=2)
    barrier = Barrier(2)

    def attempt(kind):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            try:
                if kind == "series":
                    recurrence.approve(staff, proposal.pk, 1, "Concurrent")
                else:
                    services.confirm(user, r.pk, s, e, uuid4())
                return kind
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        winners = list(pool.map(attempt, ("series", "single")))
    assert winners.count("conflict") == 1
    proposal.refresh_from_db()
    assert Booking.objects.count() == (2 if proposal.status == "approved" else 1)


def test_pending_exception_retains_original_and_allows_atomic_approval(setup):
    staff, _, _, _, user, s, e = setup
    proposal = request(setup, count=3)
    row, omitted, _ = list(proposal.occurrences.all())
    recurrence.adjust(
        user, row.pk, 1, "Einmal später", start=s + timedelta(hours=2), end=e + timedelta(hours=2)
    )
    with pytest.raises(ValidationError):
        recurrence.approve(staff, proposal.pk, 1, "Veraltet")
    recurrence.adjust(user, omitted.pk, 2, "Einmal ausnehmen")
    assert not Booking.objects.exists()
    recurrence.approve(staff, proposal.pk, 3, "Ausnahmen geprüft")
    assert Booking.objects.count() == 2
    row.refresh_from_db()
    assert row.local_start == s.isoformat()
    assert row.booking.start.astimezone(recurrence.zone(row.booking.timezone)).hour == 12
    assert AuditEvent.objects.filter(action="booking.request_adjusted").count() == 2


def test_dst_invalid_occurrence_needs_explicit_pending_correction(setup):
    from datetime import time

    from bookings.models import ScheduleWindow

    staff, r, _, p, user, _, _ = setup
    ScheduleWindow.objects.filter(resource=r).delete()
    for day in range(7):
        for purpose in ("usage", "access", "opening"):
            services.save_schedule(
                staff,
                dict(
                    resource=r,
                    purpose=purpose,
                    weekday=day,
                    start_time=time(0),
                    end_time=time(0),
                    end_next_day=True,
                ),
            )
    start, end = datetime(2026, 10, 18, 2), datetime(2026, 10, 18, 3)
    proposal = recurrence.submit(user, r.pk, start, end, uuid4(), weekdays=[6], count=2)
    with pytest.raises(recurrence.Conflicts):
        recurrence.approve(staff, proposal.pk, 1, "Mehrdeutiger Termin")
    second = list(proposal.occurrences.all())[1]
    recurrence.adjust(
        user,
        second.pk,
        1,
        "Spätere Uhrzeit",
        start=datetime(2026, 10, 25, 2),
        end=datetime(2026, 10, 25, 3),
        start_fold=1,
    )
    recurrence.approve(staff, proposal.pk, 2, "Offset geprüft")
    assert Booking.objects.count() == 2


def test_direct_editor_and_whole_series_rollback_on_policy_change(setup):
    staff, r, _, p, user, s, e = setup
    proposal = recurrence.create_approved(
        staff,
        r.pk,
        s,
        e,
        uuid4(),
        beneficiary=user,
        weekdays=[s.weekday()],
        count=2,
        reason="Direkt geplant",
    )
    assert proposal.status == "approved" and Booking.objects.count() == 2
    other = recurrence.submit(
        user,
        r.pk,
        s + timedelta(days=1),
        e + timedelta(days=1),
        uuid4(),
        weekdays=[(s + timedelta(days=1)).weekday()],
        count=3,
    )
    services.save_policy(staff, r.pk, {"max_occurrences": 2}, p.revision)
    with pytest.raises(recurrence.Conflicts):
        recurrence.approve(staff, other.pk, 1, "Limit geändert")
    assert Booking.objects.count() == 2


def test_database_request_identity_and_approval_completeness(setup):
    from bookings.models import RequestAdjustment, RequestOccurrence
    from django.db import connection

    staff, _, _, _, user, s, e = setup
    proposal = request(setup, count=2)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReservationRequest.objects.filter(pk=proposal.pk).update(beneficiary=staff, revision=2)
    with pytest.raises(IntegrityError), transaction.atomic():
        RequestOccurrence.objects.filter(request=proposal).update(local_start="2026-01-01T10:00")
    with pytest.raises(IntegrityError), transaction.atomic():
        ReservationRequest.objects.filter(pk=proposal.pk).update(
            status="approved",
            revision=2,
            decided_by=staff,
            decided_at=proposal.created_at,
            reason="Fake",
        )
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS request_consistent IMMEDIATE")
    row = proposal.occurrences.first()
    recurrence.adjust(
        user, row.pk, 1, "Später", start=s + timedelta(hours=2), end=e + timedelta(hours=2)
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        RequestAdjustment.objects.filter(occurrence=row).update(reason="Rewrite")


def test_single_rejection_withdrawal_and_csrf(setup, client):
    from django.test import Client

    staff, r, _, _, user, s, e = setup
    proposal = recurrence.submit(user, r.pk, s, e, uuid4())
    secure = Client(enforce_csrf_checks=True)
    secure.force_login(staff)
    assert (
        secure.post(
            reverse("request_detail", args=[proposal.pk]),
            dict(action="approve", revision=1, reason="No token"),
        ).status_code
        == 403
    )
    recurrence.reject(staff, proposal.pk, 1, "Anderer Termin nötig")
    assert not Booking.objects.exists()
    other = recurrence.submit(user, r.pk, s, e, uuid4())
    recurrence.withdraw(user, other.pk, 1, "Erledigt")
    other.refresh_from_db()
    assert other.status == "cancelled" and not Booking.objects.exists()


def test_selected_pool_series_cannot_fall_back_to_other_unit(setup):
    from resources import services as resources

    staff, r, old, _, user, s, e = setup
    second = resources.save_unit(staff, r.pk, {"name": "Other"})
    pool = resources.save_pool(staff, r.pk, "Selected", [old], public_name="Gewählter Pool")
    proposal = request(setup, count=2, pool_id=pool.pk)
    services.confirm(
        user, r.pk, s + timedelta(weeks=1), e + timedelta(weeks=1), uuid4(), unit_id=old.pk
    )
    with pytest.raises(recurrence.Conflicts):
        recurrence.approve(staff, proposal.pk, 1, "Kein Ersatz")
    assert Booking.objects.count() == 1 and not Booking.objects.filter(unit=second).exists()


def test_physical_series_keeps_appointments_and_current_agreement_gates(lending_setup):
    from lending import agreements
    from lending.models import Loan

    staff, r, _, _, user, s, e, pickup, due, versions = lending_setup
    for owner, actions in ((staff, ("booking.approve",)), (user, ("booking.request_recurrence",))):
        group = owner.membership_set.get(removed_at=None).group
        for action in actions:
            Grant.objects.create(group=group, action=action, effect="allow")
    proposal = recurrence.submit(
        user, r.pk, s, e, uuid4(), weekdays=[s.weekday()], count=3, pickup_at=pickup, return_at=due
    )
    newer = agreements.save_version(staff, versions[0].agreement_id, "Aktualisierte Bedingungen")
    agreements.publish_version(staff, newer.pk)
    with pytest.raises(recurrence.Conflicts):
        recurrence.approve(staff, proposal.pk, 1, "Alte Zustimmung reicht nicht")
    assert not Booking.objects.exists() and not Loan.objects.exists()
    agreements.accept(user, [newer.pk])
    recurrence.approve(staff, proposal.pk, 1, "Aktuelle Zustimmung geprüft")
    rows = list(Booking.objects.order_by("start"))
    assert rows[1].appointment.pickup_at - rows[0].appointment.pickup_at == timedelta(hours=169)
    assert not Loan.objects.exists()


def test_pending_invalid_dst_can_be_omitted_without_implicit_shift(setup):
    staff, r, _, _, user, _, _ = setup
    start, end = datetime(2026, 10, 18, 2), datetime(2026, 10, 18, 3)
    proposal = recurrence.submit(user, r.pk, start, end, uuid4(), weekdays=[6], count=2)
    row = list(proposal.occurrences.all())[1]
    change = recurrence.adjust(user, row.pk, 1, "Zeitumstellung: einmal ausnehmen")
    assert change.cancelled and change.local_start == "2026-10-25T02:00:00"
    assert not Booking.objects.exists()


def test_multiple_exception_chain_and_staff_direct_browser_flow(setup, client):
    staff, r, _, _, user, s, e = setup
    client.force_login(staff)
    response = client.post(
        reverse("booking_create", args=[r.pk]),
        dict(
            start=s.isoformat(),
            end=e.isoformat(),
            key=uuid4(),
            weekdays=[s.weekday()],
            count=2,
            action="direct",
            beneficiary_email=user.email,
            approval_reason="Teamplanung",
        ),
    )
    assert response.status_code == 302
    proposal = ReservationRequest.objects.get()
    assert proposal.status == "approved"
    row = proposal.occurrences.first()
    a = recurrence.exception(
        staff,
        row.pk,
        row.booking.revision,
        "Erste Änderung",
        start=s + timedelta(hours=2),
        end=e + timedelta(hours=2),
    )
    b = recurrence.exception(
        staff,
        row.pk,
        a.replacement.revision,
        "Zweite Änderung",
        start=s + timedelta(hours=3),
        end=e + timedelta(hours=3),
    )
    assert recurrence.current_booking(row).pk == b.replacement_id
    assert client.get(reverse("occurrence_exception", args=[row.pk])).status_code == 200


def test_series_preview_detects_conflicts_between_its_own_occurrences(setup):
    from datetime import time

    from bookings.models import ScheduleWindow

    staff, r, _, p, user, s, _ = setup
    services.save_policy(staff, r.pk, {"max_duration_minutes": 2880}, p.revision)
    ScheduleWindow.objects.filter(resource=r).delete()
    for day in range(7):
        for purpose in ("usage", "access", "opening"):
            services.save_schedule(
                staff,
                dict(
                    resource=r,
                    purpose=purpose,
                    weekday=day,
                    start_time=time(0),
                    end_time=time(0),
                    end_next_day=True,
                ),
            )
    proposal = recurrence.submit(
        user, r.pk, s, s + timedelta(hours=25), uuid4(), weekdays=[3, 4], count=2
    )
    preview = recurrence.preview(staff, proposal.pk)
    assert [r["code"] for r in preview] == ["available", "reserved"]
    assert not Booking.objects.exists()
    with pytest.raises(recurrence.Conflicts):
        recurrence.approve(staff, proposal.pk, 1, "Eigener Konflikt")
    assert not Booking.objects.exists()


def test_cap_above_52_is_configurable_not_hardcoded(setup):
    staff, r, _, p, user, _, _ = setup
    services.save_policy(staff, r.pk, {"max_occurrences": 60, "max_horizon_days": 500}, p.revision)
    Grant.objects.filter(group__membership__user=user, action="booking.create_own").update(
        max_horizon_days=500
    )
    proposal = request(setup, count=53)
    assert proposal.occurrences.count() == 53 and not AllocationClaim.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_approve_and_withdraw_are_revision_safe(setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    staff, _, _, _, user, _, _ = setup
    proposal = request(setup, count=2)
    barrier = Barrier(2)

    def attempt(kind):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            try:
                if kind == "approve":
                    recurrence.approve(staff, proposal.pk, 1, "Team")
                else:
                    recurrence.withdraw(user, proposal.pk, 1, "Zurückziehen")
                return kind
            except ValidationError:
                return "stale"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ("approve", "withdraw")))
    assert results.count("stale") == 1
    proposal.refresh_from_db()
    assert Booking.objects.count() == (2 if proposal.status == "approved" else 0)


def test_changed_optional_bundle_still_renders_history_and_refuses_silent_change(setup, client):
    from resources import bundles

    staff, r, _, _, user, s, e = setup
    child = component(setup)
    bundles.configure(staff, r.pk, [(child, False)], r.revision)
    proposal = request(setup, count=2, optional_ids=[str(child.pk)])
    r.refresh_from_db()
    bundles.configure(staff, r.pk, [], r.revision)
    client.force_login(user)
    assert client.get(reverse("request_detail", args=[proposal.pk])).status_code == 200
    client.force_login(staff)
    assert client.get(reverse("request_detail", args=[proposal.pk])).status_code == 200
    with pytest.raises(recurrence.Conflicts):
        recurrence.approve(staff, proposal.pk, 1, "Nicht still ändern")
    assert not Booking.objects.exists()
