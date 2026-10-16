from datetime import time, timedelta
from uuid import uuid4

import pytest
from accounts.models import Grant
from bookings import services as bookings
from bookings.models import AllocationClaim, Booking, ScheduleWindow
from bookings.time_rules import local_instant
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from lending import agreements, services
from lending.models import Acceptance, AgreementVersion, Loan, LoanLine
from resources import services as resources
from test_bookings import configured  # noqa: F401

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture
def lending_setup(configured, registry):  # noqa: F811
    actor, resource, logical, policy, user, start, end = configured
    group = actor.membership_set.get(removed_at=None).group
    for action in (
        "agreement.edit",
        "agreement.publish",
        "agreement.assign",
        "loan.inspect_identity",
        "loan.checkout",
        "loan.read",
        "loan.return",
        "loan.extend",
        "booking.create_for_others",
        "borrower.read_contact",
    ):
        Grant.objects.create(group=group, action=action, effect="allow")
    resources.save_unit(
        actor,
        resource.pk,
        {"name": logical.name, "is_active": False},
        unit_id=logical.pk,
        expected_revision=logical.revision,
    )
    unit = resources.save_unit(actor, resource.pk, {"name": "Physical unit", "asset": registry[3]})
    policy = bookings.save_policy(
        actor,
        resource.pk,
        {"use_mode": "physical_loan", "max_duration_minutes": 10080},
        policy.revision,
    )
    for field in ("full_name", "street", "postal_code", "city", "country", "phone"):
        setattr(user, field, "Synthetic value")
    user.save()
    versions = []
    for kind in ("general", "insurance"):
        agreement = agreements.create_agreement(actor, "Synthetic " + kind, kind)
        version = agreements.save_version(
            actor, agreement.pk, "Synthetic test text, no actual agreement."
        )
        agreements.publish_version(actor, version.pk)
        versions.append(version)
    agreements.accept(user, [v.pk for v in versions])
    for day in range(7):
        for purpose in ("pickup", "return"):
            bookings.save_schedule(
                actor,
                {
                    "resource": resource,
                    "purpose": purpose,
                    "weekday": day,
                    "start_time": time(9),
                    "end_time": time(17),
                },
            )
    pickup = local_instant(start, policy.timezone)
    due = local_instant(end, policy.timezone)
    return actor, resource, unit, policy, user, start, end, pickup, due, versions


def reserve(c):
    _, r, _, _, user, s, e, pickup, due, _ = c
    return bookings.confirm(user, r.pk, s, e, uuid4(), pickup_at=pickup, return_at=due)


def issue(c, monkeypatch):
    actor, _, _, _, user, _, _, pickup, _, _ = c
    booking = reserve(c)
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    checks = {
        str(booking.pk): {
            "condition": "good",
            "accessories_checked": True,
            "accessories": "Synthetic cable checked",
        }
    }
    loan = services.checkout(actor, user.pk, [booking.pk], uuid4(), checks=checks)
    return booking, loan


def test_physical_reservation_issue_and_return_are_separate(lending_setup, monkeypatch):
    booking, loan = issue(lending_setup, monkeypatch)
    line = loan.lines.get()
    assert line.returned_at is None and booking.pk == line.booking_id
    assert Booking.objects.count() == 1
    bookings.advance_onsite_bookings()
    line.refresh_from_db()
    assert line.returned_at is None
    borrower = lending_setup[4]
    borrower.is_active = False
    borrower.save()
    result = services.return_lines(
        lending_setup[0],
        loan.pk,
        {str(line.pk): {"condition": "good", "accessories_checked": True}},
        uuid4(),
    )
    assert result.closed_at and not AllocationClaim.objects.get(booking=booking).is_active
    booking.refresh_from_db()
    assert booking.status == "completed"
    assert not booking.incidents.filter(is_open=True).exists()


def test_new_text_version_requires_fresh_personal_acceptance(lending_setup):
    actor, r, _, _, user, s, e, pickup, due, versions = lending_setup
    version = agreements.save_version(actor, versions[0].agreement_id, "Synthetic revised text")
    agreements.publish_version(actor, version.pk)
    assert (
        bookings.availability(user, r.pk, s, e, pickup_at=pickup, return_at=due).code
        == "agreement_required"
    )
    agreements.accept(user, [version.pk])
    assert reserve(lending_setup).status == "confirmed"
    with pytest.raises(IntegrityError), transaction.atomic():
        AgreementVersion.objects.filter(pk=version.pk).update(text="Tampered")
    with pytest.raises(IntegrityError), transaction.atomic():
        Acceptance.objects.filter(user=user, version=version).delete()


