import json
from types import SimpleNamespace

import pytest

from scripts.review_upgrade_guard import ROOT, UpgradeBlocked, check_review_database

VOLUME = "deelvo_review_postgres"

CONTAINER = "a" * 64
MANIFEST = json.loads((ROOT / "docs/release/container-images.json").read_text())
DATABASE = next(row for row in MANIFEST["images"] if row["repository"].endswith("/postgres"))
IMAGE = f"postgres:{DATABASE['tag']}@{DATABASE['digest']}"


def docker_probe(
    *,
    existing=True,
    image=IMAGE,
    orphan=False,
    fail=None,
    wrong_mount=False,
    project="deelvo-review",
    volume=VOLUME,
    configured_image=IMAGE,
):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        assert kwargs["capture_output"] and not kwargs["check"]
        if args[0:2] == ("scripts/review-stack", "config"):
            output = json.dumps(
                dict(
                    name=project,
                    services={"db": {"image": configured_image}},
                    volumes={"postgres_data": {"name": volume}},
                )
            )
        elif args[0:3] == ("docker", "volume", "ls"):
            output = volume if existing or orphan else ""
        elif args[0:2] == ("scripts/review-stack", "ps"):
            output = CONTAINER if existing else ""
        elif args[0:4] == ("docker", "inspect", "--format", "{{.Config.Image}}"):
            output = image
        elif args[0:4] == ("docker", "inspect", "--format", "{{json .Mounts}}"):
            output = json.dumps(
                [
                    dict(
                        Type="volume",
                        Name="foreign-volume" if wrong_mount else volume,
                        Destination="/var/lib/postgresql/data",
                    )
                ]
            )
        else:
            raise AssertionError(f"Unexpected/mutating Docker command: {args}")
        return SimpleNamespace(
            returncode=1 if fail == args[1] else 0,
            stdout=output,
            stderr="private-connection-details-not-to-be-printed",
        )

    return run, calls


def test_fresh_review_without_volume_is_allowed():
    run, calls = docker_probe(existing=False)
    assert check_review_database(run) == "fresh_review_database"
    assert len(calls) == 3


def test_same_pinned_database_and_owned_volume_are_allowed():
    run, _ = docker_probe()
    assert check_review_database(run) == "existing_review_database_same_pinned_image"


@pytest.mark.parametrize(
    "options",
    [
        {"image": "postgres:17-bookworm@sha256:" + "b" * 64},
        {"image": "postgres:17-trixie"},
        {"existing": False, "orphan": True},
        {"wrong_mount": True},
        {"fail": "volume"},
        {"fail": "inspect"},
        {"configured_image": "postgres:17"},
        {"project": "unrelated-project"},
        {"volume": "foreign_postgres"},
    ],
)
def test_existing_or_unknown_database_blocks_without_mutation(options):
    run, _ = docker_probe(**options)
    with pytest.raises(UpgradeBlocked) as error:
        check_review_database(run)
    assert "private-connection-details" not in str(error.value)


def test_parallel_review_target_requires_matching_own_pinned_volume():
    run, _ = docker_probe(project="deelvo-review-p13", volume="deelvo_review_p13_postgres")
    assert check_review_database(run) == "existing_review_database_same_pinned_image"
