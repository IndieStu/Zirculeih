import csv
import io
from unittest.mock import patch

import pytest
from accounts.models import AuditEvent, Grant
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from inventory import csvio, extensions, services
from inventory.models import (
    Asset,
    AssetMedia,
    CustomFieldDefinition,
    CustomFieldValue,
    ImportPreview,
)
from PIL import Image
from test_inventory import limited_user

pytestmark = [pytest.mark.django_db, pytest.mark.postgres]


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("text", "Werkstatt", "Werkstatt"),
        ("number", "12.5000", "12.5000"),
        ("date", "2026-10-15", "2026-10-15"),
        ("boolean", "false", "False"),
        ("enum", "A", "A"),
        ("url", "https://example.test/manual", "https://example.test/manual"),
    ],
)
def test_typed_custom_fields(staff, registry, kind, value, expected):
    field = extensions.create_field(
        staff,
        {
            "key": "typed",
            "label": "Feld",
            "kind": kind,
            "options": ["A", "B"] if kind == "enum" else [],
        },
    )
    row = extensions.set_custom_value(staff, registry[3].pk, field.pk, value, registry[3].revision)
    assert str(row.value) == expected
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomFieldDefinition.objects.filter(pk=field.pk).update(
            kind="boolean" if kind != "boolean" else "date"
        )


@pytest.mark.parametrize(
    "kind,value",
    [
        ("number", "NaN"),
        ("number", "Infinity"),
        ("date", "invalid"),
        ("boolean", "yes"),
        ("enum", "unknown"),
        ("url", "javascript:alert(1)"),
    ],
)
def test_invalid_custom_values_rejected(staff, registry, kind, value):
    field = extensions.create_field(
        staff,
        {"key": "typed", "label": "Feld", "kind": kind, "options": ["A"] if kind == "enum" else []},
    )
    with pytest.raises(ValidationError):
        extensions.set_custom_value(staff, registry[3].pk, field.pk, value, registry[3].revision)
    assert not CustomFieldValue.objects.exists()