def test_identity_and_custody_gate(lending_setup, monkeypatch):
    actor, _, _, _, user, _, _, pickup, _, _ = lending_setup
    booking = reserve(lending_setup)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    checks = {str(booking.pk): {"condition": "good", "accessories_checked": True}}
    with pytest.raises(ValidationError):
        services.checkout(actor, user.pk, [booking.pk], uuid4(), checks=checks)
    assert not Loan.objects.exists()
    services.identity_check(actor, user.pk)
    loan = services.checkout(actor, user.pk, [booking.pk], uuid4(), checks=checks)
    with pytest.raises(IntegrityError), transaction.atomic():
        LoanLine.objects.filter(loan=loan).delete()
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=booking.pk).update(status="cancelled")
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_extension_checks_next_claim_and_preserves_evidence(lending_setup, monkeypatch):
    from lending.models import Extension

    booking, loan = issue(lending_setup, monkeypatch)
    actor, _, _, _, _, _, end, _, due, _ = lending_setup
    line = loan.lines.get()
    booking.refresh_from_db()
    services.extend_line(
        actor,
        line.pk,
        end + timedelta(hours=1),
        due + timedelta(hours=1),
        booking.revision,
        "Synthetic extension",
    )
    booking.refresh_from_db()
    assert booking.end == due + timedelta(hours=1)
    assert Extension.objects.get(booking=booking).before_end == due
    assert booking.claim.during.upper == booking.end
    with pytest.raises(IntegrityError), transaction.atomic():
        Extension.objects.filter(booking=booking).update(reason="Tamper")
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=booking.pk).update(end=booking.end + timedelta(hours=1))


def test_spontaneous_issue_is_atomic_and_idempotent(lending_setup, monkeypatch):
    actor, _, unit, _, user, start, end, pickup, due, _ = lending_setup
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    requests = [
        {
            "unit_id": str(unit.pk),
            "start": start,
            "end": end,
            "key": uuid4(),
            "pickup_at": pickup,
            "return_at": due,
        }
    ]
    checks = {str(unit.pk): {"condition": "good", "accessories_checked": True}}
    key = uuid4()
    loan = services.checkout(actor, user.pk, [], key, checks=checks, spontaneous=requests)
    assert (
        services.checkout(actor, user.pk, [], key, checks=checks, spontaneous=requests).pk
        == loan.pk
    )
    assert Booking.objects.count() == 1 and Loan.objects.count() == 1


def test_failed_spontaneous_issue_rolls_back_booking(lending_setup, monkeypatch):
    actor, _, unit, _, user, start, end, pickup, due, _ = lending_setup
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    with pytest.raises(ValidationError):
        services.checkout(
            actor,
            user.pk,
            [],
            uuid4(),
            checks={},
            spontaneous=[
                {
                    "unit_id": str(unit.pk),
                    "start": start,
                    "end": end,
                    "key": uuid4(),
                    "pickup_at": pickup,
                    "return_at": due,
                }
            ],
        )
    assert not Booking.objects.exists() and not Loan.objects.exists()


def test_future_booking_allowed_during_custody_and_overdue_marks_it(lending_setup, monkeypatch):
    booking, loan = issue(lending_setup, monkeypatch)
    _, r, _, _, user, start, end, _, due, _ = lending_setup
    future = bookings.confirm(
        user,
        r.pk,
        start + timedelta(days=1),
        end + timedelta(days=1),
        uuid4(),
        pickup_at=due + timedelta(days=1) - timedelta(hours=1),
        return_at=due + timedelta(days=1),
    )
    monkeypatch.setattr(timezone, "now", lambda: due + timedelta(minutes=1))
    assert services.mark_overdue() == 1
    assert future.incidents.filter(code="overdue_custody", is_open=True).exists()
    assert loan.lines.get().returned_at is None
    booking.refresh_from_db()
    assert booking.status == "active"


