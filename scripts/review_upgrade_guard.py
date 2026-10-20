"""Read-only guard before reusing the isolated review PostgreSQL volume."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class UpgradeBlocked(Exception):
    pass


def check_review_database(run=subprocess.run):
    def read(*args):
        result = run(args, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode:
            raise UpgradeBlocked("Cannot verify existing database; no update is permitted.")
        return result.stdout.strip()

    manifest = json.loads((ROOT / "docs/release/container-images.json").read_text())
    db = next(row for row in manifest["images"] if row["repository"].endswith("/postgres"))
    expected = f"postgres:{db['tag']}@{db['digest']}"
    config = json.loads(read("scripts/review-stack", "config", "--format", "json"))
    project = config["name"]
    volume = config["volumes"]["postgres_data"]["name"]
    if not re.fullmatch(r"deelvo-review(?:-[a-z0-9]+)*", project) or not re.fullmatch(
        r"deelvo_review(?:_[a-z0-9]+)*_postgres", volume
    ):
        raise UpgradeBlocked("Only an isolated Deelvo review project/volume is supported.")
    if config["services"]["db"]["image"] != expected:
        raise UpgradeBlocked("Review database image differs from the reviewed image manifest.")
    volumes = read(
        "docker", "volume", "ls", "--filter", f"name=^{volume}$", "--format", "{{.Name}}"
    ).splitlines()
    containers = read("scripts/review-stack", "ps", "-a", "-q", "db").splitlines()
    if not containers:
        if volumes:
            raise UpgradeBlocked("Existing database volume has no verifiable container provenance.")
        return "fresh_review_database"
    if len(containers) != 1 or not re.fullmatch(r"[0-9a-f]{12,64}", containers[0]):
        raise UpgradeBlocked("Cannot identify exactly one isolated review database container.")
    container = containers[0]
    image = read("docker", "inspect", "--format", "{{.Config.Image}}", container)
    mounts = json.loads(read("docker", "inspect", "--format", "{{json .Mounts}}", container))
    data_mounts = [m for m in mounts if m.get("Destination") == "/var/lib/postgresql/data"]
    if (
        volumes != [volume]
        or len(data_mounts) != 1
        or data_mounts[0].get("Type") != "volume"
        or data_mounts[0].get("Name") != volume
    ):
        raise UpgradeBlocked("Database volume does not match the isolated review volume.")
    if image != expected:
        raise UpgradeBlocked(
            "Database image changed. Plan a verified logical restore to a new volume, "
            "including collation/index checks; preserve the original volume and rollback source."
        )
    return "existing_review_database_same_pinned_image"


def main():
    try:
        status = check_review_database()
    except (UpgradeBlocked, OSError, ValueError, KeyError, StopIteration):
        raise SystemExit(
            "BLOCKED: review database upgrade provenance could not be verified. "
            "No changes made by this guard. See docs/handbook/production-operations.md "
            "and docs/deployment/REVIEW_INSTANCE.md; do not remove existing volumes."
        ) from None
    print("PASS: " + status)


if __name__ == "__main__":
    main()
