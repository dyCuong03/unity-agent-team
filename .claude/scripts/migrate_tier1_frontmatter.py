#!/usr/bin/env python3
"""
Migrate Tier 1 SKILL.md files to canonical frontmatter schema.

Operations (all idempotent):
  1. Add `task-categories` from registry.json if missing in frontmatter.
  2. Move `user-invocable: <val>` from top-level to `metadata.user-invocable`.
  3. Add `use-when`, `do-not-use-when`, `platforms` for Group B skills
     (routing, skill-creator, unity-skills) which have none of these yet.

Does NOT touch:
  - .claude/skills/unity-dots-ecb-lifecycle-debugger/  (owned by dots-skill-author)
  - tests/ or fixtures/
  - Any skill not registered in registry.json

Usage:
    python .claude/scripts/migrate_tier1_frontmatter.py            # dry-run
    python .claude/scripts/migrate_tier1_frontmatter.py --apply    # write files
    python .claude/scripts/migrate_tier1_frontmatter.py --skill <name>  # one skill
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]

# Skills owned by other agents — never touch their SKILL.md
SKIP_SKILLS = {"unity-dots-ecb-lifecycle-debugger"}

FRONTMATTER_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.DOTALL)

# Group B: skills missing use-when / do-not-use-when / platforms entirely.
# Values derived from file content + registry metadata.
GROUP_B_ADDITIONS: dict[str, dict] = {
    "routing": {
        "use-when": (
            "Load when the orchestrator needs to select which Unity-Skills modules to "
            "include for an agent prompt. Load when determining Layer 1/2/3 skill loading "
            "strategy before spawning any agent."
        ),
        "do-not-use-when": (
            "Do not load as a runtime skill inside any agent role. "
            "Internal orchestration helper only — never loaded by triage, unity-dev, "
            "architect, or tester."
        ),
        "platforms": ["claude-code"],
    },
    "skill-creator": {
        "use-when": (
            "Load when creating a new skill from scratch, editing or improving an existing "
            "skill, running evals to measure skill performance, benchmarking skill quality "
            "with variance analysis, or optimizing a skill description for better routing "
            "accuracy."
        ),
        "do-not-use-when": (
            "Do not load for runtime Unity development tasks or any pipeline agent role "
            "(triage, unity-dev, architect, tester, verifier). Skill authoring only."
        ),
        "platforms": ["claude-code"],
    },
    "unity-skills": {
        "use-when": (
            "Load when the task requires Unity Editor automation via the local UnitySkills "
            "REST server. Load for scene analysis, script creation, asset management, editor "
            "workflow automation, or any call to http://localhost:8090."
        ),
        "do-not-use-when": (
            "Do not load when Unity Editor is not running locally. Do not load for "
            "pure DOTS/ECS code tasks that have no Editor interaction. Do not load "
            "when unity-skills REST server is known unreachable."
        ),
        "platforms": ["claude-code"],
    },
}


# ── YAML helpers ──────────────────────────────────────────────────────────────

def _yaml_block_scalar(value: str, indent: int = 2) -> str:
    """Render a multiline string as a YAML literal block scalar with consistent indent."""
    pad = " " * indent
    lines = value.strip().splitlines()
    body = "\n".join(f"{pad}{line}" if line.strip() else "" for line in lines)
    return f"|-\n{body}"


def _yaml_list(items: list[str]) -> str:
    """Render a list as a compact inline YAML sequence."""
    parts = ", ".join(items)
    return f"[{parts}]"


def _build_task_categories_line(categories: list[str]) -> str:
    return f"task-categories: {_yaml_list(categories)}\n"


def _build_use_when_block(text: str) -> str:
    return f"use-when: {_yaml_block_scalar(text)}\n"


def _build_do_not_use_when_block(text: str) -> str:
    return f"do-not-use-when: {_yaml_block_scalar(text)}\n"


def _build_platforms_line(platforms: list[str]) -> str:
    return f"platforms: {_yaml_list(platforms)}\n"


def _build_metadata_line(key: str, value) -> str:
    if isinstance(value, bool):
        val_str = "true" if value else "false"
    else:
        val_str = str(value)
    return f"metadata:\n  {key}: {val_str}\n"


def _parse_metadata_subkeys(fm_body: str) -> set[str]:
    """Return set of sub-key names already present inside the metadata: block."""
    subkeys: set[str] = set()
    in_metadata = False
    for line in fm_body.splitlines():
        if re.match(r"^metadata\s*:", line):
            in_metadata = True
            continue
        if in_metadata:
            # Indented line under metadata
            m = re.match(r"^  ([A-Za-z0-9_-]+)\s*:", line)
            if m:
                subkeys.add(m.group(1))
            elif line.strip() and not line.startswith(" "):
                # Non-indented non-empty line = new top-level key → stop
                in_metadata = False
    return subkeys


def _inject_metadata_fields(fm_body: str, fields: dict) -> tuple[str, list[str]]:
    """
    Inject missing sub-keys into an existing metadata: block or create the block.
    Returns (new_fm_body, list_of_added_keys).
    """
    existing_subkeys = _parse_metadata_subkeys(fm_body)
    to_add = {k: v for k, v in fields.items() if k not in existing_subkeys}
    if not to_add:
        return fm_body, []

    added_lines = []
    for k, v in to_add.items():
        val_str = ("true" if v else "false") if isinstance(v, bool) else str(v)
        added_lines.append(f"  {k}: {val_str}")

    if "metadata" in _parse_yaml_keys(fm_body):
        # Insert after "metadata:" line (first indented injection point)
        inject_text = "\n".join(added_lines) + "\n"
        fm_body = re.sub(
            r"^(metadata\s*:\s*\n)",
            r"\1" + inject_text,
            fm_body,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        # Create fresh metadata block
        meta_block = "metadata:\n" + "\n".join(added_lines) + "\n"
        fm_body = fm_body.rstrip("\n") + "\n" + meta_block

    return fm_body, list(to_add.keys())


# ── Frontmatter manipulation ──────────────────────────────────────────────────

def _parse_yaml_keys(fm_body: str) -> dict[str, str]:
    """Quick scan of top-level keys in a frontmatter block (no deep parse)."""
    keys: dict[str, str] = {}
    # Only match lines that start without indentation (top-level keys)
    for line in fm_body.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:", line)
        if m:
            keys[m.group(1)] = line
    return keys


def _remove_top_level_key(fm_body: str, key: str) -> tuple[str, Optional[str]]:
    """Remove a top-level scalar key from frontmatter body. Returns (new_body, removed_line)."""
    lines = fm_body.splitlines(keepends=True)
    new_lines = []
    removed = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(" + re.escape(key) + r")\s*:(.*)$", line.rstrip("\n"))
        if m and not line.startswith(" "):
            # Scalar value — single line
            removed = line
            i += 1
        else:
            new_lines.append(line)
            i += 1
    return "".join(new_lines), removed


def _extract_user_invocable_value(removed_line: Optional[str]) -> bool:
    """Parse the value from a removed user-invocable line."""
    if removed_line is None:
        return False
    m = re.search(r":\s*(true|false|True|False|yes|no)", removed_line)
    if m:
        return m.group(1).lower() in ("true", "yes")
    return False


def migrate_skill(
    skill_name: str,
    skill_path: Path,
    registry_entry: dict,
    apply: bool,
) -> tuple[bool, list[str]]:
    """
    Apply migrations to one SKILL.md.
    Returns (changed, list_of_actions).
    """
    text = skill_path.read_text(encoding="utf-8-sig")

    m = FRONTMATTER_RE.match(text)
    if not m:
        return False, [f"SKIP: no frontmatter found in {skill_path}"]

    open_fence = m.group(1)   # "---\n"
    fm_body = m.group(2)      # raw frontmatter text
    close_fence = m.group(3)  # "\n---\n"
    rest = text[m.end():]

    existing_keys = _parse_yaml_keys(fm_body)
    actions: list[str] = []
    new_fm = fm_body

    # ── 1. Move user-invocable from top-level to metadata ─────────────────
    if "user-invocable" in existing_keys and not new_fm.lstrip().startswith(" "):
        # Check it's truly top-level (not already under metadata)
        if re.search(r"^user-invocable\s*:", new_fm, re.MULTILINE):
            new_fm, removed_line = _remove_top_level_key(new_fm, "user-invocable")
            value = _extract_user_invocable_value(removed_line)
            if "metadata" not in _parse_yaml_keys(new_fm):
                meta_block = _build_metadata_line("user-invocable", value)
                new_fm = new_fm.rstrip("\n") + "\n" + meta_block
            else:
                # metadata section already exists — inject into it
                new_fm = re.sub(
                    r"^(metadata\s*:\s*\n)",
                    r"\1  user-invocable: " + ("true" if value else "false") + "\n",
                    new_fm,
                    flags=re.MULTILINE,
                )
            actions.append(f"  user-invocable: {value!s} moved top-level → metadata.user-invocable")

    # ── 2. Add Group B fields if entirely missing ──────────────────────────
    additions = GROUP_B_ADDITIONS.get(skill_name, {})
    if "use-when" in additions and "use-when" not in _parse_yaml_keys(new_fm):
        new_fm = new_fm.rstrip("\n") + "\n" + _build_use_when_block(additions["use-when"])
        actions.append("  use-when: added")
    if "do-not-use-when" in additions and "do-not-use-when" not in _parse_yaml_keys(new_fm):
        new_fm = new_fm.rstrip("\n") + "\n" + _build_do_not_use_when_block(additions["do-not-use-when"])
        actions.append("  do-not-use-when: added")
    if "platforms" in additions and "platforms" not in _parse_yaml_keys(new_fm):
        new_fm = new_fm.rstrip("\n") + "\n" + _build_platforms_line(additions["platforms"])
        actions.append("  platforms: added")

    # ── 3. Add task-categories from registry ──────────────────────────────
    if "task-categories" not in _parse_yaml_keys(new_fm):
        categories = registry_entry.get("task-categories", [])
        if categories:
            new_fm = new_fm.rstrip("\n") + "\n" + _build_task_categories_line(categories)
            actions.append(f"  task-categories: {categories}")
        else:
            actions.append("  task-categories: SKIP — not in registry entry")

    # ── 4. Add metadata.source, metadata.version, metadata.tier ──────────
    # source: registry entry value or "internal"
    reg_source = registry_entry.get("source") or "internal"
    # version: registry entry value or "1.0.0"
    reg_version = registry_entry.get("version") or "1.0.0"
    meta_fields = {
        "source": reg_source,
        "version": reg_version,
        "tier": 1,
    }
    new_fm, injected_keys = _inject_metadata_fields(new_fm, meta_fields)
    for k in injected_keys:
        actions.append(f"  metadata.{k}: added ({meta_fields[k]!r})")

    if not actions:
        return False, []

    new_text = open_fence + new_fm + close_fence + rest

    # Preserve original BOM if present
    if text.startswith("﻿"):
        new_text = "﻿" + new_text

    if apply:
        skill_path.write_text(new_text, encoding="utf-8")

    return True, actions


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Tier 1 SKILL.md frontmatter")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    parser.add_argument("--skill", help="Migrate only this skill by name")
    args = parser.parse_args()

    registry_path = ROOT / ".claude" / "skills" / "registry.json"
    if not registry_path.exists():
        print(f"ERROR: registry.json not found at {registry_path}", file=sys.stderr)
        return 1

    with registry_path.open(encoding="utf-8") as f:
        registry = json.load(f)

    # Support both flat list and {skills: [...]} formats
    skill_list: list[dict] = registry if isinstance(registry, list) else registry.get("skills", [])
    registry_map = {s["name"]: s for s in skill_list}

    if args.skill:
        if args.skill not in registry_map:
            print(f"ERROR: skill '{args.skill}' not in registry.json", file=sys.stderr)
            return 1
        targets = {args.skill: registry_map[args.skill]}
    else:
        targets = registry_map

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"migrate_tier1_frontmatter — mode: {mode}")
    print()

    changed_count = 0
    skipped_count = 0
    error_count = 0

    for skill_name, entry in targets.items():
        if skill_name in SKIP_SKILLS:
            print(f"  SKIP (ownership): {skill_name}")
            skipped_count += 1
            continue

        skill_path = ROOT / entry.get("path", "")
        if not skill_path.exists():
            print(f"  ERROR (not found): {skill_path}")
            error_count += 1
            continue

        changed, actions = migrate_skill(skill_name, skill_path, entry, apply=args.apply)

        if changed:
            changed_count += 1
            verb = "APPLIED" if args.apply else "WOULD CHANGE"
            print(f"  {verb}: {skill_name}")
            for a in actions:
                print(f"    {a}")
        else:
            print(f"  OK (no changes): {skill_name}")

    print()
    print(f"Summary: {changed_count} changed, {skipped_count} skipped (ownership), {error_count} errors")
    if not args.apply and changed_count:
        print("Re-run with --apply to write changes.")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
