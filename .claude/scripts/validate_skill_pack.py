#!/usr/bin/env python3
"""
Validate the SKILL.md frontmatter and structure of this package.

Checks:
  - Every <skill>/SKILL.md has YAML frontmatter with `name` and `description`.
  - `name` matches the parent folder name.
  - Agent files (.claude/agents/*.md) have `name`, `description`, `model`.
  - The /team command exists and is reachable.

Usage:
    python .claude/scripts/validate_skill_pack.py
    python .claude/scripts/validate_skill_pack.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = KEY_RE.match(line)
        if km:
            out[km.group(1)] = km.group(2).strip().strip('"').strip("'")
    return out


def check_skill(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    if fm is None:
        issues.append(f"{path}: missing YAML frontmatter")
        return issues
    if "name" not in fm:
        issues.append(f"{path}: frontmatter missing `name`")
    if "description" not in fm:
        issues.append(f"{path}: frontmatter missing `description`")
    # If this is a SKILL.md, the parent folder name must match `name` (Claude Code spec)
    if path.name == "SKILL.md" and fm.get("name"):
        folder = path.parent.name
        if fm["name"] != folder:
            issues.append(
                f"{path}: frontmatter `name: {fm['name']}` does not match folder `{folder}`"
            )
    return issues


def check_agent(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    if fm is None:
        issues.append(f"{path}: missing YAML frontmatter")
        return issues
    for key in ("name", "description", "model"):
        if key not in fm:
            issues.append(f"{path}: agent frontmatter missing `{key}`")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill pack structure")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    issues: list[str] = []
    summary: dict[str, int] = {"skills_checked": 0, "agents_checked": 0, "issues": 0}

    for skill in (ROOT / ".claude" / "skills").rglob("SKILL.md"):
        summary["skills_checked"] += 1
        issues.extend(check_skill(skill))

    agents_dir = ROOT / ".claude" / "agents"
    if agents_dir.exists():
        for agent in agents_dir.glob("*.md"):
            summary["agents_checked"] += 1
            issues.extend(check_agent(agent))

    team_cmd = ROOT / ".claude" / "commands" / "team.md"
    if not team_cmd.exists():
        issues.append(f"missing: {team_cmd}")

    summary["issues"] = len(issues)

    if args.json:
        print(json.dumps({"summary": summary, "issues": issues}, indent=2))
        return 1 if issues else 0

    print(f"Skills checked: {summary['skills_checked']}")
    print(f"Agents checked: {summary['agents_checked']}")
    if not issues:
        print("OK — no issues")
        return 0
    print(f"\n{len(issues)} issue(s):")
    for line in issues:
        print(f"  - {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