def test_partial_return_and_damage_block_only_returned_unit(lending_setup, registry, monkeypatch):
    from inventory import services as inventory

    actor, r, _, _, user, _, _, pickup, _, _ = lending_setup
    asset = inventory.save_asset(
        actor,
        {
            "inventory_number": "second",
            "name": "Synthetic second",
            "location": registry[1],
            "category": registry[2],
        },
    )
    resources.save_unit(actor, r.pk, {"name": "Second physical", "asset": asset})
    first, second = reserve(lending_setup), reserve(lending_setup)
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    checks = {
        str(row.pk): {"condition": "good", "accessories_checked": True} for row in (first, second)
    }
    loan = services.checkout(actor, user.pk, [first.pk, second.pk], uuid4(), checks=checks)
    line = loan.lines.get(booking=first)
    services.return_lines(
        actor,
        loan.pk,
        {
            str(line.pk): {
                "condition": "damaged",
                "accessories_checked": True,
                "note": "Synthetic damage",
            }
        },
        uuid4(),
    )
    loan.refresh_from_db()
    assert loan.closed_at is None and loan.lines.filter(returned_at__isnull=True).count() == 1
    line.asset.refresh_from_db()
    assert line.asset.condition == "damaged" and line.asset.lifecycle == "maintenance"


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkout_has_one_actual_custody(lending_setup, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    actor, _, _, _, user, _, _, pickup, _, _ = lending_setup
    row = reserve(lending_setup)
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    barrier = Barrier(8)

    def attempt(_):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            try:
                return str(
                    services.checkout(
                        actor,
                        user.pk,
                        [row.pk],
                        uuid4(),
                        checks={str(row.pk): {"condition": "good", "accessories_checked": True}},
                    ).pk
                )
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert (
        results.count("conflict") == 7
        and LoanLine.objects.filter(returned_at__isnull=True).count() == 1
    )


def test_calendar_days_allow_closed_opening_between_appointments(lending_setup):
    from datetime import date

    actor, r, _, policy, user, _, _, _, _, _ = lending_setup
    policy = bookings.save_policy(
        actor, r.pk, {"time_mode": "days", "max_days": 7}, policy.revision
    )
    ScheduleWindow.objects.filter(resource=r, purpose__in=["usage", "opening"]).delete()
    pickup = local_instant(timezone.datetime(2026, 10, 22, 10), policy.timezone)
    due = local_instant(timezone.datetime(2026, 10, 24, 16), policy.timezone)
    row = bookings.confirm(
        user, r.pk, date(2026, 10, 22), date(2026, 10, 24), uuid4(), pickup_at=pickup, return_at=due
    )
    assert row.start_date == date(2026, 10, 22) and row.end_date_exclusive == date(2026, 10, 25)
    assert row.appointment.return_at == due


def test_current_profile_and_asset_specific_terms_are_mandatory(lending_setup):
    actor, r, unit, _, user, start, end, pickup, due, _ = lending_setup
    user.phone = ""
    user.save()
    assert (
        bookings.availability(user, r.pk, start, end, pickup_at=pickup, return_at=due).code
        == "borrower_profile_required"
    )
    user.phone = "Synthetic number"
    user.save()
    agreement = agreements.create_agreement(actor, "Synthetic additional", "additional")
    version = agreements.save_version(actor, agreement.pk, "Synthetic additional test text")
    agreements.publish_version(actor, version.pk)
    agreements.assign(actor, agreement.pk, asset=unit.asset)
    assert (
        bookings.availability(user, r.pk, start, end, pickup_at=pickup, return_at=due).code
        == "agreement_required"
    )
    agreements.accept(user, [version.pk])
    assert reserve(lending_setup).status == "confirmed"


def test_new_agreement_after_reservation_prevents_checkout(lending_setup, monkeypatch):
    actor, _, _, _, user, _, _, pickup, _, versions = lending_setup
    row = reserve(lending_setup)
    newer = agreements.save_version(actor, versions[0].agreement_id, "Synthetic new terms")
    agreements.publish_version(actor, newer.pk)
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    with pytest.raises(ValidationError):
        services.checkout(
            actor,
            user.pk,
            [row.pk],
            uuid4(),
            checks={str(row.pk): {"condition": "good", "accessories_checked": True}},
        )
    assert not Loan.objects.exists()


def test_scanner_prepares_then_confirms_and_resets_context(
    lending_setup, monkeypatch, client, registry
):
    from django.urls import reverse
    from inventory.models import Identifier

    actor, _, _, _, user, _, _, pickup, _, _ = lending_setup
    row = reserve(lending_setup)
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    code = Identifier.objects.get(asset=registry[3], namespace__key="inventory")
    client.force_login(actor)
    path = reverse("loan_checkout")
    assert client.post(path, {"action": "person", "email": user.email}).status_code == 200
    for _ in range(2):
        response = client.post(
            path, {"action": "scan", "namespace": code.namespace_id, "code": code.raw_value}
        )
        assert response.status_code == 200
    assert len(client.session["lending_cart"]["bookings"]) == 1 and not Loan.objects.exists()
    response = client.post(
        path,
        {"action": "confirm", "condition_" + str(row.pk): "good", "checked_" + str(row.pk): "on"},
    )
    assert response.status_code == 302
    assert "lending_cart" not in client.session and Loan.objects.count() == 1
    assert (
        client.post(
            reverse("loan_return_scan"), {"namespace": code.namespace_id, "code": code.raw_value}
        ).status_code
        == 302
    )


def test_receipt_idor_private_headers_and_csrf(lending_setup, monkeypatch, client):
    from accounts.models import User
    from django.test import Client
    from django.urls import reverse

    _, loan = issue(lending_setup, monkeypatch)
    stranger = User.objects.create_user(
        "stranger@example.test",
        "Quiet-River-8941!Cloud",
        privacy_version="test",
        email_verified_at=timezone.now(),
    )
    client.force_login(stranger)
    assert client.get(reverse("loan_detail", args=[loan.pk])).status_code == 404
    client.force_login(lending_setup[4])
    response = client.get(reverse("loan_detail", args=[loan.pk]))
    assert response.status_code == 200 and response["Cache-Control"] == "no-store, private"
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(lending_setup[0])
    assert csrf.post(reverse("loan_return", args=[loan.lines.get().pk]), {}).status_code == 403


def test_extension_cannot_overlap_followup(lending_setup, monkeypatch):
    actor, r, _, _, user, start, end, pickup, due, _ = lending_setup
    original = reserve(lending_setup)
    following = bookings.confirm(
        user,
        r.pk,
        end,
        end + timedelta(hours=1),
        uuid4(),
        pickup_at=due,
        return_at=due + timedelta(hours=1),
    )
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    loan = services.checkout(
        actor,
        user.pk,
        [original.pk],
        uuid4(),
        checks={str(original.pk): {"condition": "good", "accessories_checked": True}},
    )
    original.refresh_from_db()
    with pytest.raises(ValidationError):
        services.extend_line(
            actor,
            loan.lines.get().pk,
            end + timedelta(hours=1),
            due + timedelta(hours=1),
            original.revision,
            "Synthetic conflict",
        )
    original.refresh_from_db()
    assert original.end == due and following.claim.is_active


def test_no_show_frees_claim_without_creating_custody(lending_setup, monkeypatch):
    actor, _, _, _, _, _, _, pickup, _, _ = lending_setup
    row = reserve(lending_setup)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    services.no_show(actor, row.pk, row.revision, "Synthetic no-show")
    row.refresh_from_db()
    assert row.status == "no_show" and not row.claim.is_active and not Loan.objects.exists()
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=row.pk).update(status="confirmed")


