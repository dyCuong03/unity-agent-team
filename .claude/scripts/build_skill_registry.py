#!/usr/bin/env python3
"""
build_skill_registry.py — load / validate / refresh the /team skill registry.

The registry (.claude/skills/registry.json) is the metadata source of truth for
skill routing: which skills exist, their domains/roles/intents/keywords/priority,
and which are meta-only (not loaded for normal task execution).

Subcommands:
  check        — validate the registry (default): every entry path exists, and every
                 on-disk skill folder with a SKILL.md has a registry entry. Exit 1 on issue.
  list         — print the registry as a table.
  scan         — list skill folders on disk + their frontmatter `name`.

Flags:
  --json       — machine-readable output.

Stdlib only. Works on Windows + POSIX.
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
SKILLS_DIR = roots.claude_root() / "skills"
REGISTRY = SKILLS_DIR / "registry.json"

NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def frontmatter_name(skill_md: Path) -> str | None:
    if not skill_md.exists():
        return None
    text = skill_md.read_text(encoding="utf-8", errors="replace")[:2000]
    m = NAME_RE.search(text)
    return m.group(1).strip().strip('"').strip("'") if m else None


def disk_skill_folders() -> list[str]:
    out = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            out.append(child.name)
    return out


def cmd_check(as_json: bool) -> int:
    issues: list[str] = []
    if not REGISTRY.exists():
        msg = f"registry missing: {REGISTRY}"
        print(json.dumps({"issues": [msg]}) if as_json else msg)
        return 1

    reg = load_registry()
    entries = reg.get("skills", [])
    reg_names = {e["name"] for e in entries}

    # 1. every registry path exists
    for e in entries:
        p = ROOT / e["path"]
        if not p.exists():
            issues.append(f"registry entry '{e['name']}' path does not exist: {e['path']}")
        if e["path"] != f".claude/skills/{e['name']}/SKILL.md":
            issues.append(
                f"registry entry '{e['name']}' path '{e['path']}' does not match "
                f".claude/skills/{e['name']}/SKILL.md (registry keys on folder name)"
            )

    # 2. every on-disk skill folder has a registry entry
    for folder in disk_skill_folders():
        if folder not in reg_names:
            issues.append(f"skill folder '{folder}' has SKILL.md but no registry entry")

    # 3. structural sanity
    for e in entries:
        for field in ("name", "path", "domains", "roles", "intents", "keywords", "priority"):
            if field not in e:
                issues.append(f"registry entry '{e.get('name', '?')}' missing field '{field}'")

    ok = not issues
    if as_json:
        print(json.dumps({"ok": ok, "entries": len(entries), "issues": issues}, indent=2))
    else:
        print(f"registry entries: {len(entries)}  disk folders: {len(disk_skill_folders())}")
        if ok:
            print("OK — registry valid (all paths exist, all folders covered)")
        else:
            print(f"\n{len(issues)} issue(s):")
            for i in issues:
                print(f"  - {i}")
    return 0 if ok else 1


def cmd_list(as_json: bool) -> int:
    reg = load_registry()
    entries = reg.get("skills", [])
    if as_json:
        print(json.dumps(entries, indent=2))
        return 0
    print(f"{'name':<30} {'mode':<10} {'pri':>4}  domains/roles")
    for e in sorted(entries, key=lambda x: -x.get("priority", 0)):
        mode = e.get("mode", "skill")
        dom = ",".join(e.get("domains", []))
        roles = ",".join(e.get("roles", [])) or "-"
        print(f"{e['name']:<30} {mode:<10} {e.get('priority', 0):>4}  [{dom}] {roles}")
    return 0


def cmd_scan(as_json: bool) -> int:
    rows = [{"folder": f, "frontmatter_name": frontmatter_name(SKILLS_DIR / f / "SKILL.md")}
            for f in disk_skill_folders()]
    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['folder']:<30} name={r['frontmatter_name']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Load/validate/refresh the skill registry")
    ap.add_argument("command", nargs="?", default="check", choices=["check", "list", "scan"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.command == "check":
        return cmd_check(args.json)
    if args.command == "list":
        return cmd_list(args.json)
    return cmd_scan(args.json)


if __name__ == "__main__":
    sys.exit(main())
