"""Explicit isolated native PostgreSQL/media recovery drill, local or disposable CI Compose."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from operations import backup  # noqa: E402


def run(args, *, env=None, output=None, input_file=None):
    result = subprocess.run(
        args,
        env=env,
        stdin=input_file,
        stdout=output or subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        # Tool output can contain connection strings or restored records; never print it.
        raise RuntimeError("Isolated drill command failed: " + Path(args[0]).name)
    return result.stdout.decode() if output is None else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=["local", "compose"], required=True)
    parser.add_argument("--confirm-disposable", action="store_true", required=True)
    parser.add_argument("--project", default="deelvo-dev")
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    if options.adapter == "compose" and options.project != "deelvo-dev":
        parser.error("Only disposable deelvo-dev CI is supported; never a review/production stack.")
    marker = uuid4().hex
    source, target = "deelvo_drill_src_" + marker, "deelvo_drill_dst_" + marker
    compose = ["docker", "compose", "--project-name", options.project]
    user = os.environ.get("POSTGRES_USER", "deelvo")
    if options.adapter == "local":
        for suffix in ["HOST", "PORT", "USER", "PASSWORD"]:
            if "POSTGRES_" + suffix in os.environ:
                os.environ["PG" + suffix] = os.environ["POSTGRES_" + suffix]
    started = perf_counter()
    created = []
    with tempfile.TemporaryDirectory(prefix="deelvo-drill-") as work:
        work = Path(work)
        if options.adapter == "compose":
            # Reading the non-secret username only; never load/print the .env secret contents.
            for line in Path(".env").read_text().splitlines():
                if line.startswith("POSTGRES_USER="):
                    user = line.split("=", 1)[1]

            def dbtool(command, *args):
                return [
                    *compose,
                    "exec",
                    "-T",
                    "db",
                    command,
                    "-U",
                    user,
                    *args,
                ]

            def root(name):
                return "/app/media/" + name

            def manage(name, command):
                return run(
                    [
                        *compose,
                        "run",
                        "--rm",
                        "-T",
                        "--no-deps",
                        "-e",
                        "POSTGRES_DB=" + name,
                        "-e",
                        "MEDIA_ROOT=" + root(name),
                        "-e",
                        "DEELVO_REVIEW_MODE=true",
                        "-e",
                        "DEELVO_RESTORE_MODE=true",
                        "-e",
                        "DEELVO_DEPLOYMENT_PROFILE=restore",
                        "-e",
                        "OIDC_ENABLED=false",
                        "web",
                        "python",
                        "backend/manage.py",
                        *command,
                    ]
                )
        else:

            def dbtool(command, *args):
                return [command, "-U", user, *args]

            def root(name):
                return str(work / name)

            def manage(name, command):
                env = dict(
                    os.environ,
                    POSTGRES_DB=name,
                    MEDIA_ROOT=root(name),
                    DEELVO_REVIEW_MODE="true",
                    DEELVO_RESTORE_MODE="true",
                    DEELVO_DEPLOYMENT_PROFILE="restore",
                    OIDC_ENABLED="false",
                )
                return run([sys.executable, "backend/manage.py", *command], env=env)

        try:
            for name in [source, target]:
                run(dbtool("createdb", name))
                created.append(name)
            manage(source, ["migrate", "--noinput"])
            manage(source, ["seed_review_data", "--date", "2030-01-15"])
            before = json.loads(manage(source, ["verify_restore_drill"]).strip().splitlines()[-1])
            dump = work / "database.dump"
            with dump.open("xb") as output:
                run(
                    dbtool("pg_dump", "--format=custom", "--no-owner", "--no-acl", source),
                    output=output,
                )
            snapshot = work / "media"
            if options.adapter == "compose":
                run([*compose, "cp", "web:" + root(source), str(snapshot)])
            else:
                shutil.copytree(root(source), snapshot)
            key = work / "key"
            backup.create_key(key)
            envelope = work / "snapshot.deelvo"
            bundle = backup.pack(
                dump, snapshot, envelope, key, build="phase-12-drill", maintenance_confirmed=True
            )
            restore_started = perf_counter()
            restored = work / "restored"
            backup.unpack(envelope, restored, key)
            # New target database only; no --clean, no replacement of an existing schema.
            with (restored / "database.dump").open("rb") as stream:
                run(
                    dbtool(
                        "pg_restore",
                        "--exit-on-error",
                        "--no-owner",
                        "--no-acl",
                        "--dbname",
                        target,
                    ),
                    input_file=stream,
                )
            if options.adapter == "compose":
                # Restore as the real app UID. No chown capability/root exec is required.
                media_tar = work / "restored-media.tar"
                with tarfile.open(media_tar, "w") as archive:
                    archive.add(restored / "media", arcname=".")
                extractor = """import pathlib, sys, tarfile
root = pathlib.Path(sys.argv[1])
root.mkdir(mode=0o700)
with tarfile.open(fileobj=sys.stdin.buffer, mode='r|') as archive:
    archive.extractall(root, filter='data')
"""
                with media_tar.open("rb") as stream:
                    run(
                        [*compose, "exec", "-T", "web", "python", "-c", extractor, root(target)],
                        input_file=stream,
                    )
            else:
                shutil.copytree(restored / "media", root(target))
            after = json.loads(manage(target, ["verify_restore_drill"]).strip().splitlines()[-1])
            if before != after:
                print(
                    json.dumps(
                        {
                            "mismatched_fields": {
                                k: [before[k], after[k]] for k in before if before[k] != after[k]
                            }
                        }
                    )
                )
                raise RuntimeError(
                    "Restored DB/media/guards differ from the stopped-write snapshot."
                )
            manage(target, ["deployment_readiness"])
            report = dict(
                adapter=options.adapter,
                fictional_only=True,
                native_postgres_dump_restore=True,
                authenticated_encryption=True,
                source_target_equal=True,
                restore_seconds=round(perf_counter() - restore_started, 3),
                total_seconds=round(perf_counter() - started, 3),
                bundle_bytes=bundle["bytes"],
                **after,
            )
            options.output.parent.mkdir(parents=True, exist_ok=True)
            options.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report))
        finally:
            # Only UUID names created by this process; no existing database is ever dropped.
            for name in reversed(created):
                run(dbtool("dropdb", name))
            if options.adapter == "compose":
                # Fixture media remains in the disposable CI volume until compose cleanup;
                # never recursively remove paths in an existing deployment.
                pass


if __name__ == "__main__":
    main()
