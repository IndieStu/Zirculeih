import io
import json
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.test import override_settings
from operations import backup
from operations.checks import configuration_problems

from scripts.secret_check import scan


@pytest.fixture
def snapshot(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "image.jpg").write_bytes(b"synthetic-media-bytes")
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"PGDMP-synthetic-only-not-a-real-postgres-dump")
    key = tmp_path / "secret-key"
    backup.create_key(key)
    return dump, media, key, tmp_path / "snapshot.deelvo"


def packed(c):
    dump, media, key, path = c
    return backup.pack(dump, media, path, key, build="synthetic-test", maintenance_confirmed=True)


def test_encrypted_round_trip_and_private_files(snapshot, tmp_path):
    report = packed(snapshot)
    assert report["files"] == 2
    raw = snapshot[3].read_bytes()
    assert b"synthetic-media" not in raw and b"PGDMP" not in raw
    result = backup.unpack(snapshot[3], tmp_path / "restored", snapshot[2])
    assert result["files"] == 2
    assert (tmp_path / "restored/media/image.jpg").read_bytes() == b"synthetic-media-bytes"
    assert (snapshot[3].stat().st_mode & 0o777) == 0o600
    assert ((tmp_path / "restored/database.dump").stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize("position", [0, 20, -1, -30])
def test_tamper_never_extracts(snapshot, tmp_path, position):
    packed(snapshot)
    raw = bytearray(snapshot[3].read_bytes())
    raw[position] ^= 1
    snapshot[3].write_bytes(raw)
    target = tmp_path / "rejected"
    with pytest.raises(backup.BackupError):
        backup.unpack(snapshot[3], target, snapshot[2])
    assert not target.exists()
    assert not list(tmp_path.glob("deelvo-restore-*"))


def test_wrong_key_and_existing_destination(snapshot, tmp_path):
    packed(snapshot)
    other = tmp_path / "other-key"
    backup.create_key(other)
    with pytest.raises(backup.BackupError):
        backup.unpack(snapshot[3], tmp_path / "wrong", other)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep").write_text("keep")
    with pytest.raises(backup.BackupError):
        backup.unpack(snapshot[3], existing, snapshot[2])
    assert (existing / "keep").read_text() == "keep"


def test_snapshot_quiescence_key_permissions_and_symlinks(snapshot, tmp_path):
    dump, media, key, output = snapshot
    with pytest.raises(backup.BackupError):
        backup.pack(dump, media, output, key, build="synthetic")
    key.chmod(0o644)
    with pytest.raises(backup.BackupError):
        packed(snapshot)
    key.chmod(0o600)
    (media / "link").symlink_to(dump)
    with pytest.raises(backup.BackupError):
        packed(snapshot)
    assert not output.exists()


def test_existing_output_never_removed(snapshot):
    snapshot[3].write_bytes(b"keep-original")
    with pytest.raises(backup.BackupError):
        packed(snapshot)
    assert snapshot[3].read_bytes() == b"keep-original"


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "media/../escape",
        "media//a",
        "media/./a",
        "media\\a",
        "bad\x00name",
    ],
)
def test_unsafe_archive_names_rejected(name):
    assert not backup.safe_name(name)


def test_secret_detector_reports_location_not_value(tmp_path):
    token = "dv1_" + "X" * 43
    path = tmp_path / "synthetic-secret.txt"
    path.write_text(token)
    result = scan([path])
    assert result == [dict(file=str(path), line=1, kind="deelvo_raw_token")]
    assert token not in json.dumps(result)


def test_production_configuration_fails_closed(settings):
    data = {
        name: getattr(settings, name)
        for name in [
            "DEPLOYMENT_PROFILE",
            "RESTORE_MODE",
            "REVIEW_MODE",
            "DEBUG",
            "SECURE_SSL_REDIRECT",
            "SESSION_COOKIE_SECURE",
            "CSRF_COOKIE_SECURE",
            "SECURE_HSTS_SECONDS",
            "PRIVACY_NOTICE_TEXT",
            "PRIVACY_NOTICE_VERSION",
            "OIDC_ENABLED",
            "ALLOWED_HOSTS",
            "PUBLIC_BASE_URL",
        ]
    }
    data["DEPLOYMENT_PROFILE"] = "production"
    issues = dict(configuration_problems(SimpleNamespace(**data)))
    assert {"E014", "E015", "E016", "E017", "E018"} <= issues.keys()
    data.update(
        DEBUG=False,
        REVIEW_MODE=False,
        RESTORE_MODE=False,
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=3600,
        PRIVACY_NOTICE_TEXT="Synthetic operator text",
        PRIVACY_NOTICE_VERSION="synthetic",
        OIDC_ENABLED=True,
        ALLOWED_HOSTS=["deelvo.example.test"],
        PUBLIC_BASE_URL="https://deelvo.example.test",
    )
    assert not configuration_problems(SimpleNamespace(**data))
    data.update(RESTORE_MODE=True)
    assert "E011" in dict(configuration_problems(SimpleNamespace(**data)))


@pytest.mark.django_db
@pytest.mark.postgres
def test_restore_mode_never_consumes_outbox(configured):
    from uuid import uuid4

    from bookings.services import confirm
    from notifications.models import Delivery
    from notifications.services import deliver_due, deliver_one

    c = configured
    confirm(c[4], c[1].pk, c[5], c[6], uuid4())
    row = Delivery.objects.first()
    assert row
    before = list(Delivery.objects.values())
    with override_settings(RESTORE_MODE=True):
        assert deliver_one(row.pk, sender=lambda *args: pytest.fail("No external mail")) is False
        assert deliver_due() == 0
    assert list(Delivery.objects.values()) == before