def test_loan_receipt_cannot_close_before_actual_return(lending_setup, monkeypatch):
    _, loan = issue(lending_setup, monkeypatch)
    with pytest.raises(IntegrityError), transaction.atomic():
        Loan.objects.filter(pk=loan.pk).update(closed_at=timezone.now())
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_permission_revocation_and_employee_flag_never_bypass(lending_setup, monkeypatch):
    from django.core.exceptions import PermissionDenied

    actor, _, _, _, user, _, _, pickup, _, _ = lending_setup
    row = reserve(lending_setup)
    services.identity_check(actor, user.pk)
    actor.is_employee = True
    actor.is_system_admin = True
    actor.save()
    Grant.objects.filter(group__membership__user=actor, action="loan.checkout").delete()
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    with pytest.raises(PermissionDenied):
        services.checkout(
            actor,
            user.pk,
            [row.pk],
            uuid4(),
            checks={str(row.pk): {"condition": "good", "accessories_checked": True}},
        )
    assert not Loan.objects.exists()


def test_scanned_spontaneous_form_commits_booking_and_loan_together(
    lending_setup, monkeypatch, client, registry
):
    from django.urls import reverse
    from inventory.models import Identifier

    actor, _, unit, _, user, start, end, pickup, due, _ = lending_setup
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    client.force_login(actor)
    path = reverse("loan_checkout")
    client.post(path, {"action": "person", "email": user.email})
    code = Identifier.objects.get(asset=registry[3], namespace__key="inventory")
    response = client.post(
        path, {"action": "scan", "namespace": code.namespace_id, "code": code.raw_value}
    )
    assert response.status_code == 200 and client.session["lending_cart"]["units"] == [str(unit.pk)]
    prefix = "u_" + str(unit.pk) + "-"
    payload = {
        "action": "confirm",
        prefix + "start": start.isoformat(),
        prefix + "end": end.isoformat(),
        prefix + "pickup_at": start.isoformat(),
        prefix + "return_at": end.isoformat(),
        prefix + "key": str(uuid4()),
        "condition_" + str(unit.pk): "good",
        "checked_" + str(unit.pk): "on",
    }
    response = client.post(path, payload)
    assert response.status_code == 302 and Loan.objects.count() == Booking.objects.count() == 1
    assert "lending_cart" not in client.session


