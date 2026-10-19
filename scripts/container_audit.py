"""Read-only disposable CI image scan. Findings are explicit production release blockers."""

import argparse
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", required=True)
    parser.add_argument("--image", default="deelvo-dev-web")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.image != "deelvo-dev-web":
        parser.error("Only the disposable CI application image is supported.")
    with tempfile.TemporaryDirectory(prefix="deelvo-image-audit-") as work:
        work = Path(work)
        saved, report = work / "image.tar", work / "report.json"
        subprocess.run(["docker", "save", args.image, "--output", str(saved)], check=True)
        subprocess.run(
            [
                args.scanner,
                "image",
                "--input",
                str(saved),
                "--scanners",
                "vuln",
                "--list-all-pkgs",
                "--format",
                "json",
                "--output",
                str(report),
                "--no-progress",
                "--timeout",
                "5m",
            ],
            check=True,
        )
        result = json.loads(report.read_text())
        findings, inventory = [], []
        for item in result.get("Results", []):
            for pkg in item.get("Packages", []):
                inventory.append(
                    dict(
                        name=pkg["Name"],
                        version=pkg["Version"],
                        kind=item.get("Type"),
                        licenses=pkg.get("Licenses", []),
                    )
                )
            for row in item.get("Vulnerabilities", []):
                if row.get("Severity") in {"HIGH", "CRITICAL"}:
                    findings.append(
                        {
                            k: row.get(k, "")
                            for k in [
                                "VulnerabilityID",
                                "PkgName",
                                "InstalledVersion",
                                "FixedVersion",
                                "Severity",
                                "Status",
                                "PrimaryURL",
                            ]
                        }
                    )
        output = dict(
            checked_at=datetime.now(UTC).isoformat(),
            image=args.image,
            image_id=result.get("Metadata", {}).get("ImageID"),
            os=result.get("Metadata", {}).get("OS"),
            scanner=result.get("Trivy", {}),
            package_inventory=inventory,
            findings=findings,
            release_blocked=bool(findings),
            limitations="Known advisories only; no reachability or future guarantee.",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2) + "\n")
        # This image contains no deployment configuration; retain only non-secret package evidence.
        print("DEELVO_CONTAINER_AUDIT=" + json.dumps(output, separators=(",", ":")))
        print(
            "Production gate: "
            + (
                "BLOCKED — findings need fixes/explicit risk review"
                if findings
                else "no known HIGH/CRITICAL findings in this scan"
            )
        )


if __name__ == "__main__":
    main()
