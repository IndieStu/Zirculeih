"""Fetch the reviewed Linux CI scanner from its exact official version and checksum."""

import argparse
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(Path("docs/release/audit-tools.json").read_text())["trivy"]
    with urlopen(
        Request(spec["source"], headers={"User-Agent": "Deelvo-release-audit"}), timeout=60
    ) as response:
        data = response.read(256 * 1024 * 1024 + 1)
    if len(data) > 256 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != spec["sha256"]:
        raise SystemExit("Scanner artifact hash mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.getmember("trivy")
        if not member.isfile() or member.size > 256 * 1024 * 1024:
            raise SystemExit("Unexpected scanner archive")
        stream = archive.extractfile(member)
        assert stream is not None
        args.destination.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(
            os.open(args.destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o700), "wb"
        ) as target:
            target.write(stream.read())
    print("Verified official Trivy " + spec["version"] + " CI binary")


if __name__ == "__main__":
    main()