def test_physical_time_alone_cannot_activate_booking(lending_setup):
    row = reserve(lending_setup)
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=row.pk).update(status="active")
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_agreement_admin_forms_publish_assign_and_remove(lending_setup, client):
    from django.urls import reverse
    from lending.models import Agreement, AgreementAssignment

    actor, r, _, _, _, _, _, _, _, _ = lending_setup
    client.force_login(actor)
    response = client.post(
        reverse("agreement_admin"),
        {
            "title": "Synthetic special",
            "kind": "additional",
            "text": "<script>unsafe()</script> Synthetic text",
        },
    )
    assert response.status_code == 302
    row = Agreement.objects.get(title="Synthetic special")
    version = row.versions.get()
    for _ in range(2):
        assert client.post(reverse("agreement_publish", args=[version.pk])).status_code == 302
    response = client.get(reverse("agreement_admin"))
    assert b"&lt;script&gt;" in response.content and b"<script>unsafe()" not in response.content
    assert (
        client.post(
            reverse("agreement_assignment"), {"agreement": row.pk, "resource": r.pk}
        ).status_code
        == 302
    )
    assignment = AgreementAssignment.objects.get(agreement=row, resource=r)
    assert client.get(reverse("agreement_unassign", args=[assignment.pk])).status_code == 405
    assert client.post(reverse("agreement_unassign", args=[assignment.pk])).status_code == 302
    assert not AgreementAssignment.objects.filter(pk=assignment.pk).exists()


def test_own_acceptance_and_configuration_denied_to_borrower(lending_setup, client):
    from django.urls import reverse
    from lending.models import AgreementAssignment

    actor, r, _, _, user, _, _, _, _, versions = lending_setup
    newer = agreements.save_version(
        actor, versions[0].agreement_id, "Synthetic personal confirmation"
    )
    agreements.publish_version(actor, newer.pk)
    client.force_login(user)
    response = client.post(
        reverse("lending_agreements") + "?resource=" + str(r.pk), {"versions": [str(newer.pk)]}
    )
    assert (
        response.status_code == 200 and Acceptance.objects.filter(user=user, version=newer).exists()
    )
    assert client.get(reverse("lending_agreements") + "?resource=malformed").status_code == 404
    assert client.get(reverse("agreement_admin")).status_code == 404
    assert client.post(reverse("agreement_assignment"), {}).status_code == 404
    assert not AgreementAssignment.objects.exists()


def test_resource_qualification_is_rechecked_at_checkout(lending_setup, monkeypatch):
    from resources import requirements

    actor, resource, _, _, user, _, _, pickup, _, _ = lending_setup
    reserved = reserve(lending_setup)
    group = actor.membership_set.get(removed_at=None).group
    Grant.objects.create(group=group, action="qualification.issue", effect="allow")
    Grant.objects.create(group=group, action="booking.override_policy", effect="allow")
    q = requirements.create_type(actor, "Fiktive Fahrzeugeinweisung")
    requirements.configure(actor, resource.pk, [], [q.pk])
    services.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    checks = {str(reserved.pk): {"condition": "good", "accessories_checked": True}}
    with pytest.raises(ValidationError):
        services.checkout(actor, user.pk, [reserved.pk], uuid4(), checks=checks)
    assert not Loan.objects.exists()
    requirements.issue(actor, user.pk, q.pk)
    assert (
        services.checkout(actor, user.pk, [reserved.pk], uuid4(), checks=checks).lines.count() == 1
    )
