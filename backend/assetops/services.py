"""Explicit inventory operations; the common authorization lock is always first."""

from datetime import timedelta
from uuid import UUID

from accounts.authorization import Scope, authorization_write, require
from accounts.services import audit
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from inventory import services as inventory
from inventory.models import Asset, Category, Location
from lending.models import LoanLine

from .models import Discrepancy, ExpectedAsset, InventoryRun, MaintenanceTask, Observation

MAX_ASSETS = 2000


def run_scope(run):
    if run.scope == "organization":
        return Scope()
    node = (Location if run.scope == "location" else Category).objects.get(pk=run.scope_id)
    return inventory.tree_scope(node)


def members(run):
    qs = Asset.objects.filter(archived_at__isnull=True)
    if run.scope != "organization":
        model = Location if run.scope == "location" else Category
        qs = qs.filter(**{run.scope + "_id__in": inventory.descendants(model, run.scope_id)})
    return qs.select_related("category", "location").order_by("id")


def check_assets(actor, assets, action="asset.read"):
    for asset in assets:
        require(actor, action, inventory.asset_scope(asset))


def read_run(actor, run_id, action="inventory_run.read"):
    run = InventoryRun.objects.get(pk=run_id)
    require(actor, action, run_scope(run))
    # Current denies must apply even after an asset moves out of the original scope.
    ids = set(run.expected.values_list("asset_id", flat=True)) | set(
        run.observations.values_list("asset_id", flat=True)
    )
    check_assets(actor, Asset.objects.filter(pk__in=ids).select_related("location", "category"))
    return run


def visible_runs(actor):
    result = []
    for run in InventoryRun.objects.order_by("-created_at"):
        try:
            read_run(actor, run.pk)
        except PermissionDenied:
            continue
        result.append(run)
    return result


def custody(asset_id, at):
    line = LoanLine.objects.filter(asset_id=asset_id, returned_at__isnull=True).first()
    if not line:
        return {"state": "on_site", "assessed_at": at.isoformat()}
    return {
        "state": "overdue" if line.expected_return < at else "on_loan",
        "line_id": str(line.pk),
        "expected_return": line.expected_return.isoformat(),
        "assessed_at": at.isoformat(),
    }


def create_run(actor, title, scope, scope_id=None):
    with authorization_write():
        row = InventoryRun(title=title.strip(), scope=scope, scope_id=scope_id, created_by=actor)
        row.full_clean()
        require(actor, "inventory_run.create", run_scope(row))
        if scope != "organization":
            inventory.require_active(
                (Location if scope == "location" else Category).objects.get(pk=scope_id)
            )
        row.save()
        audit(actor, "inventory_run.created", object_id=row.pk)
        return row


def start(actor, run_id, revision):
    with authorization_write():
        run = read_run(actor, run_id, "inventory_run.start")
        if run.status != "draft" or run.revision != revision:
            raise ValidationError("Aktuellen Entwurf laden.")
        assets = list(members(run)[: MAX_ASSETS + 1])
        if len(assets) > MAX_ASSETS:
            raise ValidationError("Mehr als 2000 Assets: einen engeren Bereich wählen.")
        check_assets(actor, assets)
        now = timezone.now()
        for asset in assets:
            snapshot = inventory.asset_snapshot(asset)
            snapshot["custody"] = custody(asset.pk, now)
            ExpectedAsset.objects.create(run=run, asset=asset, snapshot=snapshot)
        run.status, run.started_at = "active", now
        run.revision += 1
        run.save()
        audit(actor, "inventory_run.started", object_id=run.pk, details={"expected": len(assets)})
        return run


