"""Check local documentation links and planned acceptance coverage without network."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
IGNORED = {".venv", ".local", ".git"}
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
for prefix, count in (("AC", 31), ("KIOSK-AC", 22)):
    for number in range(1, count + 1):
        scenario = f"{prefix}-{number:02}"
        if coverage.count(f"| {scenario} |") != 1:
            errors.append(f"Missing or duplicated acceptance scenario {scenario}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: {len(files)} Markdown files, local links/fences, AC-01–31 + KIOSK-AC-01–22 coverage")
