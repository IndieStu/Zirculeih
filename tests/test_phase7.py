from datetime import timedelta
from uuid import uuid4

import pytest
from accounts.models import Grant, Group, Membership, User
from bookings import services
from bookings.models import AllocationClaim, Booking, BundleMember
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from resources import bundles, requirements
from resources import services as resources
from resources.models import CategoryQualification, ResourceQualification
from test_bookings import configured as configured_fixture
from test_lending import lending_setup as lending_fixture

configured = configured_fixture
lending_setup = lending_fixture
pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


def component(c, slug="component"):
    actor, root, _, policy, _, _, _ = c
    r = resources.save_resource(
        actor,
        {
            "title": slug,
            "slug": slug,
            "location": root.location,
            "type": root.type,
            "visibility": "public",
            "booking_enabled": True,
        },
    )
    resources.save_unit(actor, r.pk, {"name": slug})
    r = resources.publication(actor, r.pk, r.revision, "publish", "Reviewed")
    services.save_policy(actor, r.pk, {"use_mode": "onsite", "max_parallel": 20})
    from bookings.models import ScheduleWindow

    for row in ScheduleWindow.objects.filter(resource=root):
        services.save_schedule(
            actor,
            {
                "resource": r,
                "purpose": row.purpose,
                "weekday": row.weekday,
                "start_time": row.start_time,
                "end_time": row.end_time,
            },
        )
    return r


def test_scoped_issuance_and_inherited_category(configured, client):
    actor, r, _, _, user, s, e = configured
    from inventory.models import Category

    category = Category.objects.create(name="Maschinen")
    child = Category.objects.create(name="CNC", parent=category)
    r.categories.add(child)
    q = requirements.create_type(actor, "Kategorie-Einweisung", category=category)
    requirements.configure_category(actor, category.pk, [q.pk])
    assert services.availability(user, r.pk, s, e).code == "qualification_required"
    teacher = User.objects.create_user(
        "teacher@example.test",
        "Test-only-password!",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name="Scoped teachers")
    Membership.objects.create(user=teacher, group=group)
    Grant.objects.create(
        group=group,
        action="qualification.issue",
        effect="allow",
        scope_kind="resource",
        scope_id=r.pk,
    )
    with pytest.raises(PermissionDenied):
        requirements.issue(teacher, user.pk, q.pk)
    Grant.objects.create(
        group=group,
        action="qualification.issue",
        effect="allow",
        scope_kind="category",
        scope_id=category.pk,
    )
    assert requirements.issue(teacher, user.pk, q.pk).qualification_id == q.pk
    assert services.availability(user, r.pk, s, e).code == "available"
    client.force_login(teacher)
    assert client.get(reverse("qualifications_admin")).status_code == 200
    other = component(configured)
    Grant.objects.create(
        group=actor.membership_set.get(removed_at=None).group,
        action="agreement.assign",
        effect="allow",
    )
    with pytest.raises(ValidationError):
        requirements.configure(actor, other.pk, [], [q.pk])
    assert CategoryQualification.objects.count() == 1


def test_selected_pool_capacity_and_public_names(configured, client):
    actor, r, u, _, user, s, e = configured
    v = resources.save_unit(
        actor, r.pk, {"name": "Private serial xyz", "public_name": "Exemplar B"}
    )
    pool = resources.save_pool(actor, r.pk, "Internal pool", [v], public_name="Pool B")
    first = services.confirm(user, r.pk, s, e, uuid4(), pool_id=pool.pk)
    assert first.unit_id == v.pk
    assert services.availability(user, r.pk, s, e, pool_id=pool.pk).code == "reserved"
    assert services.confirm(user, r.pk, s, e, uuid4(), unit_id=u.pk).unit_id == u.pk
    client.force_login(user)
    page = client.get(reverse("booking_create", args=[r.pk])).content.decode()
    assert "Exemplar B" in page and "Pool B" in page
    assert "Private serial xyz" not in page and "Internal pool" not in page
    resources.save_pool(
        actor,
        r.pk,
        pool.name,
        [v],
        pool_id=pool.pk,
        expected_revision=pool.revision,
        is_active=False,
    )
    assert (
        services.availability(
            user, r.pk, e + timedelta(hours=1), e + timedelta(hours=2), pool_id=pool.pk
        ).code
        != "available"
    )


