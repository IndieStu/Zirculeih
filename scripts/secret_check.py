"""Small repository secret-pattern gate. Prints locations/categories, never matching values."""

import argparse
import re
import subprocess
from pathlib import Path

RULES = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "deelvo_raw_token": re.compile(rb"\bdv1_[A-Za-z0-9_-]{43}\b"),
}


def scan(paths):
    findings = []
    for path in paths:
        p = Path(path)
        if not p.is_file() or p.is_symlink():
            continue
        for number, line in enumerate(p.read_bytes().splitlines(), 1):
            for kind, rule in RULES.items():
                if rule.search(line):
                    findings.append(dict(file=str(p), line=number, kind=kind))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", default="git")
    options = parser.parse_args()
    files = subprocess.check_output([options.git, "ls-files", "-z"]).decode().split("\0")
    findings = scan([p for p in files if p])
    if findings:
        for row in findings:
            print(f"{row['file']}:{row['line']}: {row['kind']}")
        raise SystemExit("Secret patterns found; review before committing.")
    print("PASS: tracked-file secret patterns; heuristic, not a complete secret detector")


if __name__ == "__main__":
    main()
