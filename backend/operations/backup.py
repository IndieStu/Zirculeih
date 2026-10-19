"""Authenticated offline bundle; never runs SQL or reads deployment secrets."""

import hashlib
import json
import os
import secrets
import shutil
import stat
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"DEELVO-BACKUP\x00\x01"
CHUNK = 1024 * 1024
# GCM's per-message plaintext bound is below 64 GiB. This format deliberately caps at 16 GiB.
MAX_BYTES = 16 * 1024**3
MAX_FILES = 100000


class BackupError(ValueError):
    pass


def private_file(path, mode="xb"):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), mode)


def key(path):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        raise BackupError("Key must be a regular owner-only file.")
    value = path.read_bytes()
    if len(value) != 32:
        raise BackupError("A separate 32-byte random key is required.")
    return value


def create_key(path):
    with private_file(path) as stream:
        stream.write(secrets.token_bytes(32))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and str(path) == name
        and not any(ord(c) < 32 for c in name)
    )


def pack(dump, media, output, key_file, *, build, maintenance_confirmed=False):
    if not maintenance_confirmed:
        raise BackupError("Stop every writer and explicitly confirm the consistent snapshot.")
    dump, media, output = Path(dump), Path(media), Path(output)
    secret = key(key_file)
    if not dump.is_file() or dump.is_symlink() or not media.is_dir() or media.is_symlink():
        raise BackupError("Regular dump and media directory required.")
    if output.exists() or output.resolve().is_relative_to(media.resolve()):
        raise BackupError("New output outside media required.")
    if Path(key_file).resolve().is_relative_to(media.resolve()):
        raise BackupError("Key must be stored separately, outside media.")
    files = {"database.dump": dump}
    for path in sorted(media.rglob("*")):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise BackupError("Special files and symbolic links are forbidden.")
        if path.is_file():
            name = "media/" + path.relative_to(media).as_posix()
            if not safe_name(name):
                raise BackupError("Unsafe file name.")
            files[name] = path
    if len(files) > MAX_FILES or sum(p.stat().st_size for p in files.values()) > MAX_BYTES - CHUNK:
        raise BackupError(
            "Bundle limit exceeded; use an independently reviewed larger backup tool."
        )
    manifest: dict[str, Any] = {
        "format": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "build": str(build)[:100],
        "files": {n: {"bytes": p.stat().st_size, "sha256": digest(p)} for n, p in files.items()},
    }
    with tempfile.TemporaryDirectory(prefix="deelvo-backup-") as work:
        archive = Path(work) / "snapshot.tar"
        # TemporaryDirectory is owner-only; archived plaintext never enters a public path.
        with tarfile.open(archive, "w", format=tarfile.PAX_FORMAT) as tar:
            import io

            content = json.dumps(manifest, sort_keys=True).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size, info.mode = len(content), 0o600
            tar.addfile(info, io.BytesIO(content))
            for name, path in files.items():
                info = tarfile.TarInfo(name)
                info.size, info.mode = path.stat().st_size, 0o600
                with path.open("rb") as stream:
                    tar.addfile(info, stream)
                if digest(path) != manifest["files"][name]["sha256"]:
                    raise BackupError("Source changed during backup; stop writers and retry.")
        if archive.stat().st_size > MAX_BYTES:
            raise BackupError("Bundle limit exceeded.")
        nonce = secrets.token_bytes(12)
        header = MAGIC + nonce
        encryptor = Cipher(algorithms.AES(secret), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(header)
        target = private_file(output)
        try:
            with target, archive.open("rb") as source:
                target.write(header)
                for block in iter(lambda: source.read(CHUNK), b""):
                    target.write(encryptor.update(block))
                target.write(encryptor.finalize())
                target.write(encryptor.tag)
                target.flush()
                os.fsync(target.fileno())
        except Exception:
            # Only the exclusively-created partial output belongs to this operation.
            if output.exists():
                output.unlink()
            raise
    return {"files": len(files), "bytes": output.stat().st_size, "sha256": digest(output)}


def unpack(bundle, destination, key_file):
    bundle, destination = Path(bundle), Path(destination)
    secret = key(key_file)
    if destination.exists() or destination.is_symlink():
        raise BackupError("Destination must not exist; existing data is never overwritten.")
    if bundle.stat().st_size > MAX_BYTES + len(MAGIC) + 28:
        raise BackupError("Bundle limit exceeded.")
    from cryptography.exceptions import InvalidTag

    with tempfile.TemporaryDirectory(prefix="deelvo-restore-", dir=destination.parent) as work:
        work_dir = Path(work)
        plain = work_dir / "authenticated.tar"
        with bundle.open("rb") as source:
            header = source.read(len(MAGIC) + 12)
            if not header.startswith(MAGIC) or len(header) != len(MAGIC) + 12:
                raise BackupError("Unsupported backup format.")
            size = bundle.stat().st_size - len(header) - 16
            if size < 0:
                raise BackupError("Truncated backup.")
            source.seek(-16, 2)
            tag = source.read(16)
            source.seek(len(header))
            decryptor = Cipher(algorithms.AES(secret), modes.GCM(header[-12:], tag)).decryptor()
            decryptor.authenticate_additional_data(header)
            try:
                with private_file(plain) as target:
                    remaining = size
                    while remaining:
                        block = source.read(min(CHUNK, remaining))
                        if not block:
                            raise BackupError("Truncated backup.")
                        remaining -= len(block)
                        target.write(decryptor.update(block))
                    target.write(decryptor.finalize())
            except InvalidTag as exc:
                raise BackupError("Backup authentication failed; no files restored.") from exc
        restored = work_dir / "verified"
        restored.mkdir(mode=0o700)
        try:
            with tarfile.open(plain, "r:") as tar:
                members = []
                for member in tar:
                    members.append(member)
                    if len(members) > MAX_FILES + 1:
                        raise BackupError("Too many archived files.")
                if any(not m.isfile() or m.size < 0 or not safe_name(m.name) for m in members):
                    raise BackupError("Unsafe archive entry.")
                names = [m.name for m in members]
                if len(set(names)) != len(names) or "manifest.json" not in names:
                    raise BackupError("Duplicate entries or missing manifest.")
                manifest_member = tar.getmember("manifest.json")
                if manifest_member.size > 16 * CHUNK:
                    raise BackupError("Manifest too large.")
                manifest_stream = tar.extractfile(manifest_member)
                assert manifest_stream is not None
                manifest = json.load(manifest_stream)
                if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
                    raise BackupError("Invalid manifest.")
                if (
                    type(manifest.get("format")) is not int
                    or not isinstance(manifest.get("build"), str)
                    or len(manifest["build"]) > 100
                ):
                    raise BackupError("Invalid manifest identity.")
                expected = manifest["files"]
                if manifest.get("format") != 1 or set(names) != {"manifest.json", *expected}:
                    raise BackupError("Invalid manifest.")
                if "database.dump" not in expected or any(
                    n != "database.dump" and not n.startswith("media/") for n in expected
                ):
                    raise BackupError("Invalid backup paths.")
                if sum(m.size for m in members) > MAX_BYTES:
                    raise BackupError("Expanded size limit exceeded.")
                for member in members:
                    target = restored / member.name
                    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    with private_file(target) as stream:
                        member_stream = tar.extractfile(member)
                        assert member_stream is not None
                        shutil.copyfileobj(member_stream, stream, CHUNK)
                    if member.name != "manifest.json" and (
                        member.size != expected[member.name]["bytes"]
                        or digest(target) != expected[member.name]["sha256"]
                    ):
                        raise BackupError("Snapshot hash mismatch.")
            (restored / "media").mkdir(mode=0o700, exist_ok=True)
            # Reserve destination atomically so a concurrently created target cannot be replaced.
            destination.mkdir(mode=0o700)
            try:
                for child in restored.iterdir():
                    child.rename(destination / child.name)
            except Exception:
                shutil.rmtree(destination)
                raise
        except (tarfile.TarError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise BackupError("Malformed backup manifest/archive.") from exc
    return {"files": len(expected), "build": manifest["build"]}