def test_atomic_bundle_and_cancel(configured):
    actor, r, _, _, user, s, e = configured
    c = component(configured)
    bundles.configure(actor, r.pk, [(c, True)], r.revision)
    key = uuid4()
    row = services.confirm(user, r.pk, s, e, key)
    assert services.confirm(user, r.pk, s, e, key).pk == row.pk
    assert Booking.objects.count() == 2 and AllocationClaim.objects.count() == 2
    member = BundleMember.objects.exclude(booking=row).get()
    services.cancel(user, member.booking_id, member.booking.revision, "Bundle entfällt")
    assert set(Booking.objects.values_list("status", flat=True)) == {"cancelled"}
    assert not AllocationClaim.objects.filter(is_active=True).exists()


def test_bundle_conflict_rolls_back_everything_and_calendar(configured):
    actor, r, _, p, user, s, e = configured
    c = component(configured)
    bundles.configure(actor, r.pk, [(c, True)], r.revision)
    services.confirm(user, c.pk, s, e, uuid4())
    with pytest.raises(ValidationError):
        services.confirm(user, r.pk, s, e, uuid4())
    assert Booking.objects.count() == 1 and not Booking.objects.filter(resource=r).exists()
    assert services.availability(user, r.pk, s, e).code == "bundle_component_unavailable"
    from bookings.time_rules import local_instant
    from resources.bundle_calendar import occupancy

    snapshot = occupancy(r, p, local_instant(s, p.timezone), local_instant(e, p.timezone), user)
    assert snapshot.state(local_instant(s, p.timezone), local_instant(e, p.timezone)) == "booked"
    assert snapshot.free_units(local_instant(s, p.timezone), local_instant(e, p.timezone)) == []


def test_bundle_optional_permissions_cycle_and_requirements(configured):
    actor, r, _, _, user, s, e = configured
    c = component(configured)
    optional = component(configured, "optional")
    bundles.configure(actor, r.pk, [(c, True), (optional, False)], r.revision)
    r.refresh_from_db()
    with pytest.raises(ValidationError):
        bundles.configure(actor, c.pk, [(r, True)], c.revision)
    assert not c.bundle_components.exists()
    group = actor.membership_set.get(removed_at=None).group
    Grant.objects.create(group=group, action="qualification.issue", effect="allow")
    q = requirements.create_type(actor, "Komponenten-Einweisung", resource=optional)
    ResourceQualification.objects.create(resource=optional, qualification=q)
    with pytest.raises(ValidationError):
        services.confirm(user, r.pk, s, e, uuid4(), optional_ids=[optional.pk])
    assert Booking.objects.count() == 0
    row = services.confirm(user, r.pk, s, e, uuid4())
    assert row.bundle_reservation.members.count() == 2


def physical_component(c):
    from inventory import services as inventory

    actor, r, u, _p, _user, _s, _e, *_ = c
    asset = inventory.save_asset(
        actor,
        {
            "inventory_number": "P7-COMPONENT",
            "name": "Bundle component",
            "location": r.location,
            "category": u.asset.category,
        },
    )
    child = resources.save_resource(
        actor,
        {
            "title": "Bundle component",
            "slug": "physical-component",
            "location": r.location,
            "type": r.type,
            "visibility": "public",
            "booking_enabled": True,
        },
    )
    unit = resources.save_unit(actor, child.pk, {"name": "Bundle component", "asset": asset})
    child = resources.publication(actor, child.pk, child.revision, "publish", "Reviewed")
    services.save_policy(
        actor,
        child.pk,
        {"use_mode": "physical_loan", "max_duration_minutes": 10080, "max_parallel": 20},
    )
    from bookings.models import ScheduleWindow

    for row in ScheduleWindow.objects.filter(resource=r):
        services.save_schedule(
            actor,
            {
                "resource": child,
                "purpose": row.purpose,
                "weekday": row.weekday,
                "start_time": row.start_time,
                "end_time": row.end_time,
            },
        )
    bundles.configure(actor, r.pk, [(child, True)], r.revision)
    return child, unit


