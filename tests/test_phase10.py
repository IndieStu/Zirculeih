from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from accounts.models import Grant, Membership, User
from assetops import reports, services
from assetops.models import Discrepancy, ExpectedAsset, InventoryRun, MaintenanceTask, Observation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone
from inventory import services as inventory
from inventory.models import AssetMovement, Location
from test_bookings import configured as configured_fixture
from test_lending import lending_setup as lending_fixture

lending_setup = lending_fixture
configured = configured_fixture
pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.fixture
def operator(staff):
    group = Membership.objects.get(user=staff).group
    for action in [
        "inventory_run.create",
        "inventory_run.start",
        "inventory_run.read",
        "inventory_run.observe",
        "inventory_run.complete",
        "inventory_run.export",
        "inventory_discrepancy.resolve",
        "maintenance.manage",
    ]:
        Grant.objects.create(group=group, action=action, effect="allow")
    return staff


def started(operator, registry):
    run = services.create_run(operator, "Werkstatt zählen", "location", registry[0].pk)
    return services.start(operator, run.pk, run.revision)


def scan(operator, run, asset, location, key=None):
    identifier = asset.identifiers.get(kind="owned")
    return services.observe(
        operator, run.pk, identifier.namespace_id, identifier.raw_value, location.pk, key or uuid4()
    )


def test_snapshot_and_scans_never_move_or_mark_missing(operator, registry):
    run = started(operator, registry)
    asset = registry[3]
    other = inventory.save_tree(operator, Location, {"name": "Nebenraum", "is_active": True})
    snapshot = run.expected.get().snapshot
    key = uuid4()
    row, state = scan(operator, run, asset, other, key)
    assert state == "wrong_location"
    assert scan(operator, run, asset, other, key)[0].pk == row.pk
    assert Observation.objects.count() == 1
    assert scan(operator, run, asset, other)[1] == "already_seen"
    asset.refresh_from_db()
    assert str(asset.location_id) == snapshot["location_id"]
    assert not AssetMovement.objects.exists()
    closed = services.close(operator, run.pk, run.revision)
    assert closed.report["assets"][0]["outcome"] == "wrong_location"
    assert closed.report["assets"][0]["custody"]["state"] == "on_site"
    asset.refresh_from_db()
    assert asset.lifecycle == "active"


def test_aliases_count_one_asset_and_not_seen_is_not_lost(operator, registry):
    run = started(operator, registry)
    asset = registry[3]
    for alias in asset.identifiers.all():
        services.observe(
            operator, run.pk, alias.namespace_id, alias.raw_value, asset.location_id, uuid4()
        )
    assert len(services.assessment(operator, run)["assets"]) == 1
    second = services.create_run(operator, "Noch nicht gescannt", "organization")
    second = services.start(operator, second.pk, second.revision)
    closed = services.close(operator, second.pk, second.revision)
    assert closed.report["assets"][0]["outcome"] == "not_seen"
    asset.refresh_from_db()
    assert asset.lifecycle != "lost"


def test_observation_key_cannot_change_payload(operator, registry):
    run = started(operator, registry)
    key = uuid4()
    asset = registry[3]
    scan(operator, run, asset, registry[1], key)
    with pytest.raises(ValidationError):
        scan(operator, run, asset, registry[0], key)


def test_closed_run_and_snapshot_sql_are_immutable(operator, registry):
    run = started(operator, registry)
    scan(operator, run, registry[3], registry[1])
    closed = services.close(operator, run.pk, run.revision)
    with pytest.raises(ValidationError):
        scan(operator, closed, registry[3], registry[1])
    for fn in [
        lambda: ExpectedAsset.objects.filter(run=run).update(snapshot={}),
        lambda: Observation.objects.filter(run=run).delete(),
        lambda: InventoryRun.objects.filter(pk=run.pk).update(report={}),
    ]:
        with pytest.raises(IntegrityError), transaction.atomic():
            fn()