@pytest.mark.django_db
@pytest.mark.postgres
def test_readiness_is_safe_and_checks_schema():
    out = io.StringIO()
    call_command("deployment_readiness", stdout=out)
    data = json.loads(out.getvalue())
    assert data["schema_current"] and not data["errors"]
    assert data["external_integrations_verified"] is False


def test_sbom_matches_reviewed_locks():
    from scripts.security_inventory import locked, sbom

    result = sbom()
    assert len(result["components"]) == len(locked()) == 28
    assert all(c["hashes"] and c["licenses"] for c in result["components"])
    assert result["metadata"]["component"]["licenses"] == [{"expression": "AGPL-3.0-or-later"}]


from test_bookings import configured as configured_fixture  # noqa: E402

configured = configured_fixture


@pytest.mark.django_db
@pytest.mark.postgres
def test_thousand_asset_api_query_budget(staff, registry):
    from time import perf_counter

    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from inventory.models import Asset
    from test_phase11 import access, http

    Asset.objects.bulk_create(
        [
            Asset(
                inventory_number=f"LOAD-{i:04}",
                name="Synthetic load fixture",
                location=registry[1],
                category=registry[2],
            )
            for i in range(1000)
        ]
    )
    _, _, raw = access(staff, ["inventory.read"])
    started = perf_counter()
    with CaptureQueriesContext(connection) as queries:
        response = http(raw).get("/api/v1/assets/?page_size=30")
    assert response.status_code == 200 and response.json()["count"] == 1001
    assert len(queries) <= 40
    print(
        json.dumps(
            dict(
                synthetic_assets=1001,
                query_count=len(queries),
                elapsed_ms=round((perf_counter() - started) * 1000, 2),
            )
        )
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_twenty_api_contenders_one_allocation(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4

    from bookings.models import Booking
    from django.db import close_old_connections
    from test_phase11 import access, http, period, post

    _, _, raw = access(configured[4], ["bookings.create"], readonly=False)
    data = period(configured)
    barrier = Barrier(20)

    def worker(_):
        close_old_connections()
        try:
            barrier.wait(timeout=30)
            return post(http(raw), "bookings/", data, HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(pool.map(worker, range(20)))
    assert statuses.count(201) == 1 and statuses.count(422) == 19
    assert Booking.objects.count() == 1


@pytest.mark.parametrize(
    "kind", ["traversal", "symlink", "duplicate", "wrong_hash", "missing_build"]
)
def test_authenticated_malformed_archive_is_never_published(snapshot, tmp_path, kind):
    import tarfile

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    stream = io.BytesIO()
    name = "../outside" if kind == "traversal" else "database.dump"
    manifest = dict(format=1, build="synthetic", files={name: {"bytes": 1, "sha256": "0" * 64}})
    if kind == "missing_build":
        manifest.pop("build")
    with tarfile.open(fileobj=stream, mode="w") as tar:
        raw = json.dumps(manifest).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
        info = tarfile.TarInfo(name)
        info.size = 1
        if kind == "symlink":
            info.type = tarfile.SYMTYPE
            info.linkname = "../outside"
            info.size = 0
        tar.addfile(info, io.BytesIO(b"x"))
        if kind == "duplicate":
            tar.addfile(info, io.BytesIO(b"x"))
    header = backup.MAGIC + bytes(range(12))
    cipher = Cipher(algorithms.AES(snapshot[2].read_bytes()), modes.GCM(header[-12:])).encryptor()
    cipher.authenticate_additional_data(header)
    encoded = header + cipher.update(stream.getvalue()) + cipher.finalize() + cipher.tag
    snapshot[3].write_bytes(encoded)
    target = tmp_path / "unsafe"
    with pytest.raises(backup.BackupError):
        backup.unpack(snapshot[3], target, snapshot[2])
    assert not target.exists() and not (tmp_path / "outside").exists()


def test_unsafe_production_profile_refuses_startup():
    import os
    import subprocess
    import sys

    env = dict(
        os.environ,
        DEELVO_DEPLOYMENT_PROFILE="production",
        DEELVO_RESTORE_MODE="false",
        OIDC_ENABLED="false",
        DJANGO_DEBUG="false",
        DJANGO_HSTS_SECONDS="0",
    )
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Unsafe production configuration" in result.stderr


@pytest.mark.parametrize("raw", ['"secret"', "null", '["too-short"]', "not-json", "[1]"])
def test_signing_fallback_configuration_rejects_invalid_input(raw):
    from config.settings import secret_fallbacks
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured):
        secret_fallbacks(raw)


def test_signing_fallback_configuration_supports_planned_rotation():
    from config.settings import secret_fallbacks

    assert secret_fallbacks("[]") == []
    assert secret_fallbacks(json.dumps(["synthetic-old-" + "x" * 50])) == [
        "synthetic-old-" + "x" * 50
    ]


def test_old_outbox_key_can_be_kept_explicitly_during_rotation():
    from django.core.exceptions import ValidationError
    from notifications.services import _cipher, decrypt

    old, new = "synthetic-old-" + "x" * 50, "synthetic-new-" + "y" * 50
    body = {"body": "Fictional recovery message"}
    encrypted = _cipher(old).encrypt(json.dumps(body).encode())
    with override_settings(SECRET_KEY=new, SECRET_KEY_FALLBACKS=[old]):
        assert decrypt(encrypted) == body
    with override_settings(SECRET_KEY=new, SECRET_KEY_FALLBACKS=[]):
        with pytest.raises(ValidationError):
            decrypt(encrypted)


def test_restore_profile_cannot_start_without_mail_protection():
    import os
    import subprocess
    import sys

    env = dict(os.environ, DEELVO_DEPLOYMENT_PROFILE="restore", DEELVO_RESTORE_MODE="false")
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "E002" in result.stderr
