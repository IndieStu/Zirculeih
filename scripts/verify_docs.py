"""Check local documentation links and planned acceptance coverage without network."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
IGNORED = {".venv", ".local", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
errors = []
files = [p for p in ROOT.rglob("*.md") if not IGNORED.intersection(p.relative_to(ROOT).parts)]
for path in files:
    text = path.read_text()
    if text.count("```") % 2:
        errors.append(f"Unclosed fence: {path.relative_to(ROOT)}")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if "://" in target or target.startswith(("#", "mailto:")):
            continue
        dest = path.parent / unquote(target.split("#")[0])
        if not dest.exists():
            errors.append(f"Missing link: {path.relative_to(ROOT)} -> {target}")
coverage = (ROOT / "docs/ACCEPTANCE_MATRIX.md").read_text()
for prefix, count in (
    ("AC", 31),
    ("KIOSK-AC", 22),
    ("P3-AC", 16),
    ("P4-AC", 14),
    ("P5-AC", 16),
    ("P6-AC", 18),
    ("DASH", 4),
    ("API", 4),
    ("CAL", 6),
    ("DOC", 4),
):
    for number in range(1, count + 1):
        scenario = f"{prefix}-{number:02}"
        if coverage.count(f"| {scenario} |") != 1:
            errors.append(f"Missing or duplicated acceptance scenario {scenario}")
for chapter in (
    "README",
    "getting-started",
    "concepts",
    "users-and-groups",
    "inventory",
    "locations",
    "identifiers-and-scanning",
    "dashboard",
    "administration",
    "imports-and-media",
    "resources",
    "catalog",
    "bookings",
    "booking-administration",
    "loans",
    "agreements",
    "backup-restore",
    "troubleshooting",
):
    path = ROOT / "docs" / "handbook" / (chapter + ".md")
    if not path.exists() or len(path.read_text().strip()) < 150:
        errors.append(f"Missing/incomplete handbook chapter: {chapter}")
if errors:
    raise SystemExit("\n".join(errors))
print(
    f"PASS: {len(files)} Markdown files, links/fences, "
    "AC/KIOSK/P3/P4/P5/P6/DASH/API/CAL/DOC coverage, handbook"
)
