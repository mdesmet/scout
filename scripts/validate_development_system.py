from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
PLANNING = ROOT / "planning"
ALLOWED_STATUSES = {
    "draft",
    "accepted",
    "implementing",
    "implemented",
    "deferred",
    "rejected",
    "superseded",
}
PLACEHOLDERS = ("TBD", "TODO", "NEEDS CLARIFICATION")


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc

    values: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        metadata = frontmatter(path)
    except ValueError as exc:
        return [f"{path.relative_to(ROOT)}: {exc}"]
    folder = path.parent.name
    if metadata.get("name") != folder:
        errors.append(f"{path.relative_to(ROOT)}: name must match folder {folder!r}")
    if not metadata.get("description"):
        errors.append(f"{path.relative_to(ROOT)}: description is required")
    return errors


def validate_proposal(path: Path, index: str) -> list[str]:
    errors: list[str] = []
    relative = path.relative_to(ROOT)
    try:
        metadata = frontmatter(path)
    except ValueError as exc:
        return [f"{relative}: {exc}"]

    match = re.fullmatch(r"(\d+)-[a-z0-9]+(?:-[a-z0-9]+)*\.md", path.name)
    if not match:
        errors.append(f"{relative}: filename must be <issue-number>-<slug>.md")
        return errors

    expected_id = f"PEP-{match.group(1)}"
    if metadata.get("id") != expected_id:
        errors.append(f"{relative}: id must be {expected_id}")
    status = metadata.get("status")
    if status not in ALLOWED_STATUSES:
        errors.append(f"{relative}: unsupported status {status!r}")
    if expected_id not in index:
        errors.append(f"{relative}: {expected_id} is missing from planning/README.md")
    if status in {"accepted", "implemented"}:
        body = path.read_text(encoding="utf-8")
        for placeholder in PLACEHOLDERS:
            if placeholder in body:
                errors.append(f"{relative}: {status} proposal contains {placeholder}")
    return errors


def main() -> int:
    errors: list[str] = []
    required = [
        ROOT / "AGENTS.md",
        PLANNING / "README.md",
        PLANNING / "proposal-template.md",
        PLANNING / "plans" / "README.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: required file is missing")

    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    if not skill_files:
        errors.append(".agents/skills: at least one skill is required")
    for path in skill_files:
        errors.extend(validate_skill(path))

    index_path = PLANNING / "README.md"
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    for path in sorted((PLANNING / "proposals").glob("*.md")):
        errors.extend(validate_proposal(path, index))

    if errors:
        print("Development system validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(skill_files)} skills and the PEP workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