def test_start_deny_is_atomic_and_read_rechecks_current_assets(operator, registry):
    run = services.create_run(operator, "Organisation", "organization")
    group = Membership.objects.get(user=operator).group
    deny = Grant.objects.create(
        group=group, action="asset.read", effect="deny", scope_kind="asset", scope_id=registry[3].pk
    )
    with pytest.raises(PermissionDenied):
        services.start(operator, run.pk, run.revision)
    assert not ExpectedAsset.objects.exists()
    deny.delete()
    run = services.start(operator, run.pk, run.revision)
    Grant.objects.create(
        group=group, action="asset.read", effect="deny", scope_kind="asset", scope_id=registry[3].pk
    )
    with pytest.raises(PermissionDenied):
        services.read_run(operator, run.pk)
    assert services.visible_runs(operator) == []


def test_unexpected_asset_does_not_expand_snapshot(operator, registry):
    run = started(operator, registry)
    new = inventory.save_asset(
        operator,
        {
            "inventory_number": "new-2",
            "name": "Neuer Fund",
            "location": registry[0],
            "category": registry[2],
        },
    )
    scan(operator, run, new, registry[0])
    assert run.expected.count() == 1
    assert Discrepancy.objects.get().kind == "unexpected"
    assert any(
        row["outcome"] == "unexpected" for row in services.assessment(operator, run)["assets"]
    )


def test_discrepancy_move_explicit_revision_and_frozen_report(operator, registry):
    run = started(operator, registry)
    scan(operator, run, registry[3], registry[0])
    run = services.close(operator, run.pk, run.revision)
    frozen = run.report
    row = Discrepancy.objects.get()
    services.resolve(
        operator,
        row.pk,
        "move",
        "Lagerung berichtigt",
        row.revision,
        location_id=registry[0].pk,
        asset_revision=registry[3].revision,
    )
    registry[3].refresh_from_db()
    run.refresh_from_db()
    assert registry[3].location_id == registry[0].pk
    assert run.report == frozen and AssetMovement.objects.count() == 1


def test_deferred_discrepancy_does_not_move(operator, registry):
    run = started(operator, registry)
    scan(operator, run, registry[3], registry[0])
    row = Discrepancy.objects.get()
    services.resolve(operator, row.pk, "defer", "Später vor Ort prüfen", row.revision)
    assert not AssetMovement.objects.exists()


def test_bulk_stale_revision_rolls_back_all(operator, registry):
    asset = registry[3]
    new = inventory.save_asset(
        operator,
        {
            "inventory_number": "new-3",
            "name": "Zweites",
            "location": registry[0],
            "category": registry[2],
        },
    )
    with pytest.raises(ValidationError):
        services.bulk(
            operator,
            [{"id": asset.pk, "revision": asset.revision}, {"id": new.pk, "revision": 999}],
            "move",
            reason="Sammelumzug",
            location_id=registry[0].pk,
        )
    asset.refresh_from_db()
    assert asset.location_id == registry[1].pk and not AssetMovement.objects.exists()
    services.bulk(
        operator,
        [{"id": asset.pk, "revision": asset.revision}],
        "condition",
        reason="Kontrolliert",
        condition="inspection",
    )
    asset.refresh_from_db()
    assert asset.condition == "inspection"


def test_maintenance_workflow_followup_and_no_implicit_release(operator, registry):
    task = services.task_create(
        operator,
        registry[3].pk,
        "Prüfung",
        "inspection",
        "Sichtprüfung",
        timezone.localdate(),
        30,
        operator,
    )
    task = services.task_transition(operator, task.pk, task.revision, "start")
    registry[3].refresh_from_db()
    assert registry[3].lifecycle == "maintenance"
    task = services.task_transition(
        operator, task.pk, task.revision, "complete", "Prüfung gut", condition="good"
    )
    registry[3].refresh_from_db()
    assert registry[3].lifecycle == "maintenance"
    assert MaintenanceTask.objects.get(previous=task).status == "planned"
    with pytest.raises(IntegrityError), transaction.atomic():
        MaintenanceTask.objects.filter(pk=task.pk).update(resolution="rewritten")