def observe(actor, run_id, namespace_id, code, location_id, request_key):
    with authorization_write():
        run = read_run(actor, run_id, "inventory_run.observe")
        if run.status != "active":
            raise ValidationError("Dieser Inventurlauf nimmt keine Scans mehr an.")
        location = Location.objects.get(pk=location_id)
        inventory.require_active(location)
        require(actor, "location.read", inventory.tree_scope(location))
        result = inventory.resolve_identifier(actor, namespace_id, code)
        if result.status != "found" or not result.asset_id:
            raise ValidationError("Code unbekannt oder nicht zugänglich; weiter scannen.")
        asset = inventory.read_asset(actor, result.asset_id)
        require(actor, "inventory_run.observe", inventory.asset_scope(asset))
        existing = Observation.objects.filter(run=run, request_key=request_key).first()
        if existing:
            if existing.asset_id != asset.pk or existing.location_id != location.pk:
                raise ValidationError("Diese Anfrage gehört zu einem anderen Scan.")
            return existing, "already_seen"
        if run.observations.count() >= 10000:
            raise ValidationError("Scanlimit erreicht; Lauf abschließen.")
        already = run.observations.filter(asset=asset).exists()
        now = timezone.now()
        row = Observation.objects.create(
            run=run,
            asset=asset,
            location=location,
            actor=actor,
            request_key=request_key,
            custody=custody(asset.pk, now),
        )
        expected = run.expected.filter(asset=asset).first()
        kind = (
            "unexpected"
            if expected is None
            else "wrong_location"
            if str(location.pk) != expected.snapshot["location_id"]
            else ""
        )
        if kind:
            Discrepancy.objects.get_or_create(run=run, asset=asset, kind=kind)
        audit(
            actor,
            "inventory_run.observed",
            object_id=run.pk,
            details={
                "asset": str(asset.pk),
                "location": str(location.pk),
                "observation": str(row.pk),
            },
        )
        return row, "already_seen" if already else kind or "seen"


def assessment(actor, run):
    read_run(actor, run.pk)
    now = timezone.now()
    expected = {row.asset_id: row for row in run.expected.all()}
    observed: dict[UUID, set[str]] = {}
    for row in run.observations.order_by("created_at", "id"):
        observed.setdefault(row.asset_id, set()).add(str(row.location_id))
    report = []
    ids = set(expected) | set(observed)
    for asset in (
        Asset.objects.filter(pk__in=ids)
        .select_related("location", "category")
        .order_by("inventory_number")
    ):
        original = expected.get(asset.pk)
        locations = sorted(observed.get(asset.pk, set()))
        expected_location = original.snapshot["location_id"] if original else None
        state = (
            "unexpected"
            if not original
            else "not_seen"
            if not locations
            else "wrong_location"
            if any(loc != expected_location for loc in locations)
            else "seen"
        )
        report.append(
            dict(
                asset_id=str(asset.pk),
                inventory_number=original.snapshot["inventory_number"]
                if original
                else asset.inventory_number,
                name=original.snapshot["name"] if original else asset.name,
                expected_location=expected_location,
                observed_locations=locations,
                outcome=state,
                custody=custody(asset.pk, now),
            )
        )
    return {"cutoff": now.isoformat(), "assets": report}


def close(actor, run_id, revision, *, cancel=False):
    with authorization_write():
        run = read_run(actor, run_id, "inventory_run.complete")
        if run.status != "active" or run.revision != revision:
            raise ValidationError("Aktuellen laufenden Inventurstand laden.")
        run.report = assessment(actor, run)
        run.closed_at = timezone.now()
        run.status = "cancelled" if cancel else "completed"
        run.revision += 1
        run.save()
        audit(actor, "inventory_run.closed", object_id=run.pk, details={"status": run.status})
        return run


def resolve(
    actor, discrepancy_id, decision, reason, revision, *, location_id=None, asset_revision=None
):
    with authorization_write():
        row = Discrepancy.objects.select_related("run").get(pk=discrepancy_id)
        read_run(actor, row.run_id)
        asset = inventory.read_asset(actor, row.asset_id)
        require(actor, "inventory_discrepancy.resolve", inventory.asset_scope(asset))
        if (
            row.revision != revision
            or row.resolved_at
            or decision not in {"move", "temporary", "defer"}
            or not reason.strip()
            or len(reason) > 500
        ):
            raise ValidationError(
                "Aktuelle offene Abweichung, Entscheidung und Grund erforderlich."
            )
        if decision == "move":
            if not Observation.objects.filter(
                run=row.run, asset=asset, location_id=location_id
            ).exists():
                raise ValidationError("Einen dokumentierten Fundort wählen.")
            inventory.move_asset(actor, asset.pk, location_id, reason, asset_revision)
        row.decision, row.reason, row.resolved_by, row.resolved_at = (
            decision,
            reason,
            actor,
            timezone.now(),
        )
        row.revision += 1
        row.save()
        audit(
            actor,
            "inventory_run.discrepancy_resolved",
            object_id=row.run_id,
            reason=reason,
            details={"discrepancy": str(row.pk), "decision": decision, "asset": str(asset.pk)},
        )
        return row


def task_read(actor, task_id):
    task = MaintenanceTask.objects.select_related("asset__location", "asset__category").get(
        pk=task_id
    )
    require(actor, "asset.read", inventory.asset_scope(task.asset))
    require(actor, "maintenance.manage", inventory.asset_scope(task.asset))
    return task


