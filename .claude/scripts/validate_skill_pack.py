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

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402

ROOT = roots.framework_root()

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    # Strip UTF-8 BOM if present (common in auto-generated Tier 3 skill files)
    if text.startswith("﻿"):
        text = text[1:]
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
    # If this is a SKILL.md, the parent folder name must match `name` (Claude Code spec).
    # Exception: unity-skills sub-modules use "unity-<folder>" naming convention.
    if path.name == "SKILL.md" and fm.get("name"):
        folder = path.parent.name
        fm_name = fm["name"]
        # Allow "unity-*" names for skills under .claude/skills/unity-skills/
        # Tier 2 sub-modules use "unity-<folder>" and the index uses "unity-skills-index"
        is_unity_submodule = ".claude/skills/unity-skills/" in str(path).replace("\\", "/")
        unity_prefix_ok = is_unity_submodule and fm_name.startswith("unity-")
        if fm_name != folder and not unity_prefix_ok:
            issues.append(
                f"{path}: frontmatter `name: {fm_name}` does not match folder `{folder}`"
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

    # Tier 3 sub-skill dirs (unity-dots/*) now have minimal frontmatter (name + description +
    # metadata.internal-only + metadata.tier) after Phase 3 migration. Check them normally.
    TIER3_DIRS = {
        str((ROOT / ".claude" / "skills" / "unity-dots").resolve()),
    }
    tier3_checked = 0

    for skill in (ROOT / ".claude" / "skills").rglob("SKILL.md"):
        skill_str = str(skill.parent.resolve())
        is_tier3_subskill = any(
            skill.parent.resolve() != Path(t3) and skill.parent.resolve().is_relative_to(Path(t3))
            for t3 in TIER3_DIRS
        )
        summary["skills_checked"] += 1
        issues.extend(check_skill(skill))
        if is_tier3_subskill:
            tier3_checked += 1

    if tier3_checked:
        summary["tier3_checked"] = tier3_checked

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
    if summary.get("tier3_checked"):
        print(f"  (tier3 sub-skills checked: {summary['tier3_checked']})")
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