def test_other_active_maintenance_prevents_release(operator, registry):
    tasks = [
        services.task_create(operator, registry[3].pk, title, "repair", "", timezone.localdate())
        for title in ["A", "B"]
    ]
    tasks = [services.task_transition(operator, t.pk, t.revision, "start") for t in tasks]
    with pytest.raises(ValidationError):
        services.task_transition(
            operator,
            tasks[0].pk,
            tasks[0].revision,
            "complete",
            "Fertig",
            condition="good",
            release=True,
        )
    services.task_transition(operator, tasks[0].pk, tasks[0].revision, "cancel", "Bleibt bei B")
    services.task_transition(
        operator,
        tasks[1].pk,
        tasks[1].revision,
        "complete",
        "Fertig",
        condition="good",
        release=True,
    )
    registry[3].refresh_from_db()
    assert registry[3].lifecycle == "active"


def test_permission_marker_is_not_maintenance_or_inventory_access(staff, registry):
    staff.is_employee = True
    staff.save()
    with pytest.raises(PermissionDenied):
        services.create_run(staff, "Nicht erlaubt", "organization")
    with pytest.raises(PermissionDenied):
        services.task_create(staff, registry[3].pk, "Nein", "repair", "", timezone.localdate())


def test_reports_no_pii_and_csv_formula_escape(operator, registry, client):
    data = reports.aggregate(operator, timezone.localdate(), timezone.localdate())
    assert data["asset_count"] == 1 and data["open_loans"] == 0
    assert "PRIVATE-SERIAL" not in str(data) and operator.email not in str(data)
    client.force_login(operator)
    response = client.get(reverse("asset_reports") + "?export=1")
    assert response.status_code == 200
    assert b"PRIVATE-SERIAL" not in response.content
    group = Membership.objects.get(user=operator).group
    Grant.objects.create(
        group=group,
        action="asset.export",
        effect="deny",
        scope_kind="asset",
        scope_id=registry[3].pk,
    )
    assert client.get(reverse("asset_reports") + "?export=1").status_code == 404


def test_web_run_forms_and_scoped_export(operator, registry, client):
    client.force_login(operator)
    assert client.get(reverse("inventory_runs")).status_code == 200
    response = client.post(
        reverse("inventory_runs"),
        {"title": "Weblauf", "scope": "location", "location": registry[0].pk},
    )
    assert response.status_code == 302
    run = InventoryRun.objects.get()
    assert client.get(reverse("inventory_run", args=[run.pk])).status_code == 200
    client.post(
        reverse("inventory_run", args=[run.pk]), {"action": "start", "revision": run.revision}
    )
    assert client.get(reverse("inventory_run_export", args=[run.pk])).status_code == 200
    assert client.get(reverse("maintenance")).status_code == 200
    assert client.get(reverse("asset_bulk")).status_code == 200


def test_labels_are_private_svg_without_asset_metadata(operator, registry, client):
    client.force_login(operator)
    code = registry[3].identifiers.get(kind="owned")
    response = client.get(reverse("asset_label_svg", args=[code.pk]))
    assert response.status_code == 200 and response["Content-Type"] == "image/svg+xml"
    assert b"<svg" in response.content and b"PRIVATE" not in response.content
    response = client.get(reverse("asset_labels") + "?asset=" + str(registry[3].pk))
    assert response.status_code == 200 and b"Inventar-Mischpult" not in response.content
    client.logout()
    assert client.get(reverse("asset_label_svg", args=[code.pk])).status_code == 302


def test_terminal_generation_rejects_old_requests_and_idle_locks(
    operator, registry, client, settings
):
    client.force_login(operator)
    client.post(reverse("staffed_terminal"), {"mode": "lookup"})
    session = client.session
    old = session["staffed_terminal"]["generation"]
    response = client.post(
        reverse("staffed_terminal"), {"mode": "lookup", "terminal_generation": old}
    )
    assert response.status_code == 302
    assert client.session["staffed_terminal"]["generation"] != old
    assert client.post(reverse("terminal_scan"), {"terminal_generation": old}).status_code == 409
    session = client.session
    from assetops.models import StaffedContext

    StaffedContext.objects.filter(pk=session["staffed_terminal"]["id"]).update(
        touched_at=timezone.now() - timedelta(hours=1)
    )
    assert client.get(reverse("staffed_terminal")).status_code == 302
    assert "_auth_user_id" not in client.session


