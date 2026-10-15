"""Restrained inventory metadata and private media; no external storage or workflow engine."""

import io
import warnings
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

from accounts.authorization import allowed, authorization_write, require
from accounts.services import audit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.validators import URLValidator
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from .models import AssetMedia, CustomFieldDefinition, CustomFieldValue
from .services import asset_scope, read_asset


def create_field(actor, data):
    with authorization_write():
        require(actor, "custom_field.manage")
        definition = CustomFieldDefinition(**data)
        if (
            not isinstance(definition.options, list)
            or len(definition.options) > 50
            or any(
                not isinstance(v, str) or not v.strip() or len(v) > 120 for v in definition.options
            )
            or len(set(definition.options)) != len(definition.options)
        ):
            raise ValidationError("Auswahl: maximal 50 unterschiedliche, nichtleere Werte.")
        if (definition.kind == "enum") != bool(definition.options):
            raise ValidationError("Nur Auswahlfelder brauchen eine nichtleere Optionsliste.")
        definition.full_clean()
        definition.save()
        audit(
            actor,
            "custom_field.created",
            object_id=definition.pk,
            details={
                "key": definition.key,
                "kind": definition.kind,
                "sensitive": definition.is_sensitive,
            },
        )
        return definition


def set_custom_value(actor, asset_id, definition_id, value, expected_revision):
    with authorization_write():
        asset = read_asset(actor, asset_id, "asset.manage")
        definition = CustomFieldDefinition.objects.get(pk=definition_id, is_active=True)
        if asset.archived_at or asset.revision != expected_revision:
            raise ValidationError("Asset archiviert oder inzwischen geändert. Bitte neu laden.")
        if definition.is_sensitive:
            require(actor, "asset.read_sensitive", asset_scope(asset))
        data: dict[str, Any] = {
            "value_text": None,
            "value_number": None,
            "value_date": None,
            "value_boolean": None,
        }
        try:
            if definition.kind == "number":
                number = Decimal(str(value))
                if not number.is_finite():
                    raise ValueError
                data["value_number"] = number
            elif definition.kind == "date":
                data["value_date"] = date.fromisoformat(str(value))
            elif definition.kind == "boolean":
                if type(value) is not bool and value not in ("true", "false"):
                    raise ValueError
                data["value_boolean"] = value in ("true", True)
            else:
                value = str(value).strip()
                if not value or len(value) > 2000:
                    raise ValueError
                if definition.kind == "enum" and value not in definition.options:
                    raise ValueError
                if definition.kind == "url":
                    URLValidator(schemes=["https", "http"])(value)
                data["value_text"] = value
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise ValidationError("Wert passt nicht zum gewählten Zusatzfeld.") from exc
        row = CustomFieldValue.objects.filter(asset=asset, definition=definition).first()
        if row is None:
            row = CustomFieldValue(asset=asset, definition=definition)
        for field, item in data.items():
            setattr(row, field, item)
        row.full_clean()
        row.save()
        asset.revision += 1
        asset.updated_at = timezone.now()
        asset.save(update_fields=["revision", "updated_at"])
        audit(
            actor,
            "asset.custom_value_updated",
            object_id=asset.pk,
            details={"definition_id": str(definition.pk), "kind": definition.kind},
        )
        return row


def visible_custom_values(actor, asset):
    require(actor, "asset.read", asset_scope(asset))
    qs = asset.custom_values.select_related("definition")
    if not allowed(actor, "asset.read_sensitive", asset_scope(asset)):
        qs = qs.filter(definition__is_sensitive=False)
    return qs


def media_storage():
    # Never bind MEDIA_ROOT to a publicly served static/media URL.
    return FileSystemStorage(location=settings.MEDIA_ROOT)


def sanitize_upload(upload):
    limit = 5 * 1024 * 1024
    if upload.size > limit:
        raise ValidationError("Dateien dürfen höchstens 5 MiB groß sein.")
    raw = upload.read(limit + 1)
    if len(raw) > limit or not raw:
        raise ValidationError("Leere oder zu große Datei.")
    suffix = Path(upload.name).suffix.lower()
    if suffix == ".txt":
        if len(raw) > 1024 * 1024:
            raise ValidationError("Textdokumente dürfen höchstens 1 MiB groß sein.")
        try:
            text = raw.decode("utf-8")
            if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
                raise ValueError
        except (UnicodeError, ValueError) as exc:
            raise ValidationError("Nur UTF-8-Text ohne Binär-/Steuerzeichen.") from exc
        return raw, "text/plain", ".txt", False
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise ValidationError("Erlaubt sind PNG, JPEG und einfache UTF-8-Textdokumente.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=["PNG", "JPEG"]) as image:
                if image.width * image.height > 8_000_000 or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Image dimensions/frames")
                image.load()
                # New pixels-only image drops EXIF/XMP/ICC/text chunks and appended content.
                clean = Image.frombytes("RGB", image.size, image.convert("RGB").tobytes())
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=85, exif=b"", icc_profile=None)
                data = output.getvalue()
                if len(data) > limit:
                    raise ValueError("Output too large")
                return data, "image/jpeg", ".jpg", True
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise ValidationError("Bild ungültig, zu groß oder mehrseitig.") from exc


def upload_media(actor, asset_id, upload, is_sensitive=True):
    asset = read_asset(actor, asset_id, "asset.attach")
    data, content_type, suffix, is_image = sanitize_upload(upload)
    stored = None
    storage = media_storage()
    try:
        with authorization_write():
            asset = read_asset(actor, asset_id, "asset.attach")
            if asset.archived_at or asset.media.filter(archived_at__isnull=True).count() >= 50:
                raise ValidationError("Asset archiviert oder Medienlimit erreicht.")
            stored = storage.save("inventory/" + uuid4().hex + suffix, ContentFile(data))
            row = AssetMedia.objects.create(
                asset=asset,
                storage_name=stored,
                display_name=("Bild" if is_image else "Textdokument") + suffix,
                content_type=content_type,
                size=len(data),
                is_image=is_image,
                is_sensitive=is_sensitive,
                uploaded_by=actor,
            )
            audit(
                actor,
                "asset.media_uploaded",
                object_id=asset.pk,
                details={
                    "media_id": str(row.pk),
                    "type": content_type,
                    "size": len(data),
                    "sensitive": is_sensitive,
                },
            )
            return row
    except Exception:
        if stored:
            storage.delete(stored)
        raise


def read_media(actor, media_id):
    row = AssetMedia.objects.select_related("asset__location", "asset__category").get(
        pk=media_id, archived_at__isnull=True
    )
    require(actor, "asset.read", asset_scope(row.asset))
    if row.is_sensitive:
        require(actor, "asset.read_sensitive", asset_scope(row.asset))
    return row


def archive_media(actor, media_id):
    with authorization_write():
        row = read_media(actor, media_id)
        require(actor, "asset.attach", asset_scope(row.asset))
        row.archived_at = timezone.now()
        row.save(update_fields=["archived_at"])
        audit(
            actor, "asset.media_archived", object_id=row.asset_id, details={"media_id": str(row.pk)}
        )