def test_sensitive_custom_field_and_direct_sql_type_guard(staff, registry):
    field = extensions.create_field(
        staff, {"key": "private", "label": "Privat", "kind": "number", "is_sensitive": True}
    )
    extensions.set_custom_value(staff, registry[3].pk, field.pk, "1", registry[3].revision)
    user, _ = limited_user(registry[0], manage=True)
    assert not extensions.visible_custom_values(user, registry[3]).exists()
    with pytest.raises(PermissionDenied):
        extensions.set_custom_value(user, registry[3].pk, field.pk, "2", registry[3].revision + 1)
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomFieldValue.objects.filter(definition=field).update(
            value_number=None, value_text="invalid"
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomFieldDefinition.objects.filter(pk=field.pk).update(is_sensitive=False)


def image_upload():
    output = io.BytesIO()
    Image.new("RGB", (30, 20), "blue").save(
        output, format="JPEG", exif=b"Exif\x00\x00private-location-metadata"
    )
    return SimpleUploadedFile(
        "photo.jpg", output.getvalue() + b"<script>trailer</script>", "text/html"
    )


def test_private_media_decode_metadata_and_permissions(staff, registry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    row = extensions.upload_media(staff, registry[3].pk, image_upload())
    assert row.content_type == "image/jpeg" and row.is_sensitive
    stored = (tmp_path / row.storage_name).read_bytes()
    assert b"private-location-metadata" not in stored and b"<script>" not in stored
    assert extensions.read_media(staff, row.pk).pk == row.pk
    user, _ = limited_user(registry[0])
    with pytest.raises(PermissionDenied):
        extensions.read_media(user, row.pk)
    extensions.archive_media(staff, row.pk)
    assert (
        tmp_path / row.storage_name
    ).exists()  # archival preserves backup/history, no destructive delete.
    with pytest.raises(AssetMedia.DoesNotExist):
        extensions.read_media(staff, row.pk)


@pytest.mark.parametrize(
    "name,payload",
    [
        ("script.svg", b"<svg onload='x'>"),
        ("fake.png", b"not image"),
        ("report.pdf", b"%PDF-1.7"),
        ("run.py", b"print(1)"),
        ("binary.txt", b"abc\x00def"),
        ("bad.txt", b"\xff"),
    ],
)
def test_malicious_uploads_rejected(staff, registry, settings, tmp_path, name, payload):
    settings.MEDIA_ROOT = tmp_path
    with pytest.raises(ValidationError):
        extensions.upload_media(staff, registry[3].pk, SimpleUploadedFile(name, payload))
    assert not AssetMedia.objects.exists() and not list(tmp_path.rglob("*"))


def test_oversized_and_decompression_image_rejected(staff, registry):
    with pytest.raises(ValidationError):
        extensions.upload_media(
            staff, registry[3].pk, SimpleUploadedFile("large.txt", b"x" * (5 * 1024 * 1024 + 1))
        )
    with patch(
        "inventory.extensions.Image.open", side_effect=Image.DecompressionBombWarning("test")
    ):
        with pytest.raises(ValidationError):
            extensions.upload_media(staff, registry[3].pk, image_upload())


def test_failed_media_database_write_cleans_storage(staff, registry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch(
        "inventory.extensions.AssetMedia.objects.create", side_effect=IntegrityError("test")
    ):
        with pytest.raises(IntegrityError):
            extensions.upload_media(staff, registry[3].pk, image_upload())
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]


def csv_upload(registry, numbers=("CSV-1", "CSV-2")):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(csvio.CORE_FIELDS)
    for number in numbers:
        writer.writerow(
            [
                number,
                "Import",
                "Beschreibung",
                str(registry[1].pk),
                str(registry[2].pk),
                "",
                "",
                "good",
                "active",
            ]
        )
    return SimpleUploadedFile("assets.csv", output.getvalue().encode())


def test_csv_preview_then_atomic_commit_and_retry(staff, registry):
    before = Asset.objects.count()
    preview = csvio.preview_import(staff, csv_upload(registry))
    assert Asset.objects.count() == before
    ids = csvio.commit_import(staff, preview.pk)
    assert len(ids) == 2 and Asset.objects.count() == before + 2
    assert csvio.commit_import(staff, preview.pk) == ids
    assert Asset.objects.count() == before + 2
    assert AuditEvent.objects.filter(action="asset.csv_imported").count() == 1


def test_csv_conflict_at_commit_no_partial_import(staff, registry):
    preview = csvio.preview_import(staff, csv_upload(registry))
    services.save_asset(
        staff,
        {
            "inventory_number": "CSV-2",
            "name": "Conflicting",
            "location": registry[1],
            "category": registry[2],
        },
    )
    with pytest.raises(ValidationError):
        csvio.commit_import(staff, preview.pk)
    assert not Asset.objects.filter(inventory_number="CSV-1").exists()
    preview.refresh_from_db()
    assert preview.committed_at is None


def test_csv_owner_scope_and_permission_recheck(staff, registry):
    preview = csvio.preview_import(staff, csv_upload(registry))
    user, group = limited_user(registry[0])
    with pytest.raises(ImportPreview.DoesNotExist):
        csvio.commit_import(user, preview.pk)
    Grant.objects.filter(action="asset.import").delete()
    with pytest.raises(PermissionDenied):
        csvio.commit_import(staff, preview.pk)
    assert not Asset.objects.filter(inventory_number="CSV-1").exists()


def test_csv_export_redacts_private_and_neutralizes_formulas(staff, registry):
    services.save_asset(
        staff,
        {"name": "=HYPERLINK(attacker)"},
        asset_id=registry[3].pk,
        expected_revision=registry[3].revision,
    )
    user, group = limited_user(registry[0])
    Grant.objects.create(group=group, action="asset.export", effect="allow")
    exported = csvio.export_csv(user, include_private=True)
    assert (
        "PRIVATE-SERIAL" not in exported
        and "PRIVATE-NOTE" not in exported
        and "100.00" not in exported
    )
    rows = list(csv.DictReader(io.StringIO(exported)))
    assert rows[0]["name"].startswith("'=")
    assert "PRIVATE-SERIAL" in csvio.export_csv(staff, include_private=True)
    Grant.objects.filter(group=group, action="asset.export").delete()
    assert len(list(csv.DictReader(io.StringIO(csvio.export_csv(user))))) == 0
