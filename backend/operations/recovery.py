"""Non-secret recovery assertions for explicitly disposable drill databases only."""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from inventory.models import AssetMedia
from lending.models import AgreementVersion, LoanLine
from notifications.models import Delivery
from notifications.services import decrypt, deliver_due
from psycopg import sql
from resources.models import ResourceImage

from .backup import digest


def verify_drill():
    if not settings.RESTORE_MODE or not connection.settings_dict["NAME"].startswith(
        "deelvo_drill_"
    ):
        raise CommandError("Only isolated deelvo_drill_* databases in restore mode are permitted.")
    if (
        settings.OIDC_ENABLED
        or settings.EMAIL_BACKEND != "django.core.mail.backends.dummy.EmailBackend"
    ):
        raise CommandError("External integrations must be disabled.")
    if not LoanLine.objects.filter(returned_at=None).exists() or not AssetMedia.objects.exists():
        raise CommandError("Fictional custody and media fixture required.")
    if LoanLine.objects.filter(returned_at=None, loan__closed_at__isnull=False).exists():
        raise CommandError("Inconsistent actual custody.")
    version = AgreementVersion.objects.filter(published_at__isnull=False).first()
    if version is None:
        raise CommandError("Published agreement fixture required.")
    try:
        with transaction.atomic():
            AgreementVersion.objects.filter(pk=version.pk).update(text="Fictional tamper probe")
            raise CommandError("Published evidence guard missing.")
    except IntegrityError:
        pass
    pending_before = list(Delivery.objects.values_list("pk", "status", "attempts", "payload"))
    for row in Delivery.objects.exclude(payload=b""):
        decrypt(row.payload)  # Proves separately retained signing key still decrypts, never output.
    if (
        deliver_due() != 0
        or list(Delivery.objects.values_list("pk", "status", "attempts", "payload"))
        != pending_before
    ):
        raise CommandError("Restore verification must not consume the outbox.")
    media = {}
    for name in [
        *AssetMedia.objects.values_list("storage_name", flat=True),
        *ResourceImage.objects.values_list("storage_name", flat=True),
    ]:
        path = Path(settings.MEDIA_ROOT) / name
        if not path.is_file() or not path.resolve().is_relative_to(
            Path(settings.MEDIA_ROOT).resolve()
        ):
            raise CommandError("Restored referenced media missing.")
        media[name] = digest(path)
    h = hashlib.sha256()
    tables = []
    total = 0
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(
                sql.SQL(
                    "SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text"
                ).format(sql.Identifier(table))
            )
            h.update(table.encode())
            for row in cursor:
                h.update(row[0].encode())
                h.update(b"\n")
                total += 1
        cursor.execute(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal "
            "ORDER BY pg_get_triggerdef(oid)"
        )
        triggers = cursor.fetchall()
        # pg_dump reparses CHECK expressions (array casts may move without semantic change).
        # Compare stable identities/validation flags; actual negative probes exercise guards.
        cursor.execute(
            "SELECT conrelid::regclass::text, conname, contype, condeferrable, "
            "condeferred, convalidated, "
            "(SELECT array_agg(a.attname ORDER BY k.n) FROM unnest(conkey) WITH ORDINALITY k(id,n) "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.id) "
            "FROM pg_constraint c "
            "WHERE contype IN ('x', 'c', 'u', 'f', 'p') AND connamespace = 'public'::regnamespace "
            "ORDER BY conrelid::regclass::text, conname"
        )
        constraints = cursor.fetchall()
        cursor.execute(
            "SELECT proname, prosrc FROM pg_proc WHERE proname LIKE 'deelvo_%' "
            "ORDER BY proname, prosrc"
        )
        functions = cursor.fetchall()
    return dict(
        tables=len(tables),
        rows=total,
        data_sha256=h.hexdigest(),
        media_count=len(media),
        media_sha256=hashlib.sha256(json.dumps(media, sort_keys=True).encode()).hexdigest(),
        guards_sha256=hashlib.sha256(
            json.dumps([triggers, constraints, functions]).encode()
        ).hexdigest(),
        outbox_untouched=True,
        evidence_guard=True,
    )