def test_default_parallel_limit_counts_bundle_once(configured):
    actor, r, _, p, user, s, e = configured
    c = component(configured)
    p = services.save_policy(actor, r.pk, {"max_parallel": 1}, p.revision)
    cp = c.bookingpolicy
    services.save_policy(actor, c.pk, {"max_parallel": 1}, cp.revision)
    bundles.configure(actor, r.pk, [(c, True)], r.revision)
    row = services.confirm(user, r.pk, s, e, uuid4())
    assert row.bundle_reservation.members.count() == 2
    another = component(configured, "another")
    ap = another.bookingpolicy
    services.save_policy(actor, another.pk, {"max_parallel": 2}, ap.revision)
    assert services.availability(user, another.pk, s, e).code == "available"


def test_optional_only_and_frozen_retry(configured):
    actor, r, _, _, user, s, e = configured
    c = component(configured)
    bundles.configure(actor, r.pk, [(c, False)], r.revision)
    key = uuid4()
    row = services.confirm(user, r.pk, s, e, key)
    assert not BundleMember.objects.filter(booking=row).exists()
    assert Booking.objects.count() == 1
    r.refresh_from_db()
    bundles.configure(actor, r.pk, [], r.revision)
    assert services.confirm(user, r.pk, s, e, key).pk == row.pk


def test_physical_bundle_issue_return_and_extension(lending_setup, monkeypatch):
    from lending import services as loans
    from lending.models import Loan, LoanLine

    actor, r, _, _, user, s, e, pickup, due, _ = lending_setup
    physical_component(lending_setup)
    root = services.confirm(user, r.pk, s, e, uuid4(), pickup_at=pickup, return_at=due)
    rows = list(Booking.objects.all())
    loans.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    checks = {str(row.pk): {"condition": "good", "accessories_checked": True} for row in rows}
    with pytest.raises(ValidationError):
        loans.checkout(actor, user.pk, [root.pk], uuid4(), checks=checks)
    assert not Loan.objects.exists()
    loan = loans.checkout(actor, user.pk, [row.pk for row in rows], uuid4(), checks=checks)
    assert loan.lines.count() == 2
    line = loan.lines.select_related("booking").first()
    loans.extend_line(
        actor,
        line.pk,
        e + timedelta(hours=1),
        due + timedelta(hours=1),
        line.booking.revision,
        "Gemeinsam länger",
    )
    assert set(LoanLine.objects.values_list("expected_return", flat=True)) == {
        due + timedelta(hours=1)
    }
    loans.return_lines(
        actor, loan.pk, {str(line.pk): {"condition": "good", "accessories_checked": True}}, uuid4()
    )
    assert LoanLine.objects.filter(returned_at__isnull=True).count() == 1


def test_bundle_spontaneous_requires_all_scanned_components(lending_setup, monkeypatch):
    from lending import services as loans
    from lending.models import Loan

    actor, r, u, _, user, s, e, pickup, due, _ = lending_setup
    _, cu = physical_component(lending_setup)
    loans.identity_check(actor, user.pk)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    pending = [
        {
            "unit_id": str(unit.pk),
            "start": s,
            "end": e,
            "pickup_at": pickup,
            "return_at": due,
            "key": uuid4(),
        }
        for unit in (u, cu)
    ]
    checks = {str(unit.pk): {"condition": "good", "accessories_checked": True} for unit in (u, cu)}
    with pytest.raises(ValidationError):
        loans.checkout(actor, user.pk, [], uuid4(), checks=checks, spontaneous=pending[:1])
    assert not Booking.objects.exists() and not Loan.objects.exists()
    loan = loans.checkout(actor, user.pk, [], uuid4(), checks=checks, spontaneous=pending)
    assert loan.lines.count() == 2 and Booking.objects.count() == 2


