#!/usr/bin/env python3
"""
Migrate Tier 2 (unity-skills sub-module) SKILL.md files to canonical frontmatter schema.

Operations (all idempotent):
  1. Add use-when (derived from description prefix).
  2. Add do-not-use-when (base constraint + extracted routing/DO-NOT body notes).
  3. Add platforms: [unity-editor, claude-code].
  4. Add task-categories from CATEGORY_MAP.
  5. Add/retain metadata.source + metadata.version: 1.9.2 + metadata.tier: 2.
  6. Truncate description to ≤1024 chars (at word boundary) for 4 known long files.

Does NOT touch:
  - Tier 1 skills (.claude/skills/<name>/SKILL.md at root level)
  - .claude/skills/unity-dots-ecb-lifecycle-debugger/ (owned by dots-skill-author)
  - tests/ or fixtures/
  - Fields already present in frontmatter (idempotent)

Creates unity-skills/CHANGES.md with one entry per modified file.

Usage:
    python .claude/scripts/migrate_tier2_frontmatter.py           # dry-run
    python .claude/scripts/migrate_tier2_frontmatter.py --apply   # write files
    python .claude/scripts/migrate_tier2_frontmatter.py --skill animator  # one skill
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402

ROOT = roots.framework_root()
SKILLS_DIR = roots.claude_root() / "skills" / "unity-skills" / "skills"
CHANGES_MD = roots.claude_root() / "skills" / "unity-skills" / "CHANGES.md"

MAX_DESC_LEN = 1024  # Architect requirement: truncate descriptions to ≤1024 chars

FRONTMATTER_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.DOTALL)

# ── Category map ──────────────────────────────────────────────────────────────
# skill folder name → task-categories list
CATEGORY_MAP: dict[str, list[str]] = {
    "addressables-design":  ["asset-loading", "addressables", "design-advisory"],
    "adr":                  ["architecture", "decision-record", "documentation"],
    "animator":             ["animation", "mecanim", "editor-automation"],
    "architecture":         ["architecture", "design-advisory", "patterns"],
    "asmdef":               ["assembly", "project-structure", "editor-automation"],
    "asset":                ["asset-management", "editor-automation"],
    "async":                ["async", "coroutines", "design-advisory"],
    "batch":                ["batch-operations", "editor-automation"],
    "blueprints":           ["architecture", "design-advisory", "documentation"],
    "bookmark":             ["editor-navigation", "editor-automation"],
    "camera":               ["camera", "cinemachine", "editor-automation"],
    "cinemachine":          ["camera", "cinemachine", "editor-automation"],
    "cleaner":              ["cleanup", "refactoring", "editor-automation"],
    "component":            ["component", "gameobject", "editor-automation"],
    "console":              ["debug", "logging", "editor-automation"],
    "debug":                ["debug", "diagnostics", "editor-automation"],
    "decal":                ["rendering", "urp", "editor-automation"],
    "dotween":              ["animation", "tweening", "editor-automation"],
    "dotween-design":       ["animation", "tweening", "design-advisory"],
    "editor":               ["editor-automation", "play-mode"],
    "event":                ["events", "messaging", "editor-automation"],
    "gameobject":           ["gameobject", "scene", "editor-automation"],
    "graphics":             ["rendering", "graphics-settings", "editor-automation"],
    "history":              ["editor-navigation", "undo-redo", "editor-automation"],
    "importer":             ["asset-import", "textures", "editor-automation"],
    "inspector":            ["editor-tooling", "inspector", "editor-automation"],
    "light":                ["lighting", "editor-automation"],
    "material":             ["materials", "rendering", "editor-automation"],
    "navmesh":              ["navigation", "pathfinding", "editor-automation"],
    "netcode":              ["networking", "multiplayer", "editor-automation"],
    "netcode-design":       ["networking", "multiplayer", "design-advisory"],
    "optimization":         ["optimization", "performance", "design-advisory"],
    "package":              ["packages", "project-setup", "editor-automation"],
    "patterns":             ["design-patterns", "design-advisory"],
    "perception":           ["scene-analysis", "diagnostics", "editor-automation"],
    "performance":          ["performance", "profiling", "design-advisory"],
    "physics":              ["physics", "collision", "editor-automation"],
    "postprocess":          ["post-processing", "rendering", "editor-automation"],
    "prefab":               ["prefab", "editor-automation"],
    "probuilder":           ["mesh-editing", "probuilder", "editor-automation"],
    "profiler":             ["profiling", "performance", "editor-automation"],
    "project":              ["project-structure", "editor-automation"],
    "project-scout":        ["project-analysis", "diagnostics", "editor-automation"],
    "sample":               ["samples", "learning", "editor-automation"],
    "scene":                ["scene", "editor-automation"],
    "scene-contracts":      ["scene", "architecture", "design-advisory"],
    "script":               ["scripting", "editor-automation"],
    "script-roles":         ["scripting", "architecture", "design-advisory"],
    "scriptableobject":     ["scriptable-objects", "data", "editor-automation"],
    "scriptdesign":         ["scripting", "design-advisory"],
    "shader":               ["shaders", "rendering", "editor-automation"],
    "shadergraph":          ["shadergraph", "rendering", "editor-automation"],
    "shadergraph-design":   ["shadergraph", "rendering", "design-advisory"],
    "smart":                ["editor-automation", "smart-operations"],
    "terrain":              ["terrain", "environment", "editor-automation"],
    "test":                 ["testing", "edit-mode-tests", "editor-automation"],
    "testability":          ["testing", "testability", "design-advisory"],
    "timeline":             ["timeline", "animation", "editor-automation"],
    "ui":                   ["ugui", "ui", "editor-automation"],
    "uitoolkit":            ["ui-toolkit", "ui", "editor-automation"],
    "unitask-design":       ["async", "unitask", "design-advisory"],
    "urp":                  ["urp", "rendering", "editor-automation"],
    "validation":           ["validation", "diagnostics", "editor-automation"],
    "volume":               ["post-processing", "volume", "editor-automation"],
    "workflow":             ["editor-automation", "workflow"],
    "xr":                   ["xr", "vr-ar", "editor-automation"],
    "yooasset":             ["asset-loading", "yooasset", "editor-automation"],
    "yooasset-design":      ["asset-loading", "yooasset", "design-advisory"],
}

# Descriptions that are design/advisory only (do NOT require REST server for use-when)
ADVISORY_SKILLS = {
    "addressables-design", "adr", "architecture", "async", "blueprints",
    "dotween-design", "netcode-design", "optimization", "patterns", "performance",
    "scene-contracts", "script-roles", "scriptdesign", "shadergraph-design",
    "testability", "unitask-design", "yooasset-design",
}


# ── YAML helpers ──────────────────────────────────────────────────────────────

def _yaml_block_scalar(value: str, indent: int = 2) -> str:
    pad = " " * indent
    lines = value.strip().splitlines()
    body = "\n".join(f"{pad}{line}" if line.strip() else "" for line in lines)
    return f"|-\n{body}"


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def _parse_yaml_top_keys(fm_body: str) -> set[str]:
    return set(re.findall(r"^([A-Za-z0-9_-]+)\s*:", fm_body, re.MULTILINE))


def _parse_metadata_subkeys(fm_body: str) -> set[str]:
    subkeys: set[str] = set()
    in_metadata = False
    for line in fm_body.splitlines():
        if re.match(r"^metadata\s*:", line):
            in_metadata = True
            continue
        if in_metadata:
            m = re.match(r"^  ([A-Za-z0-9_-]+)\s*:", line)
            if m:
                subkeys.add(m.group(1))
            elif line.strip() and not line.startswith(" "):
                in_metadata = False
    return subkeys


def _inject_metadata_fields(fm_body: str, fields: dict) -> tuple[str, list[str]]:
    existing = _parse_metadata_subkeys(fm_body)
    to_add = {k: v for k, v in fields.items() if k not in existing}
    if not to_add:
        return fm_body, []
    lines = [f"  {k}: {v}" if not isinstance(v, bool) else f"  {k}: {'true' if v else 'false'}"
             for k, v in to_add.items()]
    if "metadata" in _parse_yaml_top_keys(fm_body):
        inject = "\n".join(lines) + "\n"
        fm_body = re.sub(r"^(metadata\s*:\s*\n)", r"\1" + inject, fm_body, count=1, flags=re.MULTILINE)
    else:
        block = "metadata:\n" + "\n".join(lines) + "\n"
        fm_body = fm_body.rstrip("\n") + "\n" + block
    return fm_body, list(to_add.keys())


# ── Field derivation ──────────────────────────────────────────────────────────

def _extract_desc_prefix(description: str) -> str:
    """Return the capability part of description — before 'Triggers:' and Chinese section."""
    # Strip leading/trailing quotes
    desc = description.strip().strip('"').strip("'")
    # Cut at "Triggers:" if present
    cut = re.split(r"\.\s*Triggers\s*:", desc, maxsplit=1)
    return cut[0].strip().rstrip(".")


def _build_use_when(skill_name: str, desc_prefix: str) -> str:
    if skill_name in ADVISORY_SKILLS:
        return (
            f"Load when designing or reviewing {desc_prefix.lower().split('.')[0].strip()}. "
            "Load for design advisory guidance — does not require Unity Editor running."
        )
    return (
        f"Load when the task requires: {desc_prefix}. "
        "Unity Editor must be running with the unity-skills REST server reachable at http://localhost:8090."
    )


def _extract_routing_notes(body: str) -> list[str]:
    """Extract 'For X use Y' routing lines from skill body."""
    notes = re.findall(r"-\s*For\s+(.+?)\s*→\s*use\s+`?([^`\n]+)`?", body[:3000])
    result = []
    for what, mod in notes[:3]:
        what = what.strip().rstrip(", ")
        mod = mod.strip().rstrip(".")
        result.append(f"For {what} → use `{mod}` module instead.")
    return result


def _extract_do_not_items(body: str) -> list[str]:
    """Extract explicit DO NOT / hallucination notes from skill body."""
    items = []
    # Match "**DO NOT**" blocks
    for block in re.findall(r"\*\*DO NOT\*\*.*?(?=\n\n\n|\n## |\Z)", body[:4000], re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("- ") and len(line) > 5:
                # Extract just the first clause (before "→" or "do not exist")
                clause = re.split(r"\s*→\s*|\s*do not exist", line[2:], maxsplit=1)[0].strip()
                if clause and len(clause) < 200:
                    items.append(clause)
    return items[:3]  # Cap to avoid excessively long do-not-use-when


def _build_do_not_use_when(skill_name: str, body: str) -> str:
    if skill_name in ADVISORY_SKILLS:
        base = (
            "Do not load as a runtime editor-automation skill — this module provides "
            "design advisory guidance only. Do not use for direct Unity Editor mutations."
        )
    else:
        base = (
            "Do not load when Unity Editor is not running locally. "
            "Do not load when unity-skills REST server is unreachable at http://localhost:8090."
        )
    routing = _extract_routing_notes(body)
    if routing:
        base = base + " " + " ".join(routing)
    return base


def _truncate_description(description: str, max_len: int = MAX_DESC_LEN) -> tuple[str, bool]:
    """Truncate description at word boundary ≤ max_len, append '…'."""
    if len(description) <= max_len:
        return description, False
    # Truncate at last space before limit-3 (room for "…")
    cut_at = max_len - 1
    idx = description.rfind(" ", 0, cut_at)
    if idx < 0:
        idx = cut_at
    truncated = description[:idx].rstrip(".,; ") + "…"
    return truncated, True


# ── Core migration ────────────────────────────────────────────────────────────

def migrate_skill(skill_name: str, skill_path: Path, apply: bool) -> tuple[bool, list[str]]:
    text = skill_path.read_text(encoding="utf-8-sig")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False, [f"SKIP: no frontmatter in {skill_path}"]

    open_fence = m.group(1)
    fm_body = m.group(2)
    close_fence = m.group(3)
    rest = text[m.end():]

    existing_keys = _parse_yaml_top_keys(fm_body)
    actions: list[str] = []
    new_fm = fm_body

    # ── 1. Truncate description if too long ───────────────────────────────
    desc_match = re.search(r'^(description\s*:\s*)"([^"]*)"', new_fm, re.MULTILINE)
    if desc_match:
        raw_desc = desc_match.group(2)
        truncated, was_truncated = _truncate_description(raw_desc)
        if was_truncated:
            new_fm = new_fm[:desc_match.start(2)] + '"' + truncated + '"' + new_fm[desc_match.end(2):]
            actions.append(f"  description: truncated {len(raw_desc)} → {len(truncated)} chars")
            raw_desc = truncated
    else:
        # Try unquoted description
        desc_match = re.search(r'^description\s*:\s*(.+)', new_fm, re.MULTILINE)
        raw_desc = desc_match.group(1).strip() if desc_match else ""

    desc_prefix = _extract_desc_prefix(raw_desc)

    # ── 2. Add platforms ──────────────────────────────────────────────────
    if "platforms" not in existing_keys:
        platforms_line = f"platforms: [unity-editor, claude-code]\n"
        new_fm = new_fm.rstrip("\n") + "\n" + platforms_line
        actions.append("  platforms: added [unity-editor, claude-code]")

    # ── 3. Add task-categories ────────────────────────────────────────────
    if "task-categories" not in existing_keys:
        categories = CATEGORY_MAP.get(skill_name, ["editor-automation"])
        cats_line = f"task-categories: {_yaml_list(categories)}\n"
        new_fm = new_fm.rstrip("\n") + "\n" + cats_line
        actions.append(f"  task-categories: {categories}")

    # ── 4. Add use-when ───────────────────────────────────────────────────
    if "use-when" not in existing_keys:
        use_when_text = _build_use_when(skill_name, desc_prefix)
        use_when_block = f"use-when: {_yaml_block_scalar(use_when_text)}\n"
        new_fm = new_fm.rstrip("\n") + "\n" + use_when_block
        actions.append("  use-when: added")

    # ── 5. Add do-not-use-when ────────────────────────────────────────────
    if "do-not-use-when" not in existing_keys:
        dnu_text = _build_do_not_use_when(skill_name, rest)
        dnu_block = f"do-not-use-when: {_yaml_block_scalar(dnu_text)}\n"
        new_fm = new_fm.rstrip("\n") + "\n" + dnu_block
        actions.append("  do-not-use-when: added")

    # ── 6. Add metadata.source + version + tier ───────────────────────────
    meta_fields = {
        "source": "https://github.com/Besty0728/Unity-Skills",
        "version": "1.9.2",
        "tier": "2",
    }
    new_fm, injected = _inject_metadata_fields(new_fm, meta_fields)
    for k in injected:
        actions.append(f"  metadata.{k}: added ({meta_fields[k]!r})")

    if not actions:
        return False, []

    new_text = open_fence + new_fm + close_fence + rest
    if text.startswith("﻿"):
        new_text = "﻿" + new_text

    if apply:
        skill_path.write_text(new_text, encoding="utf-8")

    return True, actions


# ── CHANGES.md writer ─────────────────────────────────────────────────────────

def _write_changes_entry(skill_name: str, actions: list[str], apply: bool) -> str:
    today = date.today().isoformat()
    fields_added = [a.strip().split(":")[0] for a in actions if not a.startswith("SKIP")]
    summary = f"Added frontmatter fields: {', '.join(fields_added)}"
    entry = (
        f"\n## {today} — {skill_name}\n"
        f"- **What**: {summary}\n"
        f"- **Why**: Phase 2 canonical frontmatter migration (task-categories, use-when, "
        f"do-not-use-when, platforms, metadata.source/version/tier)\n"
        f"- **Phase**: Phase 2 Tier 2 frontmatter standardization\n"
    )
    return entry


def update_changes_md(entries: list[tuple[str, list[str]]], apply: bool) -> None:
    """Append one entry per changed skill to unity-skills/CHANGES.md."""
    today = date.today().isoformat()
    header = (
        f"# Unity-Skills CHANGES\n\n"
        f"Tracks per-file modifications made during agent-pipeline Phase 2 migration.\n"
        f"Required by architect per Phase 2 hard constraints.\n\n"
        f"---\n"
    )
    body = "".join(_write_changes_entry(name, actions, apply) for name, actions in entries)
    content = header + body

    if apply:
        CHANGES_MD.write_text(content, encoding="utf-8")
    return content


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Tier 2 unity-skills SKILL.md frontmatter")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    parser.add_argument("--skill", help="Process only this skill folder name")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"migrate_tier2_frontmatter — mode: {mode}")
    print()

    if args.skill:
        skill_paths = [SKILLS_DIR / args.skill / "SKILL.md"]
    else:
        skill_paths = sorted(
            p for p in SKILLS_DIR.rglob("SKILL.md")
            if p.parent.name != "skills"  # skip index
        )

    changed_count = 0
    skipped_count = 0
    error_count = 0
    changes_entries: list[tuple[str, list[str]]] = []

    for skill_path in skill_paths:
        skill_name = skill_path.parent.name
        if not skill_path.exists():
            print(f"  ERROR (not found): {skill_path}")
            error_count += 1
            continue

        changed, actions = migrate_skill(skill_name, skill_path, apply=args.apply)

        if changed:
            changed_count += 1
            verb = "APPLIED" if args.apply else "WOULD CHANGE"
            print(f"  {verb}: {skill_name}")
            for a in actions:
                print(f"    {a}")
            changes_entries.append((skill_name, actions))
        elif actions and actions[0].startswith("SKIP"):
            skipped_count += 1
            print(f"  SKIP: {skill_name} — {actions[0]}")
        else:
            print(f"  OK (no changes): {skill_name}")

    print()
    print(f"Summary: {changed_count} changed, {skipped_count} skipped, {error_count} errors")

    if changes_entries:
        changes_content = update_changes_md(changes_entries, apply=args.apply)
        if args.apply:
            print(f"CHANGES.md written: {CHANGES_MD}")
        else:
            print(f"CHANGES.md would be written to: {CHANGES_MD}")
            print(f"  ({len(changes_entries)} entries)")

    if not args.apply and changed_count:
        print("Re-run with --apply to write changes.")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
