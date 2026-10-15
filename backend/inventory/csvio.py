import csv
import io
from datetime import timedelta

from accounts.authorization import allowed, authorization_write, require
from accounts.services import audit
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Asset, Category, Identifier, IdentifierNamespace, ImportPreview, Location
from .services import asset_scope, normalize, read_asset, require_active, save_asset, visible_assets

CORE_FIELDS = [
    "inventory_number",
    "name",
    "description",
    "location_id",
    "category_id",
    "manufacturer",
    "model",
    "condition",
    "lifecycle",
]
PRIVATE_FIELDS = ["serial_number", "internal_notes", "acquisition_date", "acquisition_value"]


def validate_row(actor, row):
    if set(row) - set(CORE_FIELDS + PRIVATE_FIELDS):
        raise ValidationError("Unbekannte CSV-Spalten.")
    if not all(row.get(f) for f in ("inventory_number", "name", "location_id", "category_id")):
        raise ValidationError("Inventarnummer, Name, Standort und Kategorie sind erforderlich.")
    try:
        location = Location.objects.get(pk=row["location_id"])
        category = Category.objects.get(pk=row["category_id"])
    except (ValueError, ValidationError, Location.DoesNotExist, Category.DoesNotExist) as exc:
        raise ValidationError("Standort oder Kategorie nicht verfügbar.") from exc
    require_active(location)
    require_active(category)
    ns = IdentifierNamespace.objects.get(key="inventory", is_active=True)
    data = {k: v for k, v in row.items() if k not in {"location_id", "category_id"}}
    data["inventory_number"] = normalize(ns, data["inventory_number"])
    for field in ("condition", "lifecycle"):
        if not data.get(field):
            data.pop(field, None)
    for field in ("acquisition_date", "acquisition_value"):
        if field in data and not data[field]:
            data[field] = None
    candidate = Asset(location=location, category=category, **data)
    require(actor, "asset.import", asset_scope(candidate))
    require(actor, "asset.manage", asset_scope(candidate))
    if "serial_number" in data or "internal_notes" in data:
        require(actor, "asset.read_sensitive", asset_scope(candidate))
    if "acquisition_value" in data:
        require(actor, "asset.read_financial", asset_scope(candidate))
    if candidate.lifecycle == "retired":
        require(actor, "asset.archive", asset_scope(candidate))
    candidate.full_clean()
    if Identifier.objects.filter(namespace=ns, canonical_value=candidate.inventory_number).exists():
        raise ValidationError("Inventarnummer bereits verwendet oder stillgelegt.")
    return {**data, "location": location, "category": category}


def preview_import(actor, upload):
    if upload.size > 512 * 1024:
        raise ValidationError("CSV: maximal 512 KiB und 200 Zeilen.")
    try:
        text = upload.read(512 * 1024 + 1).decode("utf-8-sig")
        if len(text.encode()) > 512 * 1024 or "\x00" in text:
            raise ValueError
        reader = csv.DictReader(io.StringIO(text))
        fields = reader.fieldnames
        if (
            not fields
            or len(fields) != len(set(fields))
            or set(fields) - set(CORE_FIELDS + PRIVATE_FIELDS)
        ):
            raise ValueError
        rows: list[dict[str, str]] = []
        numbers = set()
        for index, row in enumerate(reader, start=2):
            if len(rows) >= 200 or None in row or any(v is None for v in row.values()):
                raise ValueError
            data = validate_row(actor, row)
            if data["inventory_number"] in numbers:
                raise ValidationError(f"Zeile {index}: doppelte Inventarnummer innerhalb der CSV.")
            numbers.add(data["inventory_number"])
            rows.append({**row, "inventory_number": data["inventory_number"]})
        if not rows:
            raise ValueError
    except (UnicodeError, csv.Error, ValueError, TypeError) as exc:
        raise ValidationError(
            "Ungültige CSV. Bitte UTF-8-Datei mit den vorgegebenen Spalten verwenden."
        ) from exc
    with authorization_write():
        # Final preview rechecks authorization under the same lock as future import commit.
        for row in rows:
            validate_row(actor, row)
        return ImportPreview.objects.create(
            actor=actor, rows=rows, expires_at=timezone.now() + timedelta(hours=1)
        )


def commit_import(actor, preview_id):
    with authorization_write():
        preview = ImportPreview.objects.get(pk=preview_id, actor=actor)
        if preview.committed_at:
            for pk in preview.created_asset_ids:
                read_asset(actor, pk, "asset.import")
            return preview.created_asset_ids
        if preview.expires_at <= timezone.now():
            raise ValidationError("Die Vorschau ist abgelaufen. Bitte erneut hochladen.")
        data = [validate_row(actor, row) for row in preview.rows]
        ids = [str(save_asset(actor, row).pk) for row in data]
        preview.created_asset_ids, preview.committed_at = ids, timezone.now()
        preview.save(update_fields=["created_asset_ids", "committed_at"])
        audit(actor, "asset.csv_imported", object_id=preview.pk, details={"count": len(ids)})
        return ids


def safe_cell(value):
    value = "" if value is None else str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def export_csv(actor, queryset=None, include_private=False):
    assets = visible_assets(actor) if queryset is None else queryset
    out = io.StringIO(newline="")
    columns = CORE_FIELDS + (PRIVATE_FIELDS if include_private else [])
    writer = csv.writer(out)
    writer.writerow(columns)
    count = 0
    for asset in assets:
        scope = asset_scope(asset)
        # Callers cannot pass an unfiltered queryset to evade the service's read/export checks.
        if not allowed(actor, "asset.read", scope) or not allowed(actor, "asset.export", scope):
            continue
        values = []
        for column in columns:
            if column in {"serial_number", "internal_notes"} and not allowed(
                actor, "asset.read_sensitive", scope
            ):
                value = ""
            elif column == "acquisition_value" and not allowed(
                actor, "asset.read_financial", scope
            ):
                value = ""
            else:
                value = getattr(asset, column)
            values.append(safe_cell(value))
        writer.writerow(values)
        count += 1
    audit(
        actor,
        "asset.csv_exported",
        details={"count": count, "private_columns_requested": include_private},
    )
    return out.getvalue()