def test_sql_bundle_history_and_partial_cancel_protected(configured):
    from django.db import IntegrityError, connection, transaction

    actor, r, _, _, user, s, e = configured
    c = component(configured)
    bundles.configure(actor, r.pk, [(c, True)], r.revision)
    root = services.confirm(user, r.pk, s, e, uuid4())
    with pytest.raises(IntegrityError), transaction.atomic():
        BundleMember.objects.filter(booking=root).delete()
    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=root.pk).update(status="cancelled")
        AllocationClaim.objects.filter(booking=root).update(is_active=False)
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert Booking.objects.filter(status="confirmed").count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_bundles_compete_for_shared_component(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    actor, r, _, _, user, s, e = configured
    other = component(configured, "other-root")
    c = component(configured, "shared")
    bundles.configure(actor, r.pk, [(c, True)], r.revision)
    bundles.configure(actor, other.pk, [(c, True)], other.revision)
    barrier = Barrier(2)

    def attempt(rid):
        close_old_connections()
        try:
            barrier.wait(timeout=20)
            try:
                services.confirm(user, rid, s, e, uuid4())
                return "confirmed"
            except ValidationError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [r.pk, other.pk]))
    assert sorted(results) == ["confirmed", "conflict"]
    assert Booking.objects.count() == 2 and AllocationClaim.objects.count() == 2


def test_component_maintenance_blocks_bundle_without_cancelling_history(configured, client):
    from bookings.models import BookingIncident

    actor, r, _, p, user, s, e = configured
    c = component(configured)
    bundles.configure(actor, r.pk, [(c, True)], r.revision)
    root = services.confirm(user, r.pk, s, e, uuid4())
    from bookings.time_rules import local_instant

    services.set_block(
        actor,
        {
            "resource": c,
            "start": local_instant(s, p.timezone),
            "end": local_instant(e, p.timezone),
            "reason": "Wartung",
        },
    )
    assert Booking.objects.filter(status="confirmed").count() == 2
    assert BookingIncident.objects.filter(
        booking__resource=c, code="hard_block", is_open=True
    ).exists()
    assert services.availability(user, r.pk, s, e).code == "reserved"
    from resources.bundle_calendar import occupancy

    snapshot = occupancy(r, p, local_instant(s, p.timezone), local_instant(e, p.timezone), user)
    assert snapshot.state(local_instant(s, p.timezone), local_instant(e, p.timezone)) == "blocked"
    client.force_login(user)
    page = client.get(reverse("booking_detail", args=[root.pk]))
    assert page.status_code == 200 and c.title in page.content.decode()
    client.force_login(actor)
    assert client.get(reverse("resource_bundle", args=[r.pk])).status_code == 200
    assert client.get(reverse("qualifications_admin")).status_code == 200
    services.cancel(user, root.pk, root.revision, "Explizite Stornierung")
    assert services.availability(user, r.pk, s, e).code == "bundle_component_unavailable"


def test_scoped_teacher_navigation_and_type_list_do_not_leak_other_types(configured, client):
    actor, r, _, _, user, _, _ = configured
    q = requirements.create_type(actor, "Raum Einweisung", resource=r)
    other = component(configured)
    hidden = requirements.create_type(actor, "Vertrauliche andere Einweisung", resource=other)
    teacher = User.objects.create_user(
        "scoped@example.test",
        "Test-only-password!",
        email_verified_at=timezone.now(),
        privacy_version="test",
    )
    group = Group.objects.create(name="Nur Raum")
    Membership.objects.create(user=teacher, group=group)
    Grant.objects.create(
        group=group,
        action="qualification.issue",
        effect="allow",
        scope_kind="resource",
        scope_id=r.pk,
    )
    client.force_login(teacher)
    page = client.get(reverse("qualifications_admin"))
    assert page.status_code == 200
    body = page.content.decode()
    assert q.name in body and hidden.name not in body
    with pytest.raises(PermissionDenied):
        requirements.issue(teacher, user.pk, hidden.pk)


def test_physical_bundle_no_show_is_atomic(lending_setup, monkeypatch):
    from lending import services as loans

    actor, r, _, _, user, s, e, pickup, due, _ = lending_setup
    physical_component(lending_setup)
    root = services.confirm(user, r.pk, s, e, uuid4(), pickup_at=pickup, return_at=due)
    monkeypatch.setattr(timezone, "now", lambda: pickup + timedelta(minutes=1))
    loans.no_show(actor, root.pk, root.revision, "Nicht erschienen")
    assert set(Booking.objects.values_list("status", flat=True)) == {"no_show"}
    assert not AllocationClaim.objects.filter(is_active=True).exists()