def test_terminal_inventory_scan_does_not_checkout(operator, registry, client):
    run = started(operator, registry)
    client.force_login(operator)
    client.post(reverse("staffed_terminal"), {"mode": "inventory"})
    code = registry[3].identifiers.get(kind="owned")
    response = client.post(
        reverse("terminal_scan"),
        {
            "terminal_generation": client.session["staffed_terminal"]["generation"],
            "run": run.pk,
            "namespace": code.namespace_id,
            "code": code.raw_value,
            "location": registry[1].pk,
            "request_key": uuid4(),
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200 and "Gefunden" in response.json()["message"]
    assert Observation.objects.count() == 1
    from lending.models import Loan

    assert not Loan.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_finish_concurrent_scan_has_single_consistent_boundary(operator, registry):
    run = started(operator, registry)
    barrier = Barrier(2)

    def worker(kind):
        close_old_connections()
        barrier.wait()
        try:
            user = User.objects.get(pk=operator.pk)
            if kind == "close":
                services.close(user, run.pk, run.revision)
                return "closed"
            try:
                scan(user, run, registry[3], registry[1])
                return "scanned"
            except ValidationError:
                return "rejected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(worker, ["close", "scan"]))
    run.refresh_from_db()
    assert result[0] == "closed"
    assert (run.report["assets"][0]["outcome"] == "seen") == (result[1] == "scanned")


def test_completed_report_retains_actual_custody_after_later_return(lending_setup, monkeypatch):
    from lending import services as lending
    from test_lending import issue

    actor = lending_setup[0]
    group = actor.membership_set.get(removed_at=None).group
    for action in [
        "inventory_run.create",
        "inventory_run.start",
        "inventory_run.read",
        "inventory_run.complete",
    ]:
        Grant.objects.create(group=group, action=action, effect="allow")
    booking, loan = issue(lending_setup, monkeypatch)
    run = services.create_run(actor, "Ausgeliehener Bestand", "organization")
    run = services.start(actor, run.pk, run.revision)
    run = services.close(actor, run.pk, run.revision)
    frozen = run.report
    assert frozen["assets"][0]["outcome"] == "not_seen"
    assert frozen["assets"][0]["custody"]["state"] == "on_loan"
    line = loan.lines.get()
    lending.return_lines(
        actor,
        loan.pk,
        {str(line.pk): {"condition": "good", "accessories_checked": True, "note": ""}},
        uuid4(),
    )
    run.refresh_from_db()
    assert run.report == frozen


def test_maintenance_flags_promises_and_blocks_new_booking(lending_setup):
    from bookings import services as booking_services
    from bookings.models import BookingIncident
    from test_lending import reserve

    actor, resource, unit, _, user, start, end, pickup, due, _ = lending_setup
    group = actor.membership_set.get(removed_at=None).group
    Grant.objects.create(group=group, action="maintenance.manage", effect="allow")
    existing = reserve(lending_setup)
    task = services.task_create(
        actor, unit.asset_id, "Reparatur", "repair", "", timezone.localdate()
    )
    task = services.task_transition(actor, task.pk, task.revision, "start")
    assert BookingIncident.objects.filter(booking=existing, is_open=True).exists()
    with pytest.raises(ValidationError):
        booking_services.confirm(
            user,
            resource.pk,
            start + timedelta(days=2),
            end + timedelta(days=2),
            uuid4(),
            pickup_at=pickup + timedelta(days=2),
            return_at=due + timedelta(days=2),
        )


def test_csrf_and_scoped_read_deny_for_new_views(operator, registry):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(operator)
    assert (
        client.post(
            reverse("inventory_runs"), {"title": "CSRF", "scope": "organization"}
        ).status_code
        == 403
    )
    assert client.post(reverse("staffed_terminal"), {"mode": "lookup"}).status_code == 403
    assert not InventoryRun.objects.exists()


def test_terminal_stale_generation_rechecked_against_database(operator, registry, client):
    from assetops.models import StaffedContext

    client.force_login(operator)
    client.post(reverse("staffed_terminal"), {"mode": "lookup"})
    old = client.session["staffed_terminal"]
    StaffedContext.objects.filter(pk=old["id"]).update(generation="a" * 32)
    assert (
        client.post(
            reverse("terminal_scan"), {"terminal_generation": old["generation"]}
        ).status_code
        == 409
    )
    assert client.get(reverse("staffed_terminal")).status_code == 302
    assert client.session["staffed_terminal"]["generation"] == "a" * 32


@pytest.mark.django_db(transaction=True)
def test_finish_concurrent_move_keeps_expectation_and_report_fixed(operator, registry):
    run = started(operator, registry)
    asset = registry[3]
    barrier = Barrier(2)

    def worker(kind):
        close_old_connections()
        barrier.wait()
        try:
            user = User.objects.get(pk=operator.pk)
            if kind == "close":
                return services.close(user, run.pk, run.revision).report
            return inventory.move_asset(
                user, asset.pk, registry[0].pk, "Während Inventur", asset.revision
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(worker, ["close", "move"]))
    run.refresh_from_db()
    asset.refresh_from_db()
    assert run.report == result[0]
    assert asset.location_id == registry[0].pk
    assert run.report["assets"][0]["expected_location"] == str(registry[1].pk)
    assert run.report["assets"][0]["outcome"] == "not_seen"


def test_run_limit_and_unknown_code_do_not_mutate(operator, registry, monkeypatch):
    monkeypatch.setattr(services, "MAX_ASSETS", 0)
    run = services.create_run(operator, "Grenze", "organization")
    with pytest.raises(ValidationError):
        services.start(operator, run.pk, run.revision)
    assert not ExpectedAsset.objects.exists()
    monkeypatch.setattr(services, "MAX_ASSETS", 2000)
    run = services.start(operator, run.pk, run.revision)
    with pytest.raises(ValidationError):
        services.observe(
            operator,
            run.pk,
            registry[3].identifiers.first().namespace_id,
            "UNKNOWN-123",
            registry[1].pk,
            uuid4(),
        )
    assert not Observation.objects.exists()


def test_terminal_return_form_keeps_generation_and_rotates_after_success(
    lending_setup, monkeypatch, client
):
    from test_lending import issue

    actor = lending_setup[0]
    _, loan = issue(lending_setup, monkeypatch)
    client.force_login(actor)
    client.post(reverse("staffed_terminal"), {"mode": "return"})
    old = client.session["staffed_terminal"]["generation"]
    line = loan.lines.get()
    url = reverse("loan_return", args=[line.pk])
    response = client.get(url)
    assert response.status_code == 200 and old.encode() in response.content
    response = client.post(
        url,
        {
            "terminal_generation": old,
            "key": uuid4(),
            "condition": "good",
            "accessories_checked": "on",
            "note": "",
        },
    )
    assert response.status_code == 302
    line.refresh_from_db()
    assert line.returned_at is not None
    assert client.session["staffed_terminal"]["generation"] != old
    assert client.post(url, {"terminal_generation": old}).status_code == 409


def test_label_svg_retains_restrictive_policy(operator, registry, client):
    client.force_login(operator)
    code = registry[3].identifiers.get(kind="owned")
    response = client.get(reverse("asset_label_svg", args=[code.pk]))
    assert response["Content-Security-Policy"] == "default-src 'none'; sandbox"
    assert response["Cache-Control"] == "no-store, private"


def test_report_reserved_hours_use_elapsed_time_across_dst(configured):
    from datetime import date, datetime, time

    from bookings import services as bookings

    actor, resource, _, policy, user, _, _ = configured
    bookings.save_policy(actor, resource.pk, {"max_duration_minutes": 3000}, policy.revision)
    for purpose in ["usage", "access", "opening"]:
        bookings.save_schedule(
            actor,
            {
                "resource": resource,
                "purpose": purpose,
                "weekday": 6,
                "start_time": time(0),
                "end_time": time(0),
                "end_next_day": True,
            },
        )
    bookings.confirm(user, resource.pk, datetime(2026, 10, 25), datetime(2026, 10, 26), uuid4())
    data = reports.aggregate(actor, date(2026, 10, 25), date(2026, 10, 25))
    assert data["bookings"][0][1]["reserved_hours"] == 25.0