def task_create(
    actor,
    asset_id,
    title,
    kind,
    description,
    due_date,
    interval_days=None,
    assignee=None,
    attachments=(),
):
    with authorization_write():
        asset = inventory.read_asset(actor, asset_id)
        require(actor, "maintenance.manage", inventory.asset_scope(asset))
        if assignee and assignee.pk != actor.pk:
            require(actor, "user.invite")
        if assignee and not assignee.is_active:
            raise ValidationError("Aktive zuständige Person wählen.")
        from inventory.extensions import read_media

        media = []
        for pk in attachments:
            item = read_media(actor, pk)
            if item.asset_id != asset.pk:
                raise ValidationError("Dokument gehört zu einem anderen Asset.")
            media.append(item)
        task = MaintenanceTask(
            asset=asset,
            title=title,
            kind=kind,
            description=description,
            due_date=due_date,
            interval_days=interval_days,
            reported_by=actor,
            assignee=assignee,
        )
        task.full_clean()
        task.save()
        task.attachments.set(media)
        audit(actor, "maintenance.created", object_id=asset.pk, details={"task": str(task.pk)})
        return task


def task_transition(actor, task_id, revision, action, resolution="", condition=None, release=False):
    with authorization_write():
        task = task_read(actor, task_id)
        asset = task.asset
        if task.revision != revision or task.status in {"completed", "cancelled"}:
            raise ValidationError("Aktuellen offenen Wartungsauftrag laden.")
        if action == "start" and task.status == "planned":
            inventory.save_asset(
                actor,
                {"lifecycle": "maintenance"},
                asset_id=asset.pk,
                expected_revision=asset.revision,
            )
            task.status, task.started_at = "in_progress", timezone.now()
        elif action in {"complete", "cancel"} and resolution.strip() and len(resolution) <= 5000:
            if release:
                if (
                    task.status != "in_progress"
                    or MaintenanceTask.objects.filter(asset=asset, status="in_progress")
                    .exclude(pk=task.pk)
                    .exists()
                ):
                    raise ValidationError("Andere aktive Wartung verhindert Freigabe.")
                if asset.lifecycle != "maintenance" or condition not in {"good", "worn"}:
                    raise ValidationError(
                        "Aktuellen Wartungszustand und freigabefähigen Zustand bestätigen."
                    )
                inventory.save_asset(
                    actor,
                    {"lifecycle": "active", "condition": condition},
                    asset_id=asset.pk,
                    expected_revision=asset.revision,
                )
            elif condition:
                inventory.save_asset(
                    actor,
                    {"condition": condition},
                    asset_id=asset.pk,
                    expected_revision=asset.revision,
                )
            task.status = "completed" if action == "complete" else "cancelled"
            task.closed_at, task.resolution = timezone.now(), resolution
            if action == "complete" and task.interval_days:
                follow = task_create(
                    actor,
                    asset.pk,
                    task.title,
                    task.kind,
                    task.description,
                    max(task.due_date, timezone.localdate()) + timedelta(days=task.interval_days),
                    task.interval_days,
                    task.assignee,
                )
                follow.previous = task
                follow.save(update_fields=["previous"])
        else:
            raise ValidationError("Ungültiger Übergang; Abschluss benötigt eine Beschreibung.")
        task.revision += 1
        task.full_clean()
        task.save()
        audit(
            actor,
            "maintenance." + task.status,
            object_id=asset.pk,
            details={"task": str(task.pk)},
            reason=resolution[:500],
        )
        return task


def bulk(actor, entries, action, *, reason, location_id=None, condition=None):
    with authorization_write():
        if not 1 <= len(entries) <= 100 or len({str(e["id"]) for e in entries}) != len(entries):
            raise ValidationError("1–100 verschiedene Assets wählen.")
        if not reason.strip() or len(reason) > 500 or action not in {"move", "condition"}:
            raise ValidationError("Aktion und Grund erforderlich.")
        for entry in entries:
            asset = inventory.read_asset(actor, UUID(str(entry["id"])))
            if action == "move":
                inventory.move_asset(actor, asset.pk, location_id, reason, entry["revision"])
            else:
                if condition not in Asset.Condition.values:
                    raise ValidationError("Zustand wählen.")
                inventory.save_asset(
                    actor,
                    {"condition": condition},
                    asset_id=asset.pk,
                    expected_revision=entry["revision"],
                )
        audit(
            actor,
            "asset.bulk_" + action,
            reason=reason,
            details={"assets": [str(e["id"]) for e in entries]},
        )
