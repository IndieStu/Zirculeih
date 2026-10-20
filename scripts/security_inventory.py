"""Reproducible locked Python SBOM and explicit online OSV/PyPI audit, no extra dependency."""

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def locked():
    rows = []
    for file, role in [("requirements.lock", "runtime"), ("requirements-dev.lock", "development")]:
        text = Path(file).read_text()
        for match in re.finditer(r"^([\w-]+)==([^\s]+)(.*?)(?=^[\w-]+==|\Z)", text, re.M | re.S):
            name, version, tail = match.groups()
            rows.append(
                dict(
                    name=name,
                    version=version,
                    role=role,
                    hashes=sorted(set(re.findall(r"--hash=sha256:([a-f0-9]{64})", tail))),
                )
            )
    return rows


def request_json(url, data=None):
    request = Request(
        url,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"User-Agent": "Deelvo-release-audit", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("Audit response too large")
    return json.loads(raw)


def sbom():
    policy = json.loads(Path("docs/release/dependency-policy.json").read_text())
    components = []
    for row in locked():
        if not row["hashes"] or row["name"] not in policy:
            raise ValueError("Unreviewed or unhashed locked component: " + row["name"])
        purl = "pkg:pypi/" + row["name"].lower().replace("_", "-") + "@" + row["version"]
        components.append(
            dict(
                type="library",
                name=row["name"],
                version=row["version"],
                purl=purl,
                **{"bom-ref": purl},
                licenses=[{"expression": policy[row["name"]]}],
                hashes=[{"alg": "SHA-256", "content": h} for h in row["hashes"]],
                properties=[
                    {"name": "deelvo:scope", "value": row["role"]},
                    {
                        "name": "deelvo:hash-meaning",
                        "value": "Locked wheels; native libraries inventoried separately",
                    },
                ],
            )
        )
    return dict(
        bomFormat="CycloneDX",
        specVersion="1.6",
        version=1,
        metadata={
            "component": {
                "type": "application",
                "name": "Deelvo",
                "version": "phase-13-review",
                "licenses": [{"expression": "AGPL-3.0-or-later"}],
            },
            "properties": [
                {
                    "name": "deelvo:license-status",
                    "value": "AGPL-3.0-or-later approved; third-party obligations separate",
                },
                {
                    "name": "deelvo:scope",
                    "value": "Python only; font/OS/codec inventories separate",
                },
            ],
        },
        components=components,
    )


def audit():
    rows = locked()
    request = {
        "queries": [
            {"package": {"ecosystem": "PyPI", "name": r["name"]}, "version": r["version"]}
            for r in rows
        ]
    }
    response = request_json("https://api.osv.dev/v1/querybatch", request)
    if len(response.get("results", [])) != len(rows):
        raise ValueError("Incomplete OSV response")

    def pypi(row):
        info = request_json(
            "https://pypi.org/pypi/" + quote(row["name"]) + "/" + quote(row["version"]) + "/json"
        )
        return dict(
            name=row["name"],
            version=row["version"],
            yanked=bool(info.get("urls")) and all(u.get("yanked") for u in info["urls"]),
            vulnerabilities=[v["id"] for v in info.get("vulnerabilities", [])],
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        metadata = list(pool.map(pypi, rows))
    results = []
    for row, result, release in zip(rows, response["results"], metadata, strict=True):
        results.append(
            dict(
                name=row["name"],
                version=row["version"],
                role=row["role"],
                osv_ids=[v["id"] for v in result.get("vulns", [])],
                pypi_ids=release["vulnerabilities"],
                yanked=release["yanked"],
                incomplete=bool(result.get("next_page_token")),
            )
        )
    return dict(
        checked_at=datetime.now(UTC).isoformat(),
        sources=[
            "https://api.osv.dev/v1/querybatch",
            "https://pypi.org/pypi/{name}/{version}/json",
        ],
        lock_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path("requirements.lock"), Path("requirements-dev.lock")]
        },
        results=results,
        findings=sum(
            bool(r["osv_ids"] or r["pypi_ids"] or r["yanked"] or r["incomplete"]) for r in results
        ),
        limitations="Known package advisories only; no container, pentest or future guarantee.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--audit", type=Path)
    options = parser.parse_args()
    options.sbom.parent.mkdir(parents=True, exist_ok=True)
    options.sbom.write_text(json.dumps(sbom(), indent=2) + "\n")
    if options.audit:
        result = audit()
        options.audit.parent.mkdir(parents=True, exist_ok=True)
        options.audit.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"packages": len(result["results"]), "findings": result["findings"]}))
        if result["findings"]:
            raise SystemExit("Dependency findings require review; no implicit waiver.")


if __name__ == "__main__":
    main()
